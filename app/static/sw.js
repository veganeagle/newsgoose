const CACHE_NAME = "newsgoose-v1";

const APP_SHELL = [
  "/dashboard",
  "/static/site.css",
  "/static/manifest.json"
];

// Install: cache app shell
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(APP_SHELL);
    })
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// Fetch strategy
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // only GET
  if (event.request.method !== "GET") return;

  // Dashboard = network first, fallback cache
  if (url.pathname === "/dashboard") {
    event.respondWith(
      fetch(event.request)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put("/dashboard", copy);
          });
          return res;
        })
        .catch(() => caches.match("/dashboard"))
    );
    return;
  }

  // Tiles = always network (fresh news)
  if (url.pathname.startsWith("/tile/")) {
    event.respondWith(
      fetch(event.request).catch(() => new Response("", { status: 204 }))
    );
    return;
  }

  // Static = cache first
  if (
    url.pathname.startsWith("/static/") ||
    url.pathname === "/sw.js"
  ) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        if (cached) return cached;

        return fetch(event.request).then((res) => {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, copy);
          });
          return res;
        });
      })
    );
  }
});