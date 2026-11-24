// AktionenFitness – Startseite ohne Framework.
// Daten: data/angebote.js (window.ANGEBOTE, Fitness-Auswahl) und data/aktionen.js (window.AKTIONEN, alle Aktionen),
// erzeugt mit `python -m aktionen.export`. Einkaufsliste: liste.js (Seitenleiste), Abgleich: abgleich.js.

const DATEN = window.ANGEBOTE || { regionen: [] };
const ALLE = window.AKTIONEN || { regionen: {}, ketten: {} };
const L = window.Einkaufsliste;
const VERLAUF = window.VERLAUF || { preise: {} };
const V = window.Vorlieben; // Kundenkarten, vegan/vegetarisch, Bio (⚙️ in der Kopfzeile, vorlieben.js)
const SPEICHER_EINST = "aktionenfitness.einstellungen.v1";
const SEITE = 60; // Karten pro "Mehr anzeigen"

// Kilopreis (bzw. Literpreis) aus Preis und Menge. Bei Mengenaktionen zählt der Aktionspreis.
function grundpreis(a, preis = a.preis) {
  if (a.pro_kg) return { wert: preis, einheit: "kg" };
  if (!a.menge) return null;
  if (a.einheit === "g") return { wert: (preis / a.menge) * 1000, einheit: "kg" };
  if (a.einheit === "ml") return { wert: (preis / a.menge) * 1000, einheit: "l" };
  if (a.einheit === "stk") return { wert: preis / a.menge, einheit: "Stück" };
  return null;
}

// Rabatt in Prozent: aus Normalpreis oder aus einem "-25%"-Hinweis des Händlers
function rabatt(a) {
  for (const t of a.aktion ?? []) {
    const m = /-\s*(\d+)\s*%/.exec(t);
    if (m) return Number(m[1]);
    const g = /(\d+)\s*\+\s*(\d+)\s*gratis/i.exec(t); // "3+3 GRATIS" = 50 %
    if (g) return (Number(g[2]) / (Number(g[1]) + Number(g[2]))) * 100;
  }
  // Mengenaktionen ("ab 6 Stück") nicht mit dem Einzelpreis vergleichen – das wäre zu hoch
  if (a.normalpreis && a.normalpreis > a.preis && !a.ab_menge) return (1 - a.preis / a.normalpreis) * 100;
  return 0;
}

const SORTIERUNG = {
  // Kilo-/Literpreis aufsteigend, dann Stückpreise, Angebote ohne Menge ans Ende
  kilopreis(a, b) {
    const rang = (g) => (!g ? 2 : g.einheit === "Stück" ? 1 : 0);
    const ga = grundpreis(a), gb = grundpreis(b);
    return rang(ga) - rang(gb) || (ga?.wert ?? 0) - (gb?.wert ?? 0);
  },
  rabatt: (a, b) => rabatt(b) - rabatt(a),
  preis: (a, b) => a.preis - b.preis,
};

// ---------- Zustand ----------
const zustand = {
  ansicht: "fitness", // "fitness" | "alle"
  region: null,
  kette: "",
  suche: "",
  sortierung: "kilopreis",
  sichtbar: SEITE,
};

function laden(schluessel, standard) {
  try { return JSON.parse(localStorage.getItem(schluessel)) ?? standard; } catch { return standard; }
}
function speichern(schluessel, wert) {
  try { localStorage.setItem(schluessel, JSON.stringify(wert)); } catch { /* privater Modus */ }
}

// ---------- Hilfen ----------
const $ = (sel) => document.querySelector(sel);
const euro = (x) => x.toLocaleString("de-AT", { style: "currency", currency: "EUR" });
const zahl = (x, stellen = 0) => x.toLocaleString("de-AT", { maximumFractionDigits: stellen, minimumFractionDigits: stellen });
const KETTEN = L.KETTEN;
const LANDESWEIT = ["lidl", "hofer", "penny", "billa", "mpreis", "dm"]; // ein Preis für alle Märkte der Kette
const WOCHENTAG = (iso) => new Date(iso + "T00:00:00").toLocaleDateString("de-AT", { weekday: "short" });
const datum = (iso) => (iso ? new Date(iso + "T00:00:00").toLocaleDateString("de-AT", { day: "2-digit", month: "2-digit" }) : "");
const heuteIso = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);

function mengeText(a) {
  if (a.pro_kg) return "Preis per kg";
  if (!a.menge) return "";
  if (a.einheit === "stk") return `${zahl(a.menge)} Stück`;
  if (a.einheit === "ml") return a.menge >= 1000 ? `${zahl(a.menge / 1000, 2)} l` : `${zahl(a.menge)} ml`;
  return a.menge >= 1000 ? `${zahl(a.menge / 1000, 2)} kg` : `${zahl(a.menge)} g`;
}

