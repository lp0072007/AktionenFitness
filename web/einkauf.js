// Oberfläche "Einkaufsliste abgleichen". Logik: abgleich.js, Daten: data/aktionen.js (python -m aktionen.export)

const DATEN = window.AKTIONEN || { regionen: {}, ketten: {} };
const A = window.Abgleich;
const KETTEN = { spar: "Spar", lidl: "Lidl", hofer: "Hofer", penny: "Penny", billa: "Billa", dm: "dm" };
const SPEICHER = "aktionenfitness.einkauf.v1"; // Region und abgewählte Treffer; die Liste selbst: liste.js
const L = window.Einkaufsliste;

const $ = (s) => document.querySelector(s);
const euro = (x) => x.toLocaleString("de-AT", { style: "currency", currency: "EUR" });
const datum = (iso) => new Date(iso + "T00:00:00").toLocaleDateString("de-AT", { weekday: "short", day: "2-digit", month: "2-digit" });
const heuteIso = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);

const zustand = { ausgeschlossen: new Set() };

function laden() {
  try { return JSON.parse(localStorage.getItem(SPEICHER)) || {}; } catch { return {}; }
}
function speichern() {
  try {
    const alt = laden();
    localStorage.setItem(SPEICHER, JSON.stringify({ ...alt, region: $("#region").value, ausgeschlossen: [...zustand.ausgeschlossen] }));
  } catch { /* privater Modus */ }
}

function angebote() {
  const region = DATEN.regionen[$("#region").value];
  return [...(region?.angebote ?? []), ...Object.values(DATEN.ketten).flat()];
}

function mengeText(a) {
  if (a.pro_kg) return "per kg";
  if (!a.menge) return "";
  if (a.einheit === "stk") return `${a.menge} Stk.`;
  if (a.einheit === "ml") return a.menge >= 1000 ? `${(a.menge / 1000).toLocaleString("de-AT")} l` : `${a.menge} ml`;
  return a.menge >= 1000 ? `${(a.menge / 1000).toLocaleString("de-AT")} kg` : `${a.menge} g`;
}

const badge = (kette) => L.badge(kette);

// Wie wurde die Zeile verstanden? "2 ×", "1 kg", "10er"
function verstanden(e) {
  const teile = [];
  if (e.anzahl && e.anzahl !== 1) teile.push(`${e.anzahl.toLocaleString("de-AT")} ×`);
  if (e.menge) {
    if (e.einheit === "stk") teile.push(`${e.menge}er`);
    else if (e.menge >= 1000) teile.push(`${(e.menge / 1000).toLocaleString("de-AT")} ${e.einheit === "g" ? "kg" : "l"}`);
    else teile.push(`${e.menge.toLocaleString("de-AT")} ${e.einheit}`);
  }
  return teile.join(" ");
}

// Keine Aktion am Einkaufstag? Dann die nächste kommende (oder gerade abgelaufene) Aktion suchen,
// damit man sieht, dass es sie gibt – nur an einem anderen Tag.
function andererTag(e) {
  const tag = $("#tag").value;
  const alle = A.finde(e, angebote().filter((a) => !zustand.ausgeschlossen.has(a.id)), null);
  const kommend = alle.filter((t) => t.angebot.gueltig_von && t.angebot.gueltig_von > tag)
    .sort((x, y) => x.angebot.gueltig_von.localeCompare(y.angebot.gueltig_von));
  if (kommend.length) return { treffer: kommend[0], text: `ab ${datum(kommend[0].angebot.gueltig_von)}` };
  const vorbei = alle.filter((t) => t.angebot.gueltig_bis && t.angebot.gueltig_bis < tag);
  if (vorbei.length) return { treffer: vorbei[0], text: `nur bis ${datum(vorbei[0].angebot.gueltig_bis)}` };
  return null;
}

