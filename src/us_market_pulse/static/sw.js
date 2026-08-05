/* Pulse Desk lightweight shell cache — HTML/auth pages always network-first. */
const CACHE = "pulse-desk-shell-v24";
const SHELL = [
  "/static/styles.css?v=20260805ak",
  "/static/app.js?v=20260805ak",
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

function isHtmlRequest(req, url) {
  if (req.mode === "navigate") return true;
  const accept = req.headers.get("accept") || "";
  if (accept.includes("text/html")) return true;
  // App routes (no file extension) are auth-sensitive documents
  if (!url.pathname.startsWith("/static/") && !url.pathname.includes(".")) {
    return true;
  }
  return false;
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/")) return;

  // Never serve cached HTML for / /login /settings etc. — session state changes
  if (isHtmlRequest(req, url)) {
    event.respondWith(
      fetch(req)
        .then((res) => res)
        .catch(async () => {
          const cached = await caches.match(req);
          return cached || Response.error();
        }),
    );
    return;
  }

  // Static assets: prefer cache, refresh in background
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