function aktuelleRegion() {
  return DATEN.regionen.find((r) => r.region === zustand.region) || DATEN.regionen[0];
}

// ---------- Angebote ----------
// Alle Listen laufen durch die Einstellungen: Filter (vegan, Bio …) und Kartenpreise
function fitnessAngebote() {
  return V.anwenden(fitnessRoh());
}
function fitnessRoh() {
  const r = aktuelleRegion();
  return [...(r?.angebote ?? []), ...LANDESWEIT.flatMap((k) => DATEN[k]?.angebote ?? [])];
}

// Bilder der Fitness-Angebote (Flugblatt-Ausschnitte) auch in "Alle Aktionen" verwenden
let _bilder;
function bildFuer(a) {
  // Fitness-Angebote ohne eigenes Bild (Export --ohne-bilder) bekommen das Händlerbild aus "Alle Aktionen"
  _bilder ??= new Map([...Object.values(ALLE.regionen).flatMap((r) => r.angebote), ...Object.values(ALLE.ketten).flat(),
    ...fitnessRoh(), ...DATEN.regionen.flatMap((r) => r.angebote)].filter((x) => x.bild).map((x) => [x.id, x.bild]));
  return a.bild || _bilder.get(a.id);
}

// Alle Aktionen (für "Alle Aktionen" und den Abgleich der Einkaufsliste)
function alleAktionen() {
  const region = ALLE.regionen[zustand.region] ?? Object.values(ALLE.regionen)[0];
  return V.anwenden([...(region?.angebote ?? []), ...Object.values(ALLE.ketten).flat()]);
}

function angeboteDerAnsicht() {
  return zustand.ansicht === "alle" ? alleAktionen() : fitnessAngebote();
}

function gefilterteAngebote() {
  const q = zustand.suche.trim().toLowerCase();
  return angeboteDerAnsicht()
    .filter((a) => !zustand.kette || a.kette === zustand.kette)
    .filter((a) => !q || `${a.name} ${a.kategorie ?? ""} ${a.beschreibung ?? ""}`.toLowerCase().includes(q))
    .sort(SORTIERUNG[zustand.sortierung] ?? SORTIERUNG.kilopreis);
}