// ---------- Liste (liste.js) ----------
function listeZeichnen(ergebnis) {
  const n = L.zeilen.filter((z) => z.erledigt).length;
  $("#erledigtZaehler").textContent = L.zeilen.length ? `${n} / ${L.zeilen.length} erledigt` : "";
  $("#hakenWeg").hidden = $("#erledigteWeg").hidden = n === 0;
  $("#listeLeer").hidden = L.zeilen.length > 0;
  $("#listeAktionen").hidden = L.zeilen.length === 0;
  L.zeichnen($("#vorschau"), ergebnis, {
    angebote: angebote().filter((a) => !zustand.ausgeschlossen.has(a.id)), tag: $("#tag").value, mitDaten: !!DATEN.erstellt,
  });
}

// ---------- Darstellung ----------
function trefferZeile(t, eintrag) {
  const li = $("#trefferVorlage").content.firstElementChild.cloneNode(true);
  const a = t.angebot;
  const aus = zustand.ausgeschlossen.has(a.id);
  li.classList.toggle("ek-treffer--aus", aus);
  const box = li.querySelector("input");
  box.checked = !aus;
  box.addEventListener("change", () => {
    if (box.checked) zustand.ausgeschlossen.delete(a.id); else zustand.ausgeschlossen.add(a.id);
    speichern();
    berechnen();
  });
  const img = li.querySelector("img");
  const bild = L.sichereUrl(a.bild);
  if (bild) { img.src = bild; img.addEventListener("error", () => img.removeAttribute("src")); }
  li.querySelector(".badge").replaceWith(badge(a.kette));
  const name = li.querySelector(".ek-treffer__name");
  name.textContent = a.name;
  const url = L.sichereUrl(a.url);
  if (url) name.href = url; else name.removeAttribute("href");

  const info = [mengeText(a)];
  if (t.grundpreis) info.push(`${euro(t.grundpreis.wert)}/${t.grundpreis.einheit}`);
  if (a.gueltig_von) info.push(`${datum(a.gueltig_von)}–${a.gueltig_bis ? datum(a.gueltig_bis) : "?"}`);
  else if (a.kette === "billa") info.push("aktuell im Shop");
  if (a.ab_menge) info.push(`ab ${a.ab_menge} Stk.`);
  if (a.zusatzpreis) info.push(`${a.zusatz_text || "Aktionstag"}: ${euro(a.zusatzpreis)}`);
  if (a.aktion?.length) info.push(a.aktion.join(" · "));
  const infoEl = li.querySelector(".ek-treffer__info");
  infoEl.textContent = (t.kosten.hinweis ? `⚠ ${t.kosten.hinweis} · ` : "") + info.filter(Boolean).join(" · ");
  infoEl.classList.toggle("warn", !!t.kosten.hinweis);

  const preis = li.querySelector(".ek-treffer__preis");
  const stueck = t.kosten.stueck;
  preis.innerHTML = "";
  preis.append(euro(t.kosten.preis));
  const klein = document.createElement("small");
  klein.textContent = (stueck !== 1 ? `${stueck.toLocaleString("de-AT")} × ${euro(a.preis)}` : "") +
    (a.normalpreis ? `${stueck !== 1 ? " · " : ""}statt ${euro(a.normalpreis)}` : "");
  preis.append(klein);
  return li;
}

