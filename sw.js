// Service worker mínimo, solo para que Chrome/Samsung Internet consideren
// la app "instalable". No cachea nada de forma agresiva: cada apertura
// sigue pidiendo la página al servidor, así que las actualizaciones
// publicadas se ven de inmediato, sin necesidad de gestionar versiones
// de caché ni de purgar nada al publicar cambios.

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // Passthrough: deja que cada petición vaya normalmente a la red.
  event.respondWith(fetch(event.request));
});
