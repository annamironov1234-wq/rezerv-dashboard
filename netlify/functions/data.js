/**
 * Цифры дашборда. Отдаются только по пропуску.
 *
 * Файл лежит в private/ - каталог не публикуется как статика, добраться до
 * него можно только через эту функцию. Раньше цифры были вшиты прямо
 * в страницу, поэтому скачивались вообще без спроса (см. ЧТО-ДЕЛАЛИ, 17.08.2026).
 */
import { readFile } from 'node:fs/promises';
import { ticketFromRequest, нельзя } from './_auth.js';

export default async (request) => {
  if (!ticketFromRequest(request)) return нельзя();

  try {
    const текст = await readFile(new URL('../../private/data.json', import.meta.url), 'utf-8');
    return new Response(текст, {
      status: 200,
      headers: {
        'content-type': 'application/json; charset=utf-8',
        // не кэшировать нигде по дороге: это чужие деньги
        'cache-control': 'private, no-store',
      },
    });
  } catch (e) {
    return new Response(JSON.stringify({ ошибка: 'данные ещё не собраны' }), {
      status: 503,
      headers: { 'content-type': 'application/json; charset=utf-8' },
    });
  }
};