function karteBauen(a, rang) {
  const k = $("#kartenVorlage").content.firstElementChild.cloneNode(true);
  k.dataset.id = a.id;
  if (rang <= 3 && zustand.sortierung === "kilopreis" && zustand.ansicht === "fitness") {
    const r = document.createElement("span");
    r.className = "rang";
    r.textContent = rang;
    r.title = `Platz ${rang}`;
    k.prepend(r);
  }
  const bild = L.sichereUrl(bildFuer(a));
  if (bild) {
    const knopfBild = k.querySelector(".karte__bild");
    const img = knopfBild.querySelector("img");
    img.src = bild;
    img.alt = a.name;
    img.addEventListener("error", () => (knopfBild.hidden = true)); // Bilder fehlen, wenn ohne Export geklont
    knopfBild.hidden = false;
    knopfBild.addEventListener("click", () => bildZeigen(a, bild));
  }
  const z = k.querySelector(".zuordnung");
  if (a.zuordnung === "geprueft") {
    z.textContent = "✓ Preis passt zum Grundpreis im Flugblatt";
    z.className = "zuordnung zuordnung--ok";
  } else if (a.zuordnung === "unsicher") {
    z.textContent = "⚠ Zuordnung unsicher – bitte im Flugblatt prüfen";
    z.className = "zuordnung zuordnung--warn";
  } else z.remove();

  // Kategorie: Fitness-Gruppe ("Skyr") bzw. letzte Stufe der Händler-Kategorie ("Joghurt & Desserts")
  const kat = k.querySelector(".badge--kat");
  const katText = zustand.ansicht === "fitness" ? a.kategorie : a.kategorie?.split(">").pop().trim();
  if (katText) kat.textContent = katText; else kat.remove();
  const kette = k.querySelector(".badge--kette");
  kette.textContent = KETTEN[a.kette] ?? a.kette;
  kette.classList.add(`badge--${a.kette}`);

  const quelle = k.querySelector(".karte__seite");
  const url = L.sichereUrl(a.url);
  if (url) {
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = `${new URL(url).hostname.replace(/^www\./, "")} ↗`;
    quelle.replaceChildren(link);
  } else if (a.seite) quelle.textContent = `Flugblatt S. ${a.seite}`;

  // Gültigkeit: pro Angebot, Spar = Zeitraum des Flugblatts der Region
  const gueltig = k.querySelector(".karte__gueltig");
  const region = aktuelleRegion();
  const von = a.gueltig_von ?? (a.kette === "spar" ? region?.gueltig_von : null);
  const bis = a.gueltig_bis ?? (a.kette === "spar" ? region?.gueltig_bis : null);
  // Stand des jeweiligen Geschäfts (sparsamer Lauf: nicht jedes Geschäft wird jeden Tag neu geladen)
  const standIso = DATEN[a.kette]?.stand ?? DATEN.erstellt;
  const stand = standIso ? new Date(standIso).toLocaleDateString("de-AT") : "–";
  if (von) {
    const zukunft = von > heuteIso();
    gueltig.textContent = `${zukunft ? "⏳ erst ab" : "📅 gültig"} ${WOCHENTAG(von)} ${datum(von)}` +
      (bis ? ` – ${WOCHENTAG(bis)} ${datum(bis)}` : "");
    gueltig.classList.toggle("karte__gueltig--zukunft", zukunft);
  } else if (a.kette === "dm") gueltig.textContent = `💶 dm-Dauerpreis (Stand ${stand})`;
  else if (a.kette === "billa") gueltig.textContent = `📅 aktuell im BILLA-Shop (Stand ${stand})`;
  else if (a.kette === "mpreis") gueltig.textContent = `📅 aktuell bei MPreis (Stand ${stand})`;
  else gueltig.textContent = "📅 Gültigkeit siehe Flugblatt";

  verlaufZeigen(k.querySelector(".verlauf"), a);
  k.querySelector(".karte__name").textContent = a.name;
  k.querySelector(".karte__menge").textContent = mengeText(a);
  k.querySelector(".preis").textContent = euro(a.preis);
  if (a.normalpreis && a.normalpreis > a.preis) k.querySelector(".normalpreis").textContent = euro(a.normalpreis);

  const bed = [];
  if (a.karte) bed.push(`💳 Preis mit ${a.karte} (ohne Karte ${euro(a.ohne_karte)})`);
  if (a.ab_menge) bed.push(`gilt ab ${a.ab_menge} Stück${a.normalpreis ? ` (1 Stk. ${euro(a.normalpreis)})` : ""}`);
  if (a.zusatzpreis) bed.push(`${V.zusatzName(a)}: ${euro(a.zusatzpreis)}`);
  k.querySelector(".karte__bedingung").textContent = bed.join(" · ");
  if (a.karte) k.querySelector(".preis").classList.add("preis--karte");

  const akt = k.querySelector(".karte__aktionen");
  for (const t of a.aktion ?? []) {
    const b = document.createElement("span");
    b.className = "badge badge--aktion";
    b.textContent = t;
    akt.append(b);
  }

  const gp = grundpreis(a);
  const kp = k.querySelector(".kilopreis");
  if (gp) {
    kp.querySelector(".kilopreis__wert").textContent = `${euro(gp.wert)} / ${gp.einheit}`;
    kp.querySelector(".kilopreis__label").textContent =
      gp.einheit === "kg" ? "Kilopreis" : gp.einheit === "l" ? "Literpreis" : "Stückpreis";
    const extra = [];
    if (a.ab_menge) extra.push(`ab ${a.ab_menge} Stück`);
    const gz = a.zusatzpreis ? grundpreis(a, a.zusatzpreis) : null;
    if (gz) extra.push(`${V.zusatzName(a)}: ${euro(gz.wert)} / ${gz.einheit}`);
    kp.querySelector(".kilopreis__extra").textContent = extra.join(" · ");
  } else kp.remove();

  const knopf = k.querySelector(".karte__knopf");
  knopfAktualisieren(knopf, a.id);
  knopf.addEventListener("click", () => L.angebotHinzufuegen(a));
  const stern = k.querySelector(".karte__merken");
  sternAktualisieren(stern, a.name);
  stern.addEventListener("click", () => {
    merkUmschalten(a.name);
    document.querySelectorAll(".karte").forEach((x) => sternAktualisieren(x.querySelector(".karte__merken"), x.querySelector(".karte__name").textContent));
  });
  return k;
}

// ---------- Merkliste: Produkte, die man regelmäßig kauft ----------
const SPEICHER_MERK = "aktionenfitness.merkliste.v1";
let merkliste = laden(SPEICHER_MERK, []);
if (!Array.isArray(merkliste)) merkliste = [];
const gemerkt = (name) => merkliste.some((m) => m.toLowerCase() === name.toLowerCase());

function merkSpeichern() { speichern(SPEICHER_MERK, merkliste); merkZeichnen(); merkDialogZeichnen(); }
function merkUmschalten(name) {
  merkliste = gemerkt(name) ? merkliste.filter((m) => m.toLowerCase() !== name.toLowerCase()) : [...merkliste, name];
  merkSpeichern();
}
function sternAktualisieren(knopf, name) {
  const an = gemerkt(name);
  knopf.textContent = an ? "★" : "☆";
  knopf.setAttribute("aria-pressed", String(an));
  knopf.setAttribute("aria-label", an ? `${name} nicht mehr merken` : `${name} merken`);
  knopf.classList.toggle("ist-gemerkt", an);
}

