// SYNOP - Custom Service Worker
// Provides offline caching for static assets and API responses

const CACHE_NAME = "synop-v1";
const STATIC_CACHE = "synop-static-v1";
const API_CACHE = "synop-api-v1";

// Assets to cache on install
const STATIC_ASSETS = [
  "/",
  "/index.html",
  "/manifest.webmanifest",
];

// Install event - cache static assets
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== STATIC_CACHE && name !== API_CACHE)
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// Fetch event - serve from cache or network
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== "GET") return;

  // Skip chrome-extension and other non-http schemes
  if (!url.protocol.startsWith("http")) return;

  // API requests - Network First with cache fallback
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(networkFirstStrategy(request, API_CACHE));
    return;
  }

  // Static assets - Cache First
  if (
    request.destination === "script" ||
    request.destination === "style" ||
    request.destination === "image" ||
    request.destination === "font" ||
    url.pathname.endsWith(".js") ||
    url.pathname.endsWith(".css") ||
    url.pathname.endsWith(".png") ||
    url.pathname.endsWith(".svg") ||
    url.pathname.endsWith(".woff2")
  ) {
    event.respondWith(cacheFirstStrategy(request, STATIC_CACHE));
    return;
  }

  // HTML/Navigation - Network First with offline fallback
  if (request.mode === "navigate" || request.destination === "document") {
    event.respondWith(networkFirstStrategy(request, STATIC_CACHE));
    return;
  }

  // Default - Network First
  event.respondWith(networkFirstStrategy(request, STATIC_CACHE));
});

// Cache First Strategy - for static assets
async function cacheFirstStrategy(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  if (cached) {
    // Serve from cache, update in background
    fetchAndCache(request, cache);
    return cached;
  }

  // Not in cache, fetch from network
  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    // Return offline page for navigation requests
    if (request.mode === "navigate") {
      return caches.match("/");
    }
    throw new Error("Offline");
  }
}

// Network First Strategy - for API and dynamic content
async function networkFirstStrategy(request, cacheName) {
  const cache = await caches.open(cacheName);

  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await cache.match(request);
    if (cached) {
      return cached;
    }
    // Return offline page for navigation
    if (request.mode === "navigate") {
      return caches.match("/");
    }
    throw new Error("Offline");
  }
}

// Background update
async function fetchAndCache(request, cache) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      await cache.put(request, response);
    }
  } catch {
    // Ignore background update failures
  }
}

// Message handling for skip waiting
self.addEventListener("message", (event) => {
  if (event.data === "skipWaiting") {
    self.skipWaiting();
  }
});