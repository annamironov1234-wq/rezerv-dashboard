/**
 * Слепок цифр прошлой сборки.
 *
 * Два входа, и оба нужны:
 *   - пропуск Анны   - посмотреть глазами;
 *   - служебный ключ - его предъявляет прогон в GitHub Actions.
 *
 * Второй вход обязателен. Прогон скачивает этот слепок и сравнивает с новым:
 * так ловятся тихие поломки, когда все проверки зелёные, а цифра вранная
 * (04.08.2026, дебиторка 92,7 млн вместо 1,6 млн). Закрыть слепок наглухо
 * значит выключить эту защиту, а она главная.
 */
import { readFile } from 'node:fs/promises';
import { ticketFromRequest, служебныйКлючВерен, нельзя } from './_auth.js';

export default async (request) => {
  const свой = ticketFromRequest(request) || служебныйКлючВерен(request);
  if (!свой) return нельзя();

  try {
    const текст = await readFile(new URL('../../private/metrics.json', import.meta.url), 'utf-8');
    return new Response(текст, {
      status: 200,
      headers: {
        'content-type': 'application/json; charset=utf-8',
        'cache-control': 'private, no-store',
      },
    });
  } catch {
    // Первый прогон: слепка ещё нет. Это не ошибка, сборка просто пропустит
    // сравнение - так же, как раньше при недоступном файле.
    return new Response(JSON.stringify({ ошибка: 'слепка ещё нет' }), {
      status: 404,
      headers: { 'content-type': 'application/json; charset=utf-8' },
    });
  }
};