// Oben auf der Startseite: was von der Merkliste gerade in Aktion ist (günstigster passender Treffer)
function merkZeichnen() {
  const box = $("#merk");
  box.hidden = merkliste.length === 0;
  if (box.hidden) return;
  const eintraege = merkliste.map((m) => window.Abgleich.parseZeile(m)).filter(Boolean);
  const r = window.Abgleich.auswerten(eintraege, alleAktionen(), { tag: heuteIso() });
  const wahl = new Map();
  for (const xs of Object.values(r.aufteilung)) for (const x of xs) wahl.set(x.eintrag, x.treffer);
  const inAktion = eintraege.filter((e) => wahl.has(e));
  $("#merkInfo").textContent = `${inAktion.length} von ${eintraege.length} gerade in Aktion`;
  $("#merkChips").replaceChildren(...[...inAktion, ...eintraege.filter((e) => !wahl.has(e))].map((e) => {
    const t = wahl.get(e);
    const b = document.createElement("button");
    b.type = "button";
    b.className = "merk-chip" + (t ? "" : " merk-chip--aus");
    const name = document.createElement("span");
    name.className = "merk-chip__name";
    name.textContent = e.name;
    b.append(name);
    if (t) {
      b.append(L.badge(t.angebot.kette), document.createTextNode(` ${euro(t.angebot.preis)}`));
      b.title = t.angebot.name;
    } else b.append(document.createTextNode(" – keine Aktion"));
    b.addEventListener("click", () => { // passende Angebote anzeigen
      ansichtSetzen("alle");
      $("#suche").value = e.name;
      zustand.suche = e.name;
      zustand.kette = ""; auswahlSetzen("kette", "");
      neuZeichnen();
      $("#zielInfo").scrollIntoView({ behavior: "smooth", block: "start" });
    });
    return b;
  }));
}

function merkDialogZeichnen() {
  $("#merkListe").replaceChildren(...merkliste.map((m) => {
    const li = document.createElement("li");
    const t = document.createElement("span");
    t.textContent = m;
    const weg = document.createElement("button");
    weg.type = "button";
    weg.className = "icon-knopf ek-vorschau__weg";
    weg.textContent = "✕";
    weg.setAttribute("aria-label", `${m} entfernen`);
    weg.addEventListener("click", () => merkUmschalten(m));
    li.append(t, weg);
    return li;
  }));
  document.querySelectorAll(".karte").forEach((x) => sternAktualisieren(x.querySelector(".karte__merken"), x.querySelector(".karte__name").textContent));
}

// ---------- Preisverlauf (data/verlauf.js, aus python -m aktionen.export) ----------
const SVG = "http://www.w3.org/2000/svg";
function minikurve(eintraege) {
  const preise = eintraege.map((e) => e[1]);
  const lo = Math.min(...preise), hi = Math.max(...preise), b = 64, h = 18;
  const pkt = preise.map((p, i) => [
    preise.length === 1 ? b / 2 : (i * (b - 4)) / (preise.length - 1) + 2,
    hi === lo ? h / 2 : 2 + ((hi - p) * (h - 4)) / (hi - lo),
  ]);
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("viewBox", `0 0 ${b} ${h}`);
  svg.setAttribute("width", b);
  svg.setAttribute("height", h);
  svg.setAttribute("aria-hidden", "true");
  svg.classList.add("verlauf__kurve");
  const linie = document.createElementNS(SVG, "polyline");
  linie.setAttribute("points", pkt.map((p) => p.join(",")).join(" "));
  const punkt = document.createElementNS(SVG, "circle");
  punkt.setAttribute("cx", pkt.at(-1)[0]);
  punkt.setAttribute("cy", pkt.at(-1)[1]);
  punkt.setAttribute("r", 2.2);
  svg.append(linie, punkt);
  return svg;
}

function verlaufZeigen(el, a) {
  const eintraege = VERLAUF.preise[a.vk || a.id];
  const frueher = eintraege?.filter(([d]) => d < (VERLAUF.stand ?? heuteIso())) ?? [];
  if (!frueher.length) return el.remove();
  const tief = frueher.reduce((m, e) => (e[1] < m[1] ? e : m));
  const seit = datum(eintraege[0][0]);
  const preis = a.ohne_karte ?? a.preis; // Verlauf speichert Preise ohne Karte
  if (preis < tief[1] - 0.005) {
    el.textContent = `🔥 Tiefster Preis seit ${seit}`;
    el.classList.add("verlauf--tief");
  } else if (preis <= tief[1] + 0.005) {
    el.textContent = `👍 So günstig wie am ${datum(tief[0])}`;
  } else {
    el.textContent = `📉 Am ${datum(tief[0])} schon ${euro(tief[1])}`;
    el.classList.add("verlauf--teurer");
  }
  el.title = eintraege.map(([d, p]) => `${datum(d)}: ${euro(p)}`).join("\n");
  el.prepend(minikurve([...frueher, [VERLAUF.stand, preis]]), " ");
}

