// Matter Lab Service Worker v1
const CACHE = 'matter-lab-v1';
const PRECACHE = ['/app', '/static/manifest.json'];

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
  // Solo GET, non le API
  if (e.request.method !== 'GET') return;
  if (e.request.url.includes('/v1/') || e.request.url.includes('/chiedi')) return;
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});
