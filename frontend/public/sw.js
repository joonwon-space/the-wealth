/**
 * THE WEALTH Service Worker
 *
 * Strategies:
 * - Auth / SSE / Push API:  network only (never cache)
 * - GET /api/v1/portfolios*, /analytics*, /prices/{ticker}: NetworkFirst (3s timeout, 5min TTL)
 * - /_next/static/*, Pretendard font: StaleWhileRevalidate
 * - Image requests: CacheFirst (30d)
 * - Navigation fallback: /offline
 *
 * No precache manifest — we rely on runtime caching because Next 16 uses
 * Turbopack and the chunk filenames change per build. The SW itself is
 * versioned via SW_VERSION; bump it to invalidate caches.
 */

const SW_VERSION = "v1";
const API_CACHE = `wealth-api-${SW_VERSION}`;
const STATIC_CACHE = `wealth-static-${SW_VERSION}`;
const IMAGE_CACHE = `wealth-images-${SW_VERSION}`;
const PAGE_CACHE = `wealth-pages-${SW_VERSION}`;

const API_NETWORK_TIMEOUT_MS = 3000;
const API_TTL_MS = 5 * 60 * 1000;
const IMAGE_TTL_MS = 30 * 24 * 60 * 60 * 1000;

const OFFLINE_URL = "/offline";

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(PAGE_CACHE);
      try {
        await cache.add(new Request(OFFLINE_URL, { cache: "reload" }));
      } catch {
        // offline page not cached on first install — OK, fallback will refetch
      }
    })()
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      if (self.registration.navigationPreload) {
        await self.registration.navigationPreload.enable();
      }
      // Clean up old caches
      const keys = await caches.keys();
      await Promise.all(
        keys
          .filter(
            (k) =>
              !k.endsWith(`-${SW_VERSION}`) &&
              (k.startsWith("wealth-api-") ||
                k.startsWith("wealth-static-") ||
                k.startsWith("wealth-images-") ||
                k.startsWith("wealth-pages-"))
          )
          .map((k) => caches.delete(k))
      );
      await self.clients.claim();
    })()
  );
});

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

// ---------- routing ----------

function isBypass(url) {
  return (
    url.pathname.startsWith("/api/v1/auth") ||
    url.pathname.startsWith("/api/v1/prices/stream") ||
    url.pathname.startsWith("/api/v1/push")
  );
}

function isCacheableApi(url, method) {
  if (method !== "GET") return false;
  return (
    url.pathname.startsWith("/api/v1/portfolios") ||
    url.pathname.startsWith("/api/v1/analytics") ||
    /^\/api\/v1\/prices\/[^/]+$/.test(url.pathname)
  );
}

function isStaticAsset(url) {
  return (
    url.pathname.startsWith("/_next/static/") ||
    url.hostname === "cdn.jsdelivr.net"
  );
}

function isImage(request) {
  return request.destination === "image";
}

// ---------- strategies ----------

async function networkFirst(request, cacheName, timeoutMs, ttlMs) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  const timeoutPromise = new Promise((resolve) =>
    setTimeout(() => resolve(null), timeoutMs)
  );
  const networkPromise = fetch(request)
    .then((response) => {
      if (response && response.ok) {
        const clone = response.clone();
        const meta = new Headers(clone.headers);
        meta.set("sw-cached-at", String(Date.now()));
        cache.put(
          request,
          new Response(clone.body, {
            status: clone.status,
            statusText: clone.statusText,
            headers: meta,
          })
        );
      }
      return response;
    })
    .catch(() => null);

  const first = await Promise.race([networkPromise, timeoutPromise]);
  if (first) return first;

  if (cached) {
    const cachedAt = Number(cached.headers.get("sw-cached-at") || 0);
    if (!ttlMs || Date.now() - cachedAt < ttlMs) return cached;
    // stale but offline — still return so user sees something
    return cached;
  }
  // last attempt: await the network promise
  const fallback = await networkPromise;
  if (fallback) return fallback;
  return new Response(JSON.stringify({ error: "offline" }), {
    status: 503,
    headers: { "content-type": "application/json" },
  });
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  const networkPromise = fetch(request)
    .then((response) => {
      if (response && response.ok) {
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => null);
  return cached || (await networkPromise) || new Response("", { status: 504 });
}

async function cacheFirst(request, cacheName, ttlMs) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) {
    const cachedAt = Number(cached.headers.get("sw-cached-at") || 0);
    if (!ttlMs || Date.now() - cachedAt < ttlMs) return cached;
  }
  try {
    const response = await fetch(request);
    if (response && response.ok) {
      const clone = response.clone();
      const meta = new Headers(clone.headers);
      meta.set("sw-cached-at", String(Date.now()));
      cache.put(
        request,
        new Response(clone.body, {
          status: clone.status,
          statusText: clone.statusText,
          headers: meta,
        })
      );
    }
    return response;
  } catch {
    if (cached) return cached;
    return new Response("", { status: 504 });
  }
}

async function handleNavigation(event) {
  try {
    const preload = await event.preloadResponse;
    if (preload) return preload;
    return await fetch(event.request);
  } catch {
    const cache = await caches.open(PAGE_CACHE);
    const offline = await cache.match(OFFLINE_URL);
    if (offline) return offline;
    return new Response(
      "<h1>Offline</h1><p>네트워크에 연결할 수 없습니다.</p>",
      { status: 503, headers: { "content-type": "text/html; charset=utf-8" } }
    );
  }
}

// ---------- dispatch ----------

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET" && request.method !== "HEAD") return;

  const url = new URL(request.url);
  // Only same-origin or known CDNs
  const sameOrigin = url.origin === self.location.origin;
  const knownCdn = url.hostname === "cdn.jsdelivr.net";
  if (!sameOrigin && !knownCdn) return;

  if (isBypass(url)) return; // fall through to network

  if (request.mode === "navigate") {
    event.respondWith(handleNavigation(event));
    return;
  }

  if (isCacheableApi(url, request.method)) {
    event.respondWith(
      networkFirst(request, API_CACHE, API_NETWORK_TIMEOUT_MS, API_TTL_MS)
    );
    return;
  }

  if (isStaticAsset(url)) {
    event.respondWith(staleWhileRevalidate(request, STATIC_CACHE));
    return;
  }

  if (isImage(request)) {
    event.respondWith(cacheFirst(request, IMAGE_CACHE, IMAGE_TTL_MS));
    return;
  }
});

// ---------- push (Phase 5 will extend) ----------

self.addEventListener("push", (event) => {
  const payload = (() => {
    if (!event.data) return { title: "THE WEALTH", body: "새 알림이 있어요." };
    try {
      return event.data.json();
    } catch {
      return { title: "THE WEALTH", body: event.data.text() };
    }
  })();

  event.waitUntil(
    self.registration.showNotification(payload.title || "THE WEALTH", {
      body: payload.body || "",
      icon: "/icon-192.png",
      badge: "/icon-192.png",
      data: { url: payload.url || "/dashboard" },
      tag: payload.tag,
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = (event.notification.data && event.notification.data.url) || "/dashboard";
  event.waitUntil(
    (async () => {
      const allClients = await self.clients.matchAll({
        type: "window",
        includeUncontrolled: true,
      });
      for (const client of allClients) {
        if (client.url.includes(targetUrl) && "focus" in client) {
          return client.focus();
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow(targetUrl);
      }
      return undefined;
    })()
  );
});