function knopfAktualisieren(knopf, id) {
  const n = L.anzahlVon(id);
  knopf.textContent = n ? `✓ ${n} auf der Liste` : "+ Liste";
  knopf.classList.toggle("ist-drauf", !!n);
}

// Gefilterte Liste merken, damit beim Nachladen nicht alles neu gezeichnet werden muss
let aktuelleListe = [];

function angeboteZeichnen() {
  aktuelleListe = gefilterteAngebote();
  const gezeigt = aktuelleListe.slice(0, zustand.sichtbar);
  $("#karten").replaceChildren(...gezeigt.map((a, i) => karteBauen(a, i + 1)));
  $("#leer").hidden = aktuelleListe.length > 0;
  mehrAktualisieren();
  const art = zustand.ansicht === "alle" ? "Aktionen" : "Fitness-Angebote";
  const sortText = { kilopreis: "nach Kilopreis – günstigstes zuerst", rabatt: "nach Rabatt – höchster zuerst", preis: "nach Preis" };
  const einst = V.zusammenfassung();
  $("#zielInfo").textContent = `${zahl(aktuelleListe.length)} ${art} · sortiert ${sortText[zustand.sortierung]}` +
    (einst ? ` · ${einst}` : "");
}

// Nächste Karten unten anhängen (beim Scrollen automatisch, sonst per Knopf)
function nachladen() {
  const schon = $("#karten").children.length;
  if (schon >= aktuelleListe.length) return;
  zustand.sichtbar = schon + SEITE;
  const neu = aktuelleListe.slice(schon, zustand.sichtbar);
  $("#karten").append(...neu.map((a, i) => karteBauen(a, schon + i + 1)));
  mehrAktualisieren();
}

function mehrAktualisieren() {
  const rest = aktuelleListe.length - $("#karten").children.length;
  $("#mehr").hidden = rest <= 0;
  $("#mehr").textContent = `Mehr anzeigen (${zahl(rest)} weitere)`;
  $("#mehrInfo").textContent = rest > 0 ? "oder am Ende weiter nach unten ziehen"
    : aktuelleListe.length > SEITE ? `Alle ${zahl(aktuelleListe.length)} angezeigt` : "";
  $("#mehrZug").hidden = rest <= 0;
}

// Am Seitenende "kräftig weiterscrollen" (Mausrad) bzw. weiter nach oben wischen (Handy) lädt die nächsten Karten.
// So bleibt das Seitenende mit Impressum erreichbar, man muss aber nicht unbedingt auf den Knopf tippen.
function weiterZiehenEinrichten() {
  // Bewusst schwergängig: ein schneller Wisch, der nur zufällig unten ankommt, lädt nichts nach.
  const SCHWELLE_RAD = 900;   // Mausrad/Touchpad: so viel Scrollen über das Ende hinaus
  const SCHWELLE_WISCH = 420; // Handy: so weit mit dem Finger weiterziehen
  const PAUSE = 600;          // erst zählen, wenn man schon so lange (ms) am Ende ist
  const MAX_SCHRITT = 40;     // Schwung (Trägheit) zählt pro Ereignis höchstens so viel
  let zug = 0, ruhe, schwelle = SCHWELLE_RAD, endeSeit = null;
  const amEnde = () => window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4;
  const anzeigen = () => $("#mehrZug").style.setProperty("--zug", Math.min(1, zug / schwelle));
  const zuruecksetzen = () => { zug = 0; anzeigen(); };
  window.addEventListener("scroll", () => {
    if (amEnde()) endeSeit ??= Date.now(); else { endeSeit = null; zuruecksetzen(); }
  }, { passive: true });
  const ziehen = (px, grenze) => {
    if ($("#mehr").hidden || !amEnde()) return zuruecksetzen();
    endeSeit ??= Date.now();
    if (Date.now() - endeSeit < PAUSE) return;   // gerade erst unten angekommen
    schwelle = grenze;
    zug += Math.min(px, MAX_SCHRITT);
    anzeigen();
    clearTimeout(ruhe);
    ruhe = setTimeout(zuruecksetzen, 400); // kurz loslassen setzt zurück
    if (zug >= schwelle) { zuruecksetzen(); endeSeit = null; nachladen(); }
  };
  window.addEventListener("wheel", (e) => { if (e.deltaY > 0) ziehen(e.deltaY, SCHWELLE_RAD); }, { passive: true });
  let startY = null;
  window.addEventListener("touchstart", (e) => { startY = amEnde() ? e.touches[0].clientY : null; }, { passive: true });
  window.addEventListener("touchmove", (e) => {
    if (startY === null) return;
    const y = e.touches[0].clientY;
    if (startY - y > 0) ziehen(startY - y, SCHWELLE_WISCH);
    startY = y;
  }, { passive: true });
  window.addEventListener("touchend", () => { startY = null; }, { passive: true });
}

