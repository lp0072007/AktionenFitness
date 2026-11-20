// AktionenFitness – Website ohne Framework.
// Daten: data/angebote.js (window.ANGEBOTE), erzeugt mit `python -m aktionen.export`.

const DATEN = window.ANGEBOTE || { regionen: [] };
const SPEICHER_LISTE = "aktionenfitness.liste.v1";
const SPEICHER_EINST = "aktionenfitness.einstellungen.v1";

// Kilopreis (bzw. Literpreis) aus Preis und Menge. Bei Mengenaktionen zählt der Aktionspreis.
function grundpreis(a, preis = a.preis) {
  if (a.pro_kg) return { wert: preis, einheit: "kg" };
  if (!a.menge) return null;
  if (a.einheit === "g") return { wert: (preis / a.menge) * 1000, einheit: "kg" };
  if (a.einheit === "ml") return { wert: (preis / a.menge) * 1000, einheit: "l" };
  if (a.einheit === "stk") return { wert: preis / a.menge, einheit: "Stück" };
  return null;
}

// Sortierung: Kilo-/Literpreis aufsteigend, dann Stückpreise, Angebote ohne Menge ans Ende
function sortiereNachKilopreis(a, b) {
  const rang = (g) => (!g ? 2 : g.einheit === "Stück" ? 1 : 0);
  const ga = grundpreis(a), gb = grundpreis(b);
  return rang(ga) - rang(gb) || (ga?.wert ?? 0) - (gb?.wert ?? 0);
}

// ---------- Zustand ----------
const zustand = {
  region: null,
  gruppe: "",
  kette: "", // "" = alle, "spar", "lidl"
  suche: "",
  liste: {}, // id -> { angebot, anzahl }
};

function laden(schluessel, standard) {
  try {
    return JSON.parse(localStorage.getItem(schluessel)) ?? standard;
  } catch {
    return standard;
  }
}
function speichern(schluessel, wert) {
  try {
    localStorage.setItem(schluessel, JSON.stringify(wert));
  } catch {
    /* privater Modus o. ä. – dann eben ohne Speichern */
  }
}

// ---------- Hilfen ----------
const $ = (sel) => document.querySelector(sel);
const euro = (x) => x.toLocaleString("de-AT", { style: "currency", currency: "EUR" });
const zahl = (x, stellen = 0) => x.toLocaleString("de-AT", { maximumFractionDigits: stellen, minimumFractionDigits: stellen });
const KETTEN = { spar: "Spar", lidl: "Lidl", hofer: "Hofer", penny: "Penny", billa: "Billa" };
const LANDESWEIT = ["lidl", "hofer", "penny", "billa"]; // gelten in ganz Österreich
const WOCHENTAG = (iso) => new Date(iso + "T00:00:00").toLocaleDateString("de-AT", { weekday: "short" });
const datum = (iso) => (iso ? new Date(iso + "T00:00:00").toLocaleDateString("de-AT", { day: "2-digit", month: "2-digit" }) : "");

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
function alleAngebote() {
  // Spar gilt pro Bundesland, Lidl österreichweit
  const r = aktuelleRegion();
  return [...(r?.angebote ?? []), ...LANDESWEIT.flatMap((k) => DATEN[k]?.angebote ?? [])];
}

function gefilterteAngebote() {
  const q = zustand.suche.trim().toLowerCase();
  return alleAngebote()
    .filter((a) => !zustand.kette || a.kette === zustand.kette)
    .filter((a) => !zustand.gruppe || a.gruppe === zustand.gruppe)
    .filter((a) => !q || `${a.name} ${a.kategorie}`.toLowerCase().includes(q))
    .sort(sortiereNachKilopreis);
}

