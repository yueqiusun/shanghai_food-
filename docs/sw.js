const CACHE_NAME = 'shanghai-food-radar-v1.0.2';
const PRECACHE_URLS = [
  './',
  './index.html',
  './manifest.webmanifest',
  './apple-touch-icon.png',
  './icon-512.png',
  './icon.svg'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME && key.startsWith('shanghai-food-radar-'))
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Stale-While-Revalidate for same-origin static assets
  event.respondWith(
    caches.open(CACHE_NAME).then((cache) =>
      cache.match(req).then((cachedResp) => {
        const fetchPromise = fetch(req)
          .then((networkResp) => {
            if (networkResp && networkResp.status === 200) {
              cache.put(req, networkResp.clone());
            }
            return networkResp;
          })
          .catch(() => cachedResp);
        return cachedResp || fetchPromise;
      })
    )
  );
});