function bildZeigen(a, bild) {
  const d = $("#grossBild");
  d.querySelector("img").src = bild;
  d.querySelector("img").alt = a.name;
  d.querySelector(".gross__text").textContent = a.seite ? `${a.name} – Flugblatt Seite ${a.seite}` : a.name;
  d.showModal();
}

// ---------- Einkaufsliste (Seitenleiste) ----------
let letzterFokus = null;
function listeOeffnen(offen) {
  const s = $("#schublade");
  s.classList.toggle("offen", offen);
  s.inert = !offen;
  $("#schleier").classList.toggle("offen", offen);
  document.body.classList.toggle("schublade-offen", offen);
  $("#listeOeffnen").setAttribute("aria-expanded", String(offen));
  if (offen) {
    letzterFokus = document.activeElement;
    listeZeichnen();
    setTimeout(() => $("#neu").focus({ preventScroll: true }), 50);
  } else letzterFokus?.focus?.();
}

let letztesErgebnis = null;
function listeZeichnen() {
  const zeilen = L.zeilen;
  $("#listeZaehler").textContent = zeilen.length;
  document.querySelectorAll(".karte").forEach((k) => knopfAktualisieren(k.querySelector(".karte__knopf"), k.dataset.id));
  if (!$("#schublade").classList.contains("offen")) return; // Abgleich nur rechnen, wenn man ihn sieht

  const angebote = alleAktionen();
  const ergebnis = L.auswerten(angebote, { tag: heuteIso() });
  letztesErgebnis = ergebnis;
  const erledigt = zeilen.filter((z) => z.erledigt).length;
  $("#erledigtZaehler").textContent = zeilen.length ? `${erledigt} / ${zeilen.length} erledigt` : "";
  $("#hakenWeg").hidden = $("#erledigteWeg").hidden = erledigt === 0;
  $("#listeLeer").hidden = zeilen.length > 0;
  $("#listeAktionen").hidden = zeilen.length === 0;
  L.zeichnen($("#vorschau"), ergebnis, { angebote, tag: heuteIso(), mitDaten: !!ALLE.erstellt, zeigen: angebotZeigen });
  ergebnisZeichnen(ergebnis);
  kopierenZeichnen(ergebnis);
}

// ---------- Kopieren für die Notizen-App ----------
const kopierWahl = new Set(); // gewählte Geschäfte, leer = alle
function kopierOptionen() {
  return { ketten: kopierWahl, ohneAktion: $("#kopierOhne").checked, erledigte: $("#kopierErledigt").checked };
}
function kopierenZeichnen(ergebnis) {
  const box = $("#sbKopieren");
  box.hidden = ergebnis.paare.length === 0;
  if (box.hidden) return;
  const anzahl = {};
  for (const [k, xs] of Object.entries(ergebnis.r.aufteilung)) anzahl[k] = xs.length;
  for (const k of [...kopierWahl]) if (!anzahl[k]) kopierWahl.delete(k); // Geschäft nicht mehr dabei
  const chip = (kette, text) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "chip";
    b.textContent = text;
    b.setAttribute("aria-pressed", String(kette ? kopierWahl.has(kette) : kopierWahl.size === 0));
    b.addEventListener("click", () => {
      if (!kette) kopierWahl.clear();
      else if (kopierWahl.has(kette)) kopierWahl.delete(kette);
      else kopierWahl.add(kette);
      kopierenZeichnen(ergebnis);
    });
    return b;
  };
  $("#kopierKetten").replaceChildren(chip("", "Alle"),
    ...Object.keys(anzahl).sort((a, b) => anzahl[b] - anzahl[a]).map((k) => chip(k, `${KETTEN[k] ?? k} (${anzahl[k]})`)));
  const text = L.alsNotiz(ergebnis, kopierOptionen());
  $("#kopierVorschau").textContent = text || "– nichts ausgewählt –";
  $("#listeKopieren").disabled = !text;
}