function karteBauen(a, rang) {
  const k = $("#kartenVorlage").content.firstElementChild.cloneNode(true);
  k.dataset.id = a.id;
  if (rang <= 3) {
    const r = document.createElement("span");
    r.className = "rang";
    r.textContent = rang;
    r.title = `Platz ${rang}`;
    k.prepend(r);
  }
  if (a.bild) {
    const knopfBild = k.querySelector(".karte__bild");
    const img = knopfBild.querySelector("img");
    img.src = a.bild;
    img.alt = `Flugblatt-Ausschnitt: ${a.name}`;
    img.addEventListener("error", () => (knopfBild.hidden = true)); // Bilder fehlen, wenn ohne Export geklont
    knopfBild.hidden = false;
    knopfBild.addEventListener("click", () => bildZeigen(a));
  }
  const z = k.querySelector(".zuordnung");
  if (a.zuordnung === "strukturiert") {
    z.textContent = "✓ Daten direkt vom Händler";
    z.className = "zuordnung zuordnung--ok";
  } else if (a.zuordnung === "geprueft") {
    z.textContent = "✓ Preis passt zum Grundpreis im Flugblatt";
    z.className = "zuordnung zuordnung--ok";
  } else if (a.zuordnung === "unsicher") {
    z.textContent = "⚠ Zuordnung unsicher – bitte im Flugblatt prüfen";
    z.className = "zuordnung zuordnung--warn";
  } else z.remove();
  k.querySelector(".badge--kat").textContent = a.kategorie;
  const kette = k.querySelector(".badge--kette");
  kette.textContent = KETTEN[a.kette] ?? a.kette;
  kette.classList.add(`badge--${a.kette}`);
  const quelle = k.querySelector(".karte__seite");
  if (a.url) {
    const link = document.createElement("a");
    link.href = a.url;
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = `${new URL(a.url).hostname.replace(/^www\./, "")} ↗`;
    quelle.replaceChildren(link);
  } else quelle.textContent = `Flugblatt S. ${a.seite}`;
  // Gültigkeit: Lidl pro Angebot, Spar = Zeitraum des Flugblatts der Region
  const gueltig = k.querySelector(".karte__gueltig");
  const region = aktuelleRegion();
  const von = a.gueltig_von ?? (a.kette === "spar" ? region?.gueltig_von : null);
  const bis = a.gueltig_bis ?? (a.kette === "spar" ? region?.gueltig_bis : null);
  if (von) {
    const heute = new Date().toISOString().slice(0, 10);
    const zukunft = von > heute;
    gueltig.textContent = `${zukunft ? "⏳ erst ab" : "📅 gültig"} ${WOCHENTAG(von)} ${datum(von)}` +
      (bis ? ` – ${WOCHENTAG(bis)} ${datum(bis)}` : "");
    gueltig.classList.toggle("karte__gueltig--zukunft", zukunft);
  } else if (a.kette === "billa") {
    gueltig.textContent = `📅 aktuell im BILLA-Shop (Stand ${DATEN.erstellt ? new Date(DATEN.erstellt).toLocaleDateString("de-AT") : "–"})`;
  } else gueltig.textContent = "📅 Gültigkeit siehe Flugblatt";
  k.querySelector(".karte__name").textContent = a.name;
  k.querySelector(".karte__menge").textContent = mengeText(a);
  k.querySelector(".preis").textContent = euro(a.preis);
  if (a.normalpreis && a.normalpreis > a.preis) k.querySelector(".normalpreis").textContent = euro(a.normalpreis);

  const bed = [];
  if (a.ab_menge) bed.push(`gilt ab ${a.ab_menge} Stück${a.normalpreis ? ` (1 Stk. ${euro(a.normalpreis)})` : ""}`);
  if (a.zusatzpreis) bed.push(`${a.zusatz_text || "Aktionstag"}: ${euro(a.zusatzpreis)}`);
  k.querySelector(".karte__bedingung").textContent = bed.join(" · ");

  const akt = k.querySelector(".karte__aktionen");
  for (const t of a.aktion) {
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
    if (gz) extra.push(`${a.zusatz_text || "Aktionstag"}: ${euro(gz.wert)} / ${gz.einheit}`);
    kp.querySelector(".kilopreis__extra").textContent = extra.join(" · ");
  } else {
    kp.querySelector(".kilopreis__wert").textContent = "–";
    kp.querySelector(".kilopreis__label").textContent = "Kilopreis unbekannt (keine Mengenangabe)";
  }

  const knopf = k.querySelector(".karte__knopf");
  knopfAktualisieren(knopf, a.id);
  knopf.addEventListener("click", () => {
    const n = zustand.liste[a.id]?.anzahl ?? 0;
    // Bei Mengenaktionen gleich die nötige Stückzahl vorschlagen
    listeSetzen(a, n ? n + 1 : a.ab_menge || 1);
  });
  return k;
}

function knopfAktualisieren(knopf, id) {
  const n = zustand.liste[id]?.anzahl;
  knopf.textContent = n ? `✓ ${n} auf der Liste` : "+ Liste";
  knopf.classList.toggle("ist-drauf", !!n);
}

function angeboteZeichnen() {
  const liste = gefilterteAngebote();
  const ziel = $("#karten");
  ziel.replaceChildren(...liste.map((a, i) => karteBauen(a, i + 1)));
  $("#leer").hidden = liste.length > 0;
  $("#zielInfo").textContent = `${liste.length} Angebote · sortiert nach Kilopreis – günstigstes zuerst`;
}

