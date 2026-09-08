// Matter Lab Service Worker v5 — cache dinamica moduli lazy (refactor matter.js)
const CACHE = 'matter-lab-v5';
const PRECACHE = ['/static/manifest.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(PRECACHE)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  if (e.request.url.includes('/v1/') || e.request.url.includes('/chiedi')) return;
  if (e.request.url.endsWith('/app') || e.request.url.includes('/app?')) return;

  // JS e CSS (core + moduli lazy matter-*.js): network-first, MA salva in cache la copia fresca
  // così i moduli sono disponibili OFFLINE dopo il primo caricamento online.
  const url = e.request.url;
  const isAsset = url.includes('/static/') && (url.includes('.js') || url.includes('.css'));
  if (isAsset) {
    e.respondWith(
      fetch(e.request).then(resp => {
        // salvo la copia fresca in cache (per l'offline)
        const copy = resp.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy)).catch(() => {});
        return resp;
      }).catch(() => caches.match(e.request))  // offline: servo dalla cache
    );
    return;
  }

  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});