// Aus der Liste zu einer Aktion springen (Spar: keine Händlerseite -> Karte auf der Seite zeigen)
function angebotZeigen(a) {
  listeOeffnen(false);
  ansichtSetzen("alle");
  zustand.kette = a.kette; auswahlSetzen("kette", a.kette);
  zustand.suche = a.name; $("#suche").value = a.name;
  neuZeichnen();
  const karte = document.querySelector(`.karte[data-id="${CSS.escape(a.id)}"]`) ?? document.querySelector(".karte");
  if (!karte) return;
  karte.scrollIntoView({ behavior: "smooth", block: "center" });
  karte.classList.add("karte--markiert");
  setTimeout(() => karte.classList.remove("karte--markiert"), 2200);
}

// Kurzfassung unter der Liste: wo einkaufen, was kostet es zusammen
function ergebnisZeichnen({ paare, r }) {
  const box = $("#sbErgebnis");
  box.hidden = paare.length === 0;
  if (!paare.length) return;
  box.replaceChildren();
  const h = document.createElement("h3");
  if (!ALLE.erstellt) {
    h.textContent = "⚠ Keine Aktionsdaten – zuerst python -m aktionen.export ausführen";
    box.append(h);
    return;
  }
  const gruppen = Object.entries(r.aufteilung).sort((a, b) => b[1].length - a[1].length);
  const summe = gruppen.reduce((s, [, xs]) => s + xs.reduce((t, x) => t + x.treffer.kosten.preis, 0), 0);
  h.textContent = gruppen.length
    ? `${paare.length - r.ohneAktion.length} von ${paare.length} in Aktion · ${euro(summe)}`
    : "Nichts von deiner Liste ist gerade in Aktion";
  box.append(h);
  if (gruppen.length) {
    const ul = document.createElement("ul");
    for (const [k, xs] of gruppen) {
      const li = document.createElement("li");
      const teil = xs.reduce((t, x) => t + x.treffer.kosten.preis, 0);
      const txt = document.createElement("span");
      txt.textContent = `${xs.length} Produkt${xs.length === 1 ? "" : "e"}`;
      const preis = document.createElement("strong");
      preis.textContent = euro(teil);
      li.append(L.badge(k), txt, preis);
      ul.append(li);
    }
    box.append(ul);
  }
  if (r.rangliste[0] && gruppen.length > 1) {
    const p = document.createElement("p");
    const b = r.rangliste[0];
    p.textContent = `Nur ein Geschäft? Am meisten in Aktion bei ${KETTEN[b.kette]} (${b.anzahl} von ${paare.length}).`;
    box.append(p);
  }
}

// ---------- Kopfzeile, Region ----------
function kopfAktualisieren() {
  const r = aktuelleRegion();
  if (!r && !LANDESWEIT.some((k) => DATEN[k])) {
    $("#gueltigkeit").textContent = "Keine Daten – zuerst `python -m aktionen.export` ausführen";
    return;
  }
  const teile = [];
  if (r) teile.push(`Spar ${r.name}${r.gueltig_von ? ` ${datum(r.gueltig_von)}–${datum(r.gueltig_bis)}` : ""}`);
  for (const k of LANDESWEIT) if (DATEN[k]) teile.push(KETTEN[k]);
  $("#gueltigkeit").textContent = teile.join(" + ");
  const fb = L.sichereUrl(r?.flugblatt_url);
  if (fb) $("#flugblattLink").href = fb;
  const tag = (iso) => new Date(iso).toLocaleDateString("de-AT", { day: "2-digit", month: "2-digit" });
  const staende = [
    ...DATEN.regionen.filter((x) => x.stand).map((x) => `Spar ${x.name} ${tag(x.stand)}`),
    ...LANDESWEIT.filter((k) => DATEN[k]?.stand).map((k) => `${KETTEN[k]} ${tag(DATEN[k].stand)}`),
  ];
  $("#stand").textContent = DATEN.erstellt ? `Datenstand: ${new Date(DATEN.erstellt).toLocaleString("de-AT")}` +
    (staende.length ? ` · zuletzt neu geladen: ${staende.join(", ")}` : "") : "";
}

function einstellungenSpeichern() {
  const { ansicht, region, kette, sortierung } = zustand;
  speichern(SPEICHER_EINST, { ansicht, region, kette, sortierung });
}

