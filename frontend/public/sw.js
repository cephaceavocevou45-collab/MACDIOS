const CACHE_ACTUEL = "gestion-commerce-shell-v3";
const FICHIERS_HORS_LIGNE = ["/", "/offline.html", "/app-icon-192.png?v=2", "/app-icon-512.png?v=2", "/macdios-wordmark.png?v=2"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_ACTUEL).then((cache) => cache.addAll(FICHIERS_HORS_LIGNE)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((cles) => Promise.all(cles.filter((cle) => cle !== CACHE_ACTUEL).map((cle) => caches.delete(cle))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const requete = event.request;
  const url = new URL(requete.url);
  if (requete.method !== "GET" || url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;

  if (requete.mode === "navigate") {
    event.respondWith(fetch(requete).catch(async () => (
      await caches.match("/offline.html") || Response.error()
    )));
    return;
  }

  if (url.pathname.startsWith("/assets/") || url.pathname.startsWith("/app-icon")) {
    event.respondWith(caches.match(requete).then((miseEnCache) => {
      if (miseEnCache) return miseEnCache;
      return fetch(requete).then((reponse) => {
        if (reponse.ok) caches.open(CACHE_ACTUEL).then((cache) => cache.put(requete, reponse.clone()));
        return reponse;
      });
    }));
  }
});
