/* Pulse Desk shell cache — static assets only. HTML/API always hit the network. */
const CACHE = "pulse-desk-shell-v153";
const SHELL = [
  "/static/styles.css?v=20260811a31",
  "/static/app.js?v=20260811a31",
  "/static/manifest.webmanifest",
  "/static/icons/apple-touch-icon.png",
  "/static/icons/icon-192.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(SHELL).catch(() => undefined)),
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))),
    ),
  );
  self.clients.claim();
});

function isVersionedStatic(url) {
  return url.pathname.startsWith("/static/") && url.searchParams.has("v");
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Never intercept HTML navigations or /api/* — SW timeouts were showing a
  // false "正在唤醒" screen while Render was still booting (45s+).
  if (url.pathname.startsWith("/api/")) return;
  if (req.mode === "navigate") return;
  const accept = req.headers.get("accept") || "";
  if (accept.includes("text/html")) return;
  if (!url.pathname.startsWith("/static/") && !url.pathname.includes(".")) return;

  if (isVersionedStatic(url)) {
    event.respondWith(
      fetch(req)
        .then((res) => {
          if (res && res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((cache) => cache.put(req, copy));
          }
          return res;
        })
        .catch(async () => (await caches.match(req)) || Response.error()),
    );
    return;
  }

  event.respondWith(
    caches.match(req).then((cached) => {
      const network = fetch(req)
        .then((res) => {
          if (res && res.ok && url.pathname.startsWith("/static/")) {
            const copy = res.clone();
            caches.open(CACHE).then((cache) => cache.put(req, copy));
          }
          return res;
        })
        .catch(() => cached);
      return cached || network;
    }),
  );
});