function bildZeigen(a) {
  const d = $("#grossBild");
  d.querySelector("img").src = a.bild;
  d.querySelector("img").alt = `Flugblatt-Ausschnitt: ${a.name}`;
  d.querySelector(".gross__text").textContent = `${a.name} – Flugblatt Seite ${a.seite}`;
  d.showModal();
}

// ---------- Einkaufsliste ----------
function stueckpreis(a, anzahl) {
  // Mengenaktion ("ab 2 Stück je 1,19") gilt erst ab der Mindestmenge
  if (a.ab_menge && anzahl < a.ab_menge && a.normalpreis) return a.normalpreis;
  return a.preis;
}

function listeSetzen(a, anzahl) {
  if (anzahl <= 0) delete zustand.liste[a.id];
  else zustand.liste[a.id] = { angebot: a, anzahl };
  speichern(SPEICHER_LISTE, zustand.liste);
  listeZeichnen();
  document.querySelectorAll(`.karte[data-id="${CSS.escape(a.id)}"] .karte__knopf`).forEach((k) => knopfAktualisieren(k, a.id));
}

function listeZeichnen() {
  const eintraege = Object.values(zustand.liste).sort((x, y) =>
    (x.angebot.kette ?? "spar").localeCompare(y.angebot.kette ?? "spar"));
  const ul = $("#listeEintraege");
  ul.replaceChildren();
  let preis = 0, protein = 0, kcal = 0, kh = 0, fett = 0, ohneMenge = 0;
  let letzteKette = null;

  for (const { angebot: a, anzahl } of eintraege) {
    const kette = a.kette ?? "spar";
    if (kette !== letzteKette) {
      const teil = eintraege
        .filter((e) => (e.angebot.kette ?? "spar") === kette)
        .reduce((s, e) => s + stueckpreis(e.angebot, e.anzahl) * e.anzahl, 0);
      const kopf = document.createElement("li");
      kopf.className = "liste__gruppe";
      kopf.innerHTML = `<span class="badge badge--kette badge--${kette}"></span><span></span>`;
      kopf.firstElementChild.textContent = KETTEN[kette] ?? kette;
      kopf.lastElementChild.textContent = euro(teil);
      ul.append(kopf);
      letzteKette = kette;
    }
    const sp = stueckpreis(a, anzahl);
    preis += sp * anzahl;
    if (a.gramm) {
      const f = (a.gramm / 100) * anzahl;
      protein += a.naehrwerte.protein * f;
      kcal += a.naehrwerte.kcal * f;
      kh += a.naehrwerte.kohlenhydrate * f;
      fett += a.naehrwerte.fett * f;
    } else ohneMenge++;

    const li = document.createElement("li");
    li.className = "eintrag";
    const fehlt = a.ab_menge && anzahl < a.ab_menge;
    li.innerHTML = `
      <span class="eintrag__name"></span>
      <span class="eintrag__preis"></span>
      <span class="eintrag__info${fehlt ? " warn" : ""}"></span>
      <span class="stepper">
        <button aria-label="Weniger">−</button><span></span><button aria-label="Mehr">+</button>
      </span>`;
    li.querySelector(".eintrag__name").textContent = a.name;
    li.querySelector(".eintrag__preis").textContent = euro(sp * anzahl);
    li.querySelector(".eintrag__info").textContent = fehlt
      ? `Aktion erst ab ${a.ab_menge} Stück – jetzt ${euro(sp)}/Stk.`
      : `${a.pro_kg ? `${anzahl} kg` : `${anzahl} × ${mengeText(a) || "Stück"}`} · ${euro(sp)}${a.pro_kg ? "/kg" : ""}`;
    li.querySelector(".stepper span").textContent = anzahl;
    const [minus, plus] = li.querySelectorAll(".stepper button");
    minus.addEventListener("click", () => listeSetzen(a, anzahl - 1));
    plus.addEventListener("click", () => listeSetzen(a, anzahl + 1));
    ul.append(li);
  }

  const leer = eintraege.length === 0;
  $("#listeLeer").hidden = !leer;
  $("#summen").hidden = leer;
  $("#listeZaehler").textContent = eintraege.length;
  $("#sumPreis").textContent = euro(preis);
  $("#sumProtein").textContent = zahl(protein);
  $("#sumKcal").textContent = zahl(kcal);
  $("#sumKh").textContent = zahl(kh);
  $("#sumFett").textContent = zahl(fett);
  $("#sumHinweis").textContent =
    (ohneMenge ? `${ohneMenge} Produkt(e) ohne Mengenangabe nicht in den Makros.` : "");
}

