/**
 * Метка свежести: когда данные собирались в последний раз.
 *
 * Страница на телефоне спрашивает её мимо кэша при каждом возврате
 * в приложение и перезагружается, если сервер отдал дату свежее
 * (см. checkFresh в web/index.html). Файл крошечный, поэтому дёргать
 * его часто не жалко.
 *
 * Тоже за пропуском: сама по себе дата не тайна, но отвечать незнакомцу
 * "да, тут живёт дашборд, обновлён вчера" незачем.
 */
import { readFile } from 'node:fs/promises';
import { ticketFromRequest, нельзя } from './_auth.js';

export default async (request) => {
  if (!ticketFromRequest(request)) return нельзя();

  try {
    const текст = await readFile(new URL('../../private/stamp.txt', import.meta.url), 'utf-8');
    return new Response(текст, {
      status: 200,
      headers: {
        'content-type': 'text/plain; charset=utf-8',
        'cache-control': 'private, no-store',
      },
    });
  } catch {
    return new Response('', { status: 404 });
  }
};
