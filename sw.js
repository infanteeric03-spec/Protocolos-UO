// Service worker de Protocolos UO: permite usar la web sin conexión.
// - Página (index.html): primero la red (para ver siempre la última versión
//   publicada); si no hay conexión o tarda más de 4 s, se usa la copia guardada.
// - PDF, iconos y manifest: se sirven desde la copia guardada y se actualizan
//   en segundo plano cuando hay conexión.
// Al cambiar la lista de archivos o la estrategia, sube el número de versión.
const CACHE = 'uo-v2';
const PRECACHE = [
  './',
  './index.html',
  './manifest.json',
  './icon-32.png',
  './icon-180.png',
  './icon-192.png',
  './icon-512.png',
  './pdf/absceso-periamigdalino.pdf',
  './pdf/asma.pdf',
  './pdf/celulitis.pdf',
  './pdf/dolor-toracico.pdf',
  './pdf/epoc.pdf',
  './pdf/espirometria-resumen-algoritmos.pdf',
  './pdf/espirometria-separ.pdf',
  './pdf/fibrilacion-auricular.pdf',
  './pdf/gastroenteritis.pdf',
  './pdf/gea-recomendaciones-alta.pdf',
  './pdf/hematuria.pdf',
  './pdf/hemorragia-digestiva-alta.pdf',
  './pdf/insuficiencia-cardiaca.pdf',
  './pdf/intoxicaciones.pdf',
  './pdf/neumonia.pdf',
  './pdf/pielonefritis.pdf',
  './pdf/policontusionado.pdf',
  './pdf/suboclusion.pdf',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => Promise.all(PRECACHE.map((u) => c.add(u).catch(() => null))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function networkFirst(req) {
  return new Promise((resolve) => {
    let done = false;
    const fallback = () => caches.match(req, { ignoreSearch: true })
      .then((r) => r || caches.match('./index.html'));
    const timer = setTimeout(() => { if (!done) fallback().then((r) => { if (r && !done) { done = true; resolve(r); } }); }, 4000);
    fetch(req).then((res) => {
      if (res && res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); }
      clearTimeout(timer);
      if (!done) { done = true; resolve(res); }
    }).catch(() => {
      clearTimeout(timer);
      fallback().then((r) => { if (!done) { done = true; resolve(r || Response.error()); } });
    });
  });
}

function staleWhileRevalidate(req) {
  return caches.open(CACHE).then((c) => c.match(req, { ignoreSearch: true }).then((cached) => {
    const net = fetch(req).then((res) => { if (res && res.ok) c.put(req, res.clone()); return res; }).catch(() => cached);
    return cached || net;
  }));
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  const isPage = req.mode === 'navigate' || url.pathname.endsWith('/') || url.pathname.endsWith('.html');
  event.respondWith(isPage ? networkFirst(req) : staleWhileRevalidate(req));
});
