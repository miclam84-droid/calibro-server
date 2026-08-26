// Matter Lab Service Worker v4 — cache invalidata 26/08/2026 (fix bottoni crea + flavour cliccabile)
const CACHE = 'matter-lab-v4';
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
  // Solo GET, non le API — /app e gli asset JS/CSS sempre network-first (mai dalla cache vecchia)
  if (e.request.method !== 'GET') return;
  if (e.request.url.includes('/v1/') || e.request.url.includes('/chiedi')) return;
  if (e.request.url.endsWith('/app') || e.request.url.includes('/app?')) return;
  // JS e CSS: sempre freschi dalla rete (mai servire una versione vecchia dei fix)
  if (e.request.url.includes('/static/matter.js') || e.request.url.includes('/static/matter.css')) {
    e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
    return;
  }
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});