function zeichnen(liste, r) {
  $("#leerHinweis").hidden = liste.length > 0;
  $("#ergebnis").hidden = liste.length === 0;
  if (!liste.length) return;

  // Empfehlung
  const emp = $("#empfehlung");
  emp.replaceChildren();
  const h = document.createElement("h2");
  const beste = r.rangliste[0];
  if (!DATEN.erstellt) {
    emp.classList.add("ek-empfehlung--fehler");
    h.textContent = "⚠ Keine Aktionsdaten geladen";
    const p = document.createElement("p");
    p.textContent = "Die Datei web/data/aktionen.js fehlt. Im Ordner scraper (mit aktivierter venv) einmal " +
      "„python -m aktionen.export“ ausführen und die Seite neu laden.";
    emp.append(h, p);
  } else if (!beste) {
    h.textContent = "Diese Woche ist nichts von deiner Liste in Aktion.";
    emp.append(h);
  } else {
    h.textContent = `🏆 ${KETTEN[beste.kette]}: ${beste.anzahl} von ${liste.length} Produkten in Aktion`;
    const p1 = document.createElement("p");
    p1.textContent = beste.ersparnis > 0
      ? `Du sparst dort mindestens ${euro(beste.ersparnis)} gegenüber dem Normalpreis.`
      : "Ersparnis unbekannt (der Händler nennt keinen Normalpreis).";
    const kombi = Object.entries(r.aufteilung).sort((a, b) => b[1].length - a[1].length);
    const p2 = document.createElement("p");
    if (kombi.length > 1) {
      const summe = kombi.reduce((s, [, xs]) => s + xs.reduce((t, x) => t + x.treffer.kosten.preis, 0), 0);
      p2.textContent = `Günstigste Aufteilung: ${kombi.map(([k, xs]) => `${KETTEN[k]} (${xs.length})`).join(" + ")} · ` +
        `Aktionsprodukte zusammen ${euro(summe)}.`;
    }
    const p3 = document.createElement("p");
    if (r.ohneAktion.length) p3.textContent = `Nicht in Aktion: ${r.ohneAktion.map((e) => e.text).join(", ")}.`;
    emp.append(h, p1, p2, p3);
  }

  // Rangliste der Geschäfte
  $("#rangliste").replaceChildren(...r.rangliste.map((z, i) => {
    const d = document.createElement("div");
    d.className = "ek-kette" + (i === 0 ? " ek-kette--erste" : "");
    const s = document.createElement("strong");
    s.textContent = `${z.anzahl} / ${liste.length}`;
    const t1 = document.createElement("span");
    t1.textContent = `Produkte in Aktion · ${euro(z.preis)}`;
    const t2 = document.createElement("span");
    t2.textContent = z.ersparnis > 0 ? `spart ≥ ${euro(z.ersparnis)}` : "Ersparnis unbekannt";
    d.append(badge(z.kette), s, t1, t2);
    return d;
  }));

  // Aufteilung nach Geschäft
  const auf = $("#aufteilung");
  auf.replaceChildren();
  for (const [k, xs] of Object.entries(r.aufteilung).sort((a, b) => b[1].length - a[1].length)) {
    const g = document.createElement("div");
    g.className = "ek-gruppe";
    const kopf = document.createElement("div");
    kopf.className = "ek-gruppe__kopf";
    const summe = xs.reduce((s, x) => s + x.treffer.kosten.preis, 0);
    const sp = document.createElement("span");
    sp.textContent = euro(summe);
    kopf.append(badge(k), sp);
    const ul = document.createElement("ul");
    for (const { eintrag, treffer } of xs) {
      const li = document.createElement("li");
      const links = document.createElement("span");
      links.textContent = eintrag.text + " ";
      const klein = document.createElement("small");
      klein.textContent = `→ ${treffer.angebot.name}`;
      links.append(klein);
      const rechts = document.createElement("span");
      rechts.textContent = euro(treffer.kosten.preis);
      li.append(links, rechts);
      ul.append(li);
    }
    g.append(kopf, ul);
    auf.append(g);
  }
  if (r.ohneAktion.length) {
    const p = document.createElement("p");
    p.className = "ek-fehlt";
    p.textContent = `Ohne Aktion (Preis unbekannt, kaufst du irgendwo zum Normalpreis): ${r.ohneAktion.map((e) => e.text).join(", ")}`;
    auf.append(p);
  }

  // Alle Treffer pro Eintrag – inklusive abgewählter, damit man sie wieder anhaken kann
  const alleAngebote = angebote();
  $("#eintraege").replaceChildren(...liste.map((e) => {
    const box = document.createElement("div");
    box.className = "ek-eintrag";
    const h3 = document.createElement("h3");
    const alle = A.finde(e, alleAngebote, $("#tag").value);
    h3.textContent = e.name;
    const menge = verstanden(e);
    if (menge) {
      const m = document.createElement("small");
      m.className = "ek-menge";
      m.textContent = menge;
      h3.append(" ", m);
    }
    const anz = document.createElement("span");
    anz.textContent = `${alle.length} Treffer`;
    h3.append(anz);
    box.append(h3);
    if (!alle.length) {
      const p = document.createElement("p");
      p.className = "ek-keine";
      const anders = andererTag(e);
      p.textContent = anders
        ? `Am gewählten Einkaufstag nicht in Aktion – ${KETTEN[anders.treffer.angebot.kette] ?? anders.treffer.angebot.kette}: ` +
          `${anders.treffer.angebot.name} ${anders.text} (${euro(anders.treffer.angebot.preis)}). Einkaufstag oben ändern, um damit zu rechnen.`
        : "Keine passende Aktion gefunden.";
      box.append(p);
    } else {
      const ul = document.createElement("ul");
      // bester Treffer je Geschäft zuerst, dann die übrigen in ihrer Reihenfolge (max. 8)
      const besteJeKette = [];
      const gesehen = new Set();
      for (const t of alle) {
        if (!gesehen.has(t.angebot.kette)) { gesehen.add(t.angebot.kette); besteJeKette.push(t); }
      }
      const rest = alle.filter((t) => !besteJeKette.includes(t));
      const gezeigt = [...besteJeKette, ...rest].slice(0, 8);
      ul.append(...gezeigt.map((t) => trefferZeile(t, e)));
      box.append(ul);
    }
    return box;
  }));
}

