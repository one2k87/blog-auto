// 서비스워커 - 아이폰 홈화면 설치(PWA) 및 오프라인 캐시
const CACHE = "adsense-blog-v1";
const ASSETS = [
  "./index.html",
  "./manifest.json",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/apple-touch-icon.png"
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  // latest.json 같은 데이터는 항상 네트워크 우선(최신 글 받기), 실패 시 캐시
  if (url.pathname.endsWith(".json")) {
    e.respondWith(
      fetch(e.request).then((r) => {
        const copy = r.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
        return r;
      }).catch(() => caches.match(e.request))
    );
    return;
  }
  // 앱 자원은 캐시 우선(오프라인에서도 열림)
  e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
});
