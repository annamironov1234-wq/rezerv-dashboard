/* Service worker дашборда «Резерв Сил».
   Задача одна: иконка на экране «Домой» не должна показывать вчерашнюю копию.

   Стратегия «сначала сеть»: на каждый запрос сперва идём на сервер и отдаём
   свежее, а копию кладём в кэш. Кэш нужен ровно для одного случая — метро,
   самолёт, нет связи: тогда отдаём последнее, что видели, вместо белого экрана.
   Обратная стратегия (сначала кэш) как раз и давала залипшую страницу. */
const CACHE = 'rezerv-net-first-v1';

self.addEventListener('install', () => self.skipWaiting());          // не ждём закрытия старых вкладок
self.addEventListener('activate', e => e.waitUntil(
  caches.keys()
    .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))  // чистим старые версии
    .then(() => self.clients.claim())
));

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET' || !req.url.startsWith(self.location.origin)) return;
  e.respondWith(
    fetch(req)
      .then(res => {
        if (res && res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
        return res;
      })
      .catch(() => caches.match(req))     // сети нет: отдаём последнее известное
  );
});
