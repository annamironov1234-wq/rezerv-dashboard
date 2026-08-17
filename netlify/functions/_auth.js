/**
 * Пароль и пропуска для дашборда.
 *
 * Взято из базы исполнителей (podbor-smen/baza/netlify/functions/_auth.js)
 * и упрощено: там две роли, здесь ролей нет вообще. Вопрос один -
 * свой человек или нет. Смотрят дашборд Анна и муж.
 *
 * Ни одной внешней библиотеки: всё встроенным crypto. Чем меньше
 * зависимостей, тем меньше того, что сломается через год.
 */
import crypto from 'node:crypto';

/** Хэш вида scrypt$соль$хэш. Соль своя, поэтому по таблице не подобрать. */
export function hashPassword(plain) {
  const salt = crypto.randomBytes(16).toString('hex');
  const key = crypto.scryptSync(String(plain).normalize('NFKC'), salt, 32).toString('hex');
  return `scrypt$${salt}$${key}`;
}

export function checkPassword(plain, stored) {
  const parts = String(stored ?? '').split('$');
  if (parts.length !== 3 || parts[0] !== 'scrypt') return false;
  let key;
  try {
    key = crypto.scryptSync(String(plain).normalize('NFKC'), parts[1], 32);
  } catch {
    return false;
  }
  const было = Buffer.from(parts[2], 'hex');
  // сравнение с постоянным временем: обычное подсказывает подбором,
  // на каком символе пароль разошёлся
  return key.length === было.length && crypto.timingSafeEqual(key, было);
}

function sign(data) {
  const secret = process.env.TICKET_SECRET;
  if (!secret) throw new Error('не задан TICKET_SECRET');
  return crypto.createHmac('sha256', secret).update(data).digest('base64url');
}

/** Пропуск на устройство, по умолчанию на 30 дней. Подписан, подменить нельзя. */
export function makeTicket(days = 30) {
  const body = Buffer.from(JSON.stringify({
    exp: Date.now() + days * 86_400_000,
  })).toString('base64url');
  return `${body}.${sign(body)}`;
}

export function readTicket(ticket) {
  const t = String(ticket ?? '');
  if (!t.includes('.')) return null;
  const [body, sig] = t.split('.');
  let good;
  try {
    good = Buffer.from(sign(body));
  } catch {
    return null;
  }
  const given = Buffer.from(String(sig));
  if (good.length !== given.length || !crypto.timingSafeEqual(good, given)) return null;
  try {
    const who = JSON.parse(Buffer.from(body, 'base64url').toString());
    return who.exp > Date.now() ? who : null;
  } catch {
    return null;
  }
}

/** Пропуск из заголовка Cookie. */
export function ticketFromRequest(request) {
  const raw = request.headers.get('cookie') || '';
  for (const part of raw.split(';')) {
    const [k, ...v] = part.trim().split('=');
    if (k === 'пропуск') return readTicket(decodeURIComponent(v.join('=')));
  }
  return null;
}

/**
 * Служебный вход для сборки.
 *
 * Прогон в GitHub Actions скачивает слепок прошлой сборки и сравнивает с новым -
 * это главная защита от тихих поломок (04.08.2026 дашборд показал дебиторку
 * 92,7 млн вместо 1,6 млн). Закрыть слепок наглухо значит убить эту защиту,
 * поэтому у сборки свой ключ, отдельный от пароля Анны.
 */
export function служебныйКлючВерен(request) {
  const дан = request.headers.get('x-build-token') || '';
  const нужен = process.env.BUILD_TOKEN || '';
  if (!нужен || !дан) return false;
  const a = Buffer.from(String(дан));
  const b = Buffer.from(String(нужен));
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

/** Ответ «сюда нельзя». Без подробностей: подсказывать нечего. */
export const нельзя = () =>
  new Response(JSON.stringify({ ошибка: 'нужен вход' }), {
    status: 401,
    headers: { 'content-type': 'application/json; charset=utf-8' },
  });
