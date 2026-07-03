// Matter Service Worker — IN5
// Cache delle risorse statiche per uso offline parziale
const CACHE = 'matter-v1';
const STATIC = [
  '/',
  '/static/manifest.json',
  '/static/icon-192.png',
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC)));
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  // API calls: sempre dalla rete
  if(url.pathname.startsWith('/chiedi') ||
     url.pathname.startsWith('/v1/') ||
     url.pathname.startsWith('/home') ||
     url.pathname.startsWith('/disciplina') ||
     url.pathname.startsWith('/lezione') ||
     url.pathname.startsWith('/mappa')) {
    return; // passa alla rete
  }
  // risorse statiche: cache first
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});