function listeAlsText() {
  const eintraege = Object.values(zustand.liste);
  const zeilen = ["Einkaufsliste"];
  for (const kette of [...new Set(eintraege.map((e) => e.angebot.kette ?? "spar"))].sort()) {
    zeilen.push("", `${KETTEN[kette] ?? kette}:`);
    for (const { angebot: a, anzahl } of eintraege.filter((e) => (e.angebot.kette ?? "spar") === kette)) {
      const sp = stueckpreis(a, anzahl);
      zeilen.push(`☐ ${anzahl}× ${a.name}${a.menge ? ` (${mengeText(a)})` : ""} – ${euro(sp * anzahl)}`);
    }
  }
  const summe = eintraege.reduce((s, { angebot: a, anzahl }) => s + stueckpreis(a, anzahl) * anzahl, 0);
  return [...zeilen, "", `Gesamt: ${euro(summe)}`].join("\n");
}

// ---------- Mobil: Liste ein-/ausblenden ----------
function listeOeffnen(offen) {
  $("#einkaufsliste").classList.toggle("offen", offen);
  $("#schleier").hidden = !offen;
  $("#listeOeffnen").setAttribute("aria-expanded", String(offen));
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
  const anzahl = alleAngebote().length;
  $("#gueltigkeit").textContent = `${teile.join(" + ")} · ${anzahl} Fitness-Angebote`;
  const link = $("#flugblattLink");
  if (r.flugblatt_url) link.href = r.flugblatt_url;
  $("#stand").textContent = DATEN.erstellt ? `Datenstand: ${new Date(DATEN.erstellt).toLocaleString("de-AT")}` : "";
}

function einstellungenSpeichern() {
  speichern(SPEICHER_EINST, { region: zustand.region, gruppe: zustand.gruppe, kette: zustand.kette });
}

function ketteSetzen(kette) {
  zustand.kette = kette;
  document.querySelectorAll("[data-kette]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.kette === kette)));
}
function gruppeSetzen(gruppe) {
  zustand.gruppe = gruppe;
  document.querySelectorAll("[data-kette]").forEach((b) =>
    b.addEventListener("click", () => {
      ketteSetzen(b.dataset.kette);
      einstellungenSpeichern();
      angeboteZeichnen();
    })
  );
  document.querySelectorAll("[data-gruppe]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.gruppe === gruppe)));
}

// ---------- Start ----------
function start() {
  const einst = laden(SPEICHER_EINST, {});
  zustand.liste = laden(SPEICHER_LISTE, {});

  const sel = $("#region");
  for (const r of DATEN.regionen) sel.add(new Option(r.name, r.region));
  zustand.region = DATEN.regionen.some((r) => r.region === einst.region) ? einst.region : DATEN.regionen[0]?.region;
  sel.value = zustand.region ?? "";
  gruppeSetzen(einst.gruppe ?? "");
  ketteSetzen(KETTEN[einst.kette] ? einst.kette : "");

  sel.addEventListener("change", () => {
    zustand.region = sel.value;
    einstellungenSpeichern();
    kopfAktualisieren();
    angeboteZeichnen();
  });
  $("#suche").addEventListener("input", (e) => {
    zustand.suche = e.target.value;
    angeboteZeichnen();
  });
  document.querySelectorAll("[data-gruppe]").forEach((b) =>
    b.addEventListener("click", () => {
      gruppeSetzen(b.dataset.gruppe);
      einstellungenSpeichern();
      angeboteZeichnen();
    })
  );
  $("#grossBild").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) e.currentTarget.close(); // Klick neben das Bild schließt
  });
  $("#listeOeffnen").addEventListener("click", () => listeOeffnen(true));
  $("#listeSchliessen").addEventListener("click", () => listeOeffnen(false));
  $("#schleier").addEventListener("click", () => listeOeffnen(false));
  $("#listeLeeren").addEventListener("click", () => {
    if (!confirm("Einkaufsliste wirklich leeren?")) return;
    zustand.liste = {};
    speichern(SPEICHER_LISTE, zustand.liste);
    listeZeichnen();
    angeboteZeichnen();
  });
  $("#listeKopieren").addEventListener("click", async (e) => {
    const knopf = e.currentTarget;
    try {
      await navigator.clipboard.writeText(listeAlsText());
      knopf.textContent = "✓ Kopiert";
    } catch {
      prompt("Zum Kopieren markieren:", listeAlsText());
    }
    setTimeout(() => (knopf.textContent = "📋 Als Text kopieren"), 1500);
  });

  kopfAktualisieren();
  angeboteZeichnen();
  listeZeichnen();
}

start();
