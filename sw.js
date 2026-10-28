// Offline-Cache. Bei jedem Deploy mit geänderten Dateien VERSION hochzählen.
const VERSION = 'essen-v2';
const KERN = ['./', 'index.html', 'gerichte.json', 'manifest.webmanifest', 'icons/apple-touch-icon.png', 'icons/icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(KERN)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== VERSION) await caches.delete(k);
    await self.clients.claim();
    await bilderVorladen();
  })());
});

// Alle Bilder aus gerichte.json in den Cache holen, damit die App komplett offline läuft.
async function bilderVorladen() {
  try {
    const cache = await caches.open(VERSION);
    const antwort = await cache.match('gerichte.json');
    if (!antwort) return;
    const daten = await antwort.json();
    const liste = Array.isArray(daten) ? daten : daten.gerichte;
    const pfade = liste.map(g => g.image).filter(p => p && p.startsWith('bilder/'));
    await Promise.allSettled(pfade.map(async p => { if (!(await cache.match(p))) await cache.add(p); }));
  } catch (e) { /* nächster Versuch beim nächsten Laden */ }
}

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  if (url.pathname.includes('/bilder/')) e.respondWith(cacheZuerst(req));
  else e.respondWith(netzZuerst(req, e));
});

async function cacheZuerst(req) {
  const cache = await caches.open(VERSION);
  const treffer = await cache.match(req);
  if (treffer) return treffer;
  const antwort = await fetch(req);
  if (antwort.ok) cache.put(req, antwort.clone());
  return antwort;
}

// Immer den neuesten Stand holen; ohne Netz (oder nach 4 s) den Cache nehmen.
async function netzZuerst(req, e) {
  const cache = await caches.open(VERSION);
  const url = new URL(req.url);
  const schluessel = url.origin + url.pathname; // ohne ?t=…, sonst wächst der Cache bei jedem Start
  try {
    const antwort = await Promise.race([
      // Navigations-Requests dürfen nicht mit Optionen neu gebaut werden, daher die URL.
      fetch(req.mode === 'navigate' ? req.url : req, { cache: 'no-cache' }),
      new Promise((_, nein) => setTimeout(() => nein(new Error('langsam')), 4000)),
    ]);
    if (antwort.ok) {
      await cache.put(schluessel, antwort.clone());
      if (url.pathname.endsWith('/gerichte.json')) e.waitUntil(bilderVorladen());
    }
    return antwort;
  } catch (err) {
    const r = await cache.match(schluessel) || (req.mode === 'navigate' ? await cache.match('index.html') : undefined);
    if (r) return r;
    throw err;
  }
}