function auswahlSetzen(attr, wert) {
  document.querySelectorAll(`[data-${attr}]`).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset[attr] === wert)));
}
function ansichtSetzen(ansicht) {
  zustand.ansicht = ansicht;
  document.querySelectorAll("[data-ansicht]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.ansicht === ansicht)));
}

function neuZeichnen() {
  zustand.sichtbar = SEITE;
  einstellungenSpeichern();
  angeboteZeichnen();
}

// ---------- Start ----------
function start() {
  const einst = laden(SPEICHER_EINST, {});
  const sel = $("#region");
  for (const r of DATEN.regionen) sel.add(new Option(`Spar: ${r.name}`, r.region));
  zustand.region = DATEN.regionen.some((r) => r.region === einst.region) ? einst.region : DATEN.regionen[0]?.region;
  sel.value = zustand.region ?? "";
  sel.hidden = DATEN.regionen.length < 2;
  zustand.kette = KETTEN[einst.kette] ? einst.kette : "";
  zustand.sortierung = SORTIERUNG[einst.sortierung] ? einst.sortierung : "kilopreis";
  $("#sortierung").value = zustand.sortierung;
  auswahlSetzen("kette", zustand.kette);
  ansichtSetzen(einst.ansicht === "alle" && ALLE.erstellt ? "alle" : "fitness");

  sel.addEventListener("change", () => { zustand.region = sel.value; kopfAktualisieren(); neuZeichnen(); listeZeichnen(); merkZeichnen(); });
  $("#sortierung").addEventListener("change", (e) => { zustand.sortierung = e.target.value; neuZeichnen(); });
  let timer;
  $("#suche").addEventListener("input", (e) => {
    clearTimeout(timer);
    timer = setTimeout(() => { zustand.suche = e.target.value; zustand.sichtbar = SEITE; angeboteZeichnen(); }, 150);
  });
  document.querySelectorAll("[data-ansicht]").forEach((b) => b.addEventListener("click", () => { ansichtSetzen(b.dataset.ansicht); neuZeichnen(); }));
  document.querySelectorAll("[data-kette]").forEach((b) => b.addEventListener("click", () => {
    zustand.kette = b.dataset.kette; auswahlSetzen("kette", zustand.kette); neuZeichnen();
  }));
  $("#mehr").addEventListener("click", nachladen);
  weiterZiehenEinrichten();
  $("#grossBild").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) e.currentTarget.close(); // Klick neben das Bild schließt
  });

  // Seitenleiste
  $("#listeOeffnen").addEventListener("click", () => listeOeffnen(true));
  $("#listeSchliessen").addEventListener("click", () => listeOeffnen(false));
  $("#schleier").addEventListener("click", () => listeOeffnen(false));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && $("#schublade").classList.contains("offen") && !$("#grossBild").open) listeOeffnen(false);
  });
  const feld = $("#neu");
  $("#neuForm").addEventListener("submit", (ev) => {
    ev.preventDefault();
    if (L.hinzufuegen(feld.value)) feld.value = "";
    feld.focus();
  });
  feld.addEventListener("paste", (ev) => { // mehrere Zeilen einfügen -> mehrere Punkte
    const text = ev.clipboardData?.getData("text") ?? "";
    if (!/\n/.test(text)) return;
    ev.preventDefault();
    L.hinzufuegen(text);
  });
  $("#hakenWeg").addEventListener("click", L.hakenWeg);
  $("#erledigteWeg").addEventListener("click", L.erledigteWeg);
  $("#allesWeg").addEventListener("click", () => { if (confirm("Ganze Einkaufsliste löschen?")) L.leeren(); });
  $("#listeKopieren").addEventListener("click", async (e) => {
    const knopf = e.currentTarget;
    const text = L.alsNotiz(letztesErgebnis ?? L.auswerten(alleAktionen(), { tag: heuteIso() }), kopierOptionen());
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      knopf.textContent = "✓ Kopiert";
    } catch {
      prompt("Zum Kopieren markieren:", text);
    }
    setTimeout(() => (knopf.textContent = "📋 Kopieren"), 1500);
  });
  for (const id of ["#kopierOhne", "#kopierErledigt"]) $(id).addEventListener("change", () => letztesErgebnis && kopierenZeichnen(letztesErgebnis));
  L.beiAenderung(listeZeichnen);
  V.beiAenderung(() => { angeboteZeichnen(); listeZeichnen(); merkZeichnen(); });

  $("#merkBearbeiten").addEventListener("click", () => { merkDialogZeichnen(); $("#merkDialog").showModal(); });
  $("#merkDialog").addEventListener("click", (e) => { if (e.target === e.currentTarget) e.currentTarget.close(); });
  $("#merkForm").addEventListener("submit", (ev) => {
    ev.preventDefault();
    const neu = window.Abgleich.parseListe($("#merkNeu").value).map((e) => e.text).filter((t) => !gemerkt(t));
    if (neu.length) { merkliste.push(...neu); merkSpeichern(); }
    $("#merkNeu").value = "";
  });

  kopfAktualisieren();
  merkZeichnen();
  angeboteZeichnen();
  listeZeichnen();
  const perLink = () => { if (location.hash === "#liste") listeOeffnen(true); };
  window.addEventListener("hashchange", perLink);
  perLink();
}

start();

// Offline-Fähigkeit und "Zum Startbildschirm hinzufügen" (nur über http/https, nicht per Doppelklick)
if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
  navigator.serviceWorker.register("sw.js").catch(() => { /* ohne Offline-Modus weiter */ });
}
