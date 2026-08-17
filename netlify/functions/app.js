/**
 * Сама страница дашборда. Тоже за пропуском.
 *
 * Почему не просто статикой: 17.08.2026 выяснилось, что в страницу
 * незаметно попали названия клиентов - в подсказках «откуда взялась цифра»
 * стояло «(ЗетТЕК/КЦХ/Клемер)». Чистить такие места по одному бесполезно:
 * следующая правка страницы занесёт что-нибудь ещё.
 *
 * Поэтому открытой оставлена только форма входа. Всё остальное - сюда,
 * и вопрос закрыт навсегда, что бы в страницу ни дописали потом.
 */
import { readFile } from 'node:fs/promises';
import { ticketFromRequest } from './_auth.js';

export default async (request) => {
  if (!ticketFromRequest(request)) {
    // Не пускаем, но и не пугаем: просто отправляем ко входу
    return new Response(null, { status: 302, headers: { location: '/' } });
  }

  try {
    const html = await readFile(new URL('../../private/app.html', import.meta.url), 'utf-8');
    return new Response(html, {
      status: 200,
      headers: {
        'content-type': 'text/html; charset=utf-8',
        'cache-control': 'private, no-store',
      },
    });
  } catch {
    return new Response('Дашборд ещё не собран.', {
      status: 503,
      headers: { 'content-type': 'text/plain; charset=utf-8' },
    });
  }
};
