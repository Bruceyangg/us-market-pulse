/* Pulse Desk lightweight shell cache — HTML/auth pages always network-first. */
const CACHE = "pulse-desk-shell-v145";
const API_CACHE = "pulse-desk-api-v1";
const SHELL = [
  "/static/styles.css?v=20260811a23",
  "/static/app.js?v=20260811a23",
  "/static/manifest.webmanifest",
  "/static/icons/apple-touch-icon.png",
  "/static/icons/icon-192.png",
];
/** Soft sector desks: stale-while-revalidate window (ms). */
const API_SECTORS_MAX_AGE_MS = 90_000;

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
  // App routes (no file extension) are auth-sensitive documents
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

async function staleWhileRevalidateSectors(req) {
  const cache = await caches.open(API_CACHE);
  const cached = await cache.match(req);
  const network = fetch(req)
    .then((res) => {
      if (res && res.ok) {
        const copy = res.clone();
        cache.put(req, copy);
      }
      return res;
    })
    .catch(() => null);

  if (cached) {
    const cachedAt = Number(cached.headers.get("x-pulse-cached-at") || 0);
    const age = cachedAt ? Date.now() - cachedAt : 0;
    // Kick network refresh; serve cache immediately when still warm.
    void network.then(async (res) => {
      if (!res || !res.ok) return;
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
        /* ignore cache write races */
      }
    });
    if (!cachedAt || age < API_SECTORS_MAX_AGE_MS) {
      return cached;
    }
  }

  const fresh = await network;
  if (fresh && fresh.ok) {
    try {
      const body = await fresh.clone().arrayBuffer();
      const headers = new Headers(fresh.headers);
      headers.set("x-pulse-cached-at", String(Date.now()));
      await cache.put(
        req,
        new Response(body, {
          status: fresh.status,
          statusText: fresh.statusText,
          headers,
        }),
      );
    } catch (_) {
      /* ignore */
    }
    return fresh;
  }
  return cached || Response.error();
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Soft sector desks: stale-while-revalidate for snappy rank/chip switches.
  if (isSoftSectorsApi(url)) {
    event.respondWith(staleWhileRevalidateSectors(req));
    return;
  }

  // Other APIs stay network-only (quotes / auth-sensitive).
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

  // Versioned static (?v=): network-first so bumps apply immediately.
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

  // Other static assets: prefer cache, refresh in background
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
