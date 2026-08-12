/* Pulse Desk lightweight shell cache — HTML/auth pages always network-first. */
const CACHE = "pulse-desk-shell-v146";
const API_CACHE = "pulse-desk-api-v2";
const SHELL = [
  "/static/styles.css?v=20260811a24",
  "/static/app.js?v=20260811a24",
  "/static/manifest.webmanifest",
  "/static/icons/apple-touch-icon.png",
  "/static/icons/icon-192.png",
];
/** Soft sector desks: stale-while-revalidate window (ms). */
const API_SECTORS_MAX_AGE_MS = 90_000;
const NAV_TIMEOUT_MS = 10_000;
const API_TIMEOUT_MS = 12_000;

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
          .filter((k) => k !== CACHE && k !== API_CACHE)
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

function isSoftSectorsApi(url) {
  return (
    url.pathname === "/api/sectors" &&
    !url.searchParams.has("refresh") &&
    url.searchParams.has("sector")
  );
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

async function staleWhileRevalidateSectors(req) {
  const cache = await caches.open(API_CACHE);
  const cached = await cache.match(req);
  const networkPromise = fetchWithTimeout(req, API_TIMEOUT_MS)
    .then(async (res) => {
      if (res && res.ok) {
        try {
          const body = await res.clone().arrayBuffer();
          const headers = new Headers(res.headers);
          headers.set("x-pulse-cached-at", String(Date.now()));
          await cache.put(
            req,
            new Response(body, {
              status: res.status,
              statusText: res.statusText,
              headers,
            }),
          );
        } catch (_) {
          /* ignore cache races */
        }
      }
      return res;
    })
    .catch(() => null);

  if (cached) {
    const cachedAt = Number(cached.headers.get("x-pulse-cached-at") || 0);
    const age = cachedAt ? Date.now() - cachedAt : 0;
    void networkPromise;
    if (!cachedAt || age < API_SECTORS_MAX_AGE_MS) {
      return cached;
    }
  }

  const fresh = await networkPromise;
  if (fresh && fresh.ok) return fresh;
  if (cached) return cached;
  return new Response(JSON.stringify({ ok: false, error: "timeout" }), {
    status: 504,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Health / non-sector APIs: never intercept (avoid hanging the worker).
  if (url.pathname.startsWith("/api/")) {
    if (isSoftSectorsApi(url)) {
      event.respondWith(staleWhileRevalidateSectors(req));
    }
    return;
  }

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
