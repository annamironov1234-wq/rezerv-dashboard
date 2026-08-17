/**
 * Вход по паролю.
 *
 * Принимает пароль, сверяет с хэшем из переменной PASSWORD_HASH и ставит
 * пропуск на 30 дней. Пароль в открытом виде нигде не хранится - ни в коде,
 * ни в настройках, только его хэш.
 *
 * Задержка при неверном пароле: перебирать по сети становится бессмысленно.
 */
import { checkPassword, makeTicket } from './_auth.js';

const пауза = (мс) => new Promise((r) => setTimeout(r, мс));

export default async (request) => {
  if (request.method !== 'POST') {
    return new Response('только POST', { status: 405 });
  }

  const хэш = process.env.PASSWORD_HASH;
  if (!хэш) {
    return new Response(
      JSON.stringify({ ошибка: 'пароль ещё не задан, запустите setup/установить-пароль.sh' }),
      { status: 500, headers: { 'content-type': 'application/json; charset=utf-8' } },
    );
  }

  let пароль = '';
  try {
    пароль = (await request.json()).пароль ?? '';
  } catch {
    пароль = '';
  }

  if (!checkPassword(пароль, хэш)) {
    await пауза(1200);
    return new Response(JSON.stringify({ ошибка: 'неверный пароль' }), {
      status: 401,
      headers: { 'content-type': 'application/json; charset=utf-8' },
    });
  }

  const пропуск = makeTicket(30);
  return new Response(JSON.stringify({ ок: true }), {
    status: 200,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      // HttpOnly: пропуск не виден скриптам на странице
      // SameSite=Lax: не уедет на чужой сайт
      'set-cookie': `пропуск=${encodeURIComponent(пропуск)}; Path=/; Max-Age=${30 * 86400}; HttpOnly; Secure; SameSite=Lax`,
    },
  });
};
