const CACHE_NAME = 'media-server-v1';

self.addEventListener('install', e => {
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.delete(CACHE_NAME).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET') return;
  // HTML 页面始终走网络，不缓存
  if (url.pathname === '/' || url.pathname === '/admin' || url.pathname.startsWith('/play/')) return;
  // API、文件流不缓存
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/raw/') || url.pathname.startsWith('/thumb/') || url.pathname.startsWith('/upload')) return;

  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request).then(resp => {
      if (resp.ok && resp.type === 'basic') {
        const clone = resp.clone();
        caches.open(CACHE_NAME).then(c => c.put(e.request, clone));
      }
      return resp;
    }))
  );
});
