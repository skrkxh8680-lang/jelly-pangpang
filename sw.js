/* 멧챠 젤리팡팡 — 오프라인 캐시용 서비스워커
   index.html(게임 본체)을 캐시해 네트워크 없이도 앱이 켜지게 한다.
   게임을 새로 올릴 때는 아래 CACHE 버전만 올리면 자동으로 새 파일을 받는다. */
const CACHE = 'jelly-pangpang-v143b';
const SHELL = ['./', './index.html', './manifest.webmanifest',
               './icon-192.png', './icon-512.png', './icon-180.png', './icon-maskable-512.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // 다른 도메인(폰트, PeerJS 대전 서버 등)은 캐시하지 않고 네트워크로 그대로 통과.
  if (url.origin !== self.location.origin) return;

  // 게임 본체는 '네트워크 우선, 실패하면 캐시' — 최신본을 받되 오프라인에서도 켜진다.
  e.respondWith(
    fetch(req)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
        return res;
      })
      .catch(() => caches.match(req).then((r) => r || caches.match('./index.html')))
  );
});
