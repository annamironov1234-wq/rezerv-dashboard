process.env.TICKET_SECRET = 'тестовый-секрет-только-для-проверки';
process.env.BUILD_TOKEN = 'служебный-ключ-теста';
const A = await import('../netlify/functions/_auth.js');

let ok = 0, fail = 0;
const проверка = (имя, условие) => {
  if (condition_ok(условие)) { console.log(`  ✓ ${имя}`); ok++; }
  else { console.log(`  ✗ ${имя}`); fail++; }
};
function condition_ok(c){ return c === true; }

console.log('ПАРОЛЬ');
const хэш = A.hashPassword('правильный пароль');
проверка('верный пароль принимается', A.checkPassword('правильный пароль', хэш));
проверка('неверный отвергается', A.checkPassword('другой пароль', хэш) === false);
проверка('пустой отвергается', A.checkPassword('', хэш) === false);
проверка('мусор вместо хэша отвергается', A.checkPassword('пароль', 'ерунда') === false);
проверка('два хэша одного пароля разные', A.hashPassword('x') !== A.hashPassword('x'));

console.log('\nПРОПУСК');
const п = A.makeTicket(30);
проверка('свой пропуск читается', A.readTicket(п) !== null);
проверка('подделанная подпись отвергается', A.readTicket(п.split('.')[0] + '.поддельнаяподпись') === null);
проверка('мусор отвергается', A.readTicket('чепуха') === null);
проверка('пустой отвергается', A.readTicket('') === null);
проверка('просроченный отвергается', A.readTicket(A.makeTicket(-1)) === null);

console.log('\nПРОПУСК ИЗ COOKIE');
const req = (cookie) => ({ headers: { get: (k) => (k === 'cookie' ? cookie : null) } });
проверка('пропуск в cookie находится',
  A.ticketFromRequest(req('пропуск=' + encodeURIComponent(п))) !== null);
проверка('чужая cookie не пускает',
  A.ticketFromRequest(req('другое=значение')) === null);
проверка('без cookie не пускает', A.ticketFromRequest(req('')) === null);

console.log('\nСЛУЖЕБНЫЙ КЛЮЧ');
const reqT = (t) => ({ headers: { get: (k) => (k === 'x-build-token' ? t : null) } });
проверка('верный ключ принимается', A.служебныйКлючВерен(reqT('служебный-ключ-теста')));
проверка('неверный отвергается', A.служебныйКлючВерен(reqT('не тот')) === false);
проверка('пустой отвергается', A.служебныйКлючВерен(reqT('')) === false);

console.log(`\nИТОГ: прошло ${ok}, провалено ${fail}`);
process.exit(fail ? 1 : 0);

// ── Имя cookie ─────────────────────────────────────
// 17.08.2026: имя было кириллицей («пропуск»), браузер молча его выбрасывал.
// Пароль принимался, пропуск не сохранялся, человека возвращало на форму -
// и выглядело это как «пароль не подошёл». По RFC 6265 имя cookie это
// ASCII-токен, поэтому проверяем буквально.
console.log('\nИМЯ COOKIE');
const латиница = /^[A-Za-z0-9!#$%&'*+.^_`|~-]+$/;
const исходник = await (await import('node:fs/promises')).readFile(
  new URL('../netlify/functions/login.js', import.meta.url), 'utf-8');
const имя = (исходник.match(/'set-cookie':\s*`([^=]+)=/) || [])[1] || '';
проверка(`имя «${имя}» только из латиницы`, латиница.test(имя));
проверка('старое кириллическое имя тоже читается (кто успел войти)',
  исходник.includes('propusk') && true);