function berechnen() {
  const ergebnis = L.auswerten(angebote(), { tag: $("#tag").value, ausgeschlossen: zustand.ausgeschlossen });
  zeichnen(ergebnis.paare.map((p) => p.eintrag), ergebnis.r);
  listeZeichnen(ergebnis);
}

// ---------- Start ----------
function start() {
  const gespeichert = laden();
  const sel = $("#region");
  for (const [key, r] of Object.entries(DATEN.regionen)) sel.add(new Option(r.name, key));
  if (gespeichert.region && DATEN.regionen[gespeichert.region]) sel.value = gespeichert.region;
  $("#tag").value = heuteIso();
  zustand.ausgeschlossen = new Set(gespeichert.ausgeschlossen ?? []);

  const anzahl = Object.values(DATEN.regionen).reduce((s, r) => s + r.angebote.length, 0) +
    Object.values(DATEN.ketten).reduce((s, l) => s + l.length, 0);
  $("#stand").textContent = DATEN.erstellt
    ? `${anzahl.toLocaleString("de-AT")} Aktionen · Stand ${new Date(DATEN.erstellt).toLocaleString("de-AT")}`
    : "Keine Daten – zuerst `python -m aktionen.export` ausführen";

  const feld = $("#neu");
  $("#neuForm").addEventListener("submit", (ev) => {
    ev.preventDefault();
    if (L.hinzufuegen(feld.value)) feld.value = "";
    feld.focus();
  });
  // Mehrere Zeilen einfügen (z. B. aus einer Notiz-App) -> alle auf einmal übernehmen
  feld.addEventListener("paste", (ev) => {
    const text = ev.clipboardData?.getData("text") ?? "";
    if (!/\n/.test(text)) return;
    ev.preventDefault();
    L.hinzufuegen(text);
  });
  sel.addEventListener("change", () => { speichern(); berechnen(); });
  $("#hakenWeg").addEventListener("click", L.hakenWeg);
  $("#erledigteWeg").addEventListener("click", L.erledigteWeg);
  $("#allesWeg").addEventListener("click", () => { if (confirm("Ganze Liste löschen?")) L.leeren(); });
  L.beiAenderung(berechnen);
  $("#tag").addEventListener("change", berechnen);
  berechnen();
}

start();

// Offline-Fähigkeit und "Zum Startbildschirm hinzufügen" (nur über http/https, nicht per Doppelklick)
if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
  navigator.serviceWorker.register("sw.js").catch(() => { /* ohne Offline-Modus weiter */ });
}
