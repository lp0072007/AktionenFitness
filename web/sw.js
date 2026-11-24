// Service-Worker: Seite und Daten offline verfügbar machen (z. B. im Supermarkt ohne Netz).
// Seiten und Daten: zuerst Netz (damit neue Aktionen sofort da sind), sonst aus dem Speicher.
// Skripte, Stile, Bilder: sofort aus dem Speicher, im Hintergrund aktualisieren.
const VERSION = "af-v5";
const KERN = [
  "./", "index.html", "einkauf.html", "impressum.html", "datenschutz.html",
  "style.css", "einkauf.css", "app.js", "einkauf.js", "abgleich.js", "liste.js", "thema.js", "vorlieben.js", "zaehler.js",
  "manifest.webmanifest", "icons/icon-192.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(KERN)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((namen) => Promise.all(namen.filter((n) => n !== VERSION).map((n) => caches.delete(n))))
    .then(() => self.clients.claim()));
});

async function zuerstNetz(req) {
  const cache = await caches.open(VERSION);
  try {
    const antwort = await fetch(req);
    if (antwort.ok) cache.put(req, antwort.clone());
    return antwort;
  } catch {
    const gespeichert = await cache.match(req, { ignoreSearch: true });
    if (gespeichert) return gespeichert;
    if (req.mode === "navigate") return (await cache.match("index.html")) || Response.error();
    return new Response("", { status: 504, statusText: "offline" }); // z. B. fehlende Datendatei: leer, nicht die Startseite
  }
}

async function zuerstSpeicher(req, ereignis) {
  const cache = await caches.open(VERSION);
  const gespeichert = await cache.match(req);
  const neu = fetch(req).then((a) => { if (a.ok) cache.put(req, a.clone()); return a; }).catch(() => gespeichert);
  if (gespeichert) { ereignis.waitUntil(neu); return gespeichert; }
  return neu;
}

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return; // fremde Bilder: normal laden
  const seiteOderDaten = e.request.mode === "navigate" || /\/data\/[^/]+\.js(on)?$/.test(url.pathname);
  e.respondWith(seiteOderDaten ? zuerstNetz(e.request) : zuerstSpeicher(e.request, e));
});
