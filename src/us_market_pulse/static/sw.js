/* Pulse Desk lightweight shell cache — HTML/auth pages always network-first. */
const CACHE = "pulse-desk-shell-v149";
const SHELL = [
  "/static/styles.css?v=20260811a27",
  "/static/app.js?v=20260811a27",
  "/static/manifest.webmanifest",
  "/static/icons/apple-touch-icon.png",
  "/static/icons/icon-192.png",
];
/* Render free cold start often needs 30–60s; don't flash offline shell too early. */
const NAV_TIMEOUT_MS = 45_000;

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(SHELL).catch(() => undefined)),
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== CACHE)
          .map((k) => caches.delete(k)),
      ),
    ),
  );
  self.clients.claim();
});

function isHtmlRequest(req, url) {
  if (req.mode === "navigate") return true;
  const accept = req.headers.get("accept") || "";
  if (accept.includes("text/html")) return true;
  if (!url.pathname.startsWith("/static/") && !url.pathname.includes(".")) {
    return true;
  }
  return false;
}

function isVersionedStatic(url) {
  return url.pathname.startsWith("/static/") && url.searchParams.has("v");
}

function offlineShell() {
  const body = `<!doctype html><html lang="zh-CN"><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/><title>Pulse Desk</title><body style="margin:0;font:16px/1.5 system-ui,sans-serif;background:#102033;color:#e8eef6;display:grid;place-items:center;min-height:100vh;padding:2rem"><main style="max-width:28rem;text-align:center"><h1 style="margin:0 0 .5rem;font-size:1.4rem">Pulse Desk 正在唤醒</h1><p style="margin:0 0 1rem;opacity:.85">免费实例冷启动约需 30–60 秒，请稍后刷新。</p><button onclick="location.reload()" style="appearance:none;border:0;border-radius:10px;padding:.7rem 1.1rem;font:inherit;font-weight:700;background:#6aa8d4;color:#102033;cursor:pointer">重试</button></main></body></html>`;
  return new Response(body, {
    status: 503,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}

async function fetchWithTimeout(req, ms) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), ms);
  try {
    return await fetch(req, { signal: ctrl.signal });
  } finally {
    clearTimeout(timer);
  }
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Never intercept APIs — client memory/session cache + server budgets handle fluency.
  // Intercepting /api/sectors caused false 504s while Render was still waking.
  if (url.pathname.startsWith("/api/")) return;

  if (isHtmlRequest(req, url)) {
    event.respondWith(
      fetchWithTimeout(req, NAV_TIMEOUT_MS)
        .then((res) => res)
        .catch(async () => {
          const cached = await caches.match(req);
          return cached || offlineShell();
        }),
    );
    return;
  }

  if (isVersionedStatic(url)) {
    event.respondWith(
      fetchWithTimeout(req, NAV_TIMEOUT_MS)
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
