// AktionenFitness – Website ohne Framework.
// Daten: data/angebote.js (window.ANGEBOTE), erzeugt mit `python -m aktionen.export`.

const DATEN = window.ANGEBOTE || { regionen: [] };
const SPEICHER_LISTE = "aktionenfitness.liste.v1";
const SPEICHER_EINST = "aktionenfitness.einstellungen.v1";

const ZIELE = {
  protein: {
    info: "Sortiert nach Gramm Protein pro Euro – am meisten Eiweiß fürs Geld.",
    sort: (a, b) => (b.protein_pro_euro ?? -1) - (a.protein_pro_euro ?? -1),
  },
  diaet: {
    info: "Diät: eiweißreiche Lebensmittel (mind. 8 g Protein pro 100 kcal) zuerst, dann nach Protein pro Euro.",
    sort: (a, b) =>
      (b.protein_pro_100kcal >= 8) - (a.protein_pro_100kcal >= 8) ||
      (b.protein_pro_euro ?? -1) - (a.protein_pro_euro ?? -1),
  },
  aufbau: {
    info: "Aufbau: möglichst viele Kalorien pro Euro – günstige Energie für den Masseaufbau.",
    sort: (a, b) => (b.kcal_pro_euro ?? -1) - (a.kcal_pro_euro ?? -1),
  },
};

// ---------- Zustand ----------
const zustand = {
  region: null,
  ziel: "protein",
  gruppe: "",
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
function gefilterteAngebote() {
  const r = aktuelleRegion();
  if (!r) return [];
  const q = zustand.suche.trim().toLowerCase();
  return r.angebote
    .filter((a) => !zustand.gruppe || a.gruppe === zustand.gruppe)
    .filter((a) => !q || `${a.name} ${a.kategorie}`.toLowerCase().includes(q))
    .sort(ZIELE[zustand.ziel].sort);
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
  if (a.zuordnung === "geprueft") {
    z.textContent = "✓ Preis passt zum Grundpreis im Flugblatt";
    z.className = "zuordnung zuordnung--ok";
  } else if (a.zuordnung === "unsicher") {
    z.textContent = "⚠ Zuordnung unsicher – bitte im Flugblatt prüfen";
    z.className = "zuordnung zuordnung--warn";
  } else z.remove();
  k.querySelector(".badge--kat").textContent = a.kategorie;
  k.querySelector(".karte__seite").textContent = `Flugblatt S. ${a.seite}`;
  k.querySelector(".karte__name").textContent = a.name;
  k.querySelector(".karte__menge").textContent = mengeText(a);
  k.querySelector(".preis").textContent = euro(a.preis);
  if (a.normalpreis && a.normalpreis > a.preis) k.querySelector(".normalpreis").textContent = euro(a.normalpreis);

  const bed = [];
  if (a.ab_menge) bed.push(`gilt ab ${a.ab_menge} Stück${a.normalpreis ? ` (1 Stk. ${euro(a.normalpreis)})` : ""}`);
  if (a.zusatzpreis) bed.push(`Aktionstag: ${euro(a.zusatzpreis)}`);
  k.querySelector(".karte__bedingung").textContent = bed.join(" · ");

  const akt = k.querySelector(".karte__aktionen");
  for (const t of a.aktion) {
    const b = document.createElement("span");
    b.className = "badge badge--aktion";
    b.textContent = t;
    akt.append(b);
  }

  k.querySelector(".k-protein").textContent = a.protein_pro_euro != null ? `${zahl(a.protein_pro_euro, 1)} g` : "–";
  k.querySelector(".k-kcal").textContent = a.kcal_pro_euro != null ? zahl(a.kcal_pro_euro) : "–";
  k.querySelector(".k-dichte").textContent = `${zahl(a.protein_pro_100kcal, 1)} g`;

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
  $("#zielInfo").textContent = `${liste.length} Angebote · ${ZIELE[zustand.ziel].info}`;
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
  const eintraege = Object.values(zustand.liste);
  const ul = $("#listeEintraege");
  ul.replaceChildren();
  let preis = 0, protein = 0, kcal = 0, kh = 0, fett = 0, ohneMenge = 0;

  for (const { angebot: a, anzahl } of eintraege) {
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
    (protein && preis ? `≈ ${zahl(protein / preis, 1)} g Protein pro Euro. ` : "") +
    (ohneMenge ? `${ohneMenge} Produkt(e) ohne Mengenangabe nicht in den Makros.` : "");
}

function listeAlsText() {
  const zeilen = Object.values(zustand.liste).map(({ angebot: a, anzahl }) => {
    const sp = stueckpreis(a, anzahl);
    return `☐ ${anzahl}× ${a.name}${a.menge ? ` (${mengeText(a)})` : ""} – ${euro(sp * anzahl)}`;
  });
  const summe = Object.values(zustand.liste).reduce((s, { angebot: a, anzahl }) => s + stueckpreis(a, anzahl) * anzahl, 0);
  const r = aktuelleRegion();
  return [`Einkaufsliste Spar${r ? ` (${r.name})` : ""}`, ...zeilen, `Gesamt: ${euro(summe)}`].join("\n");
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
  if (!r) {
    $("#gueltigkeit").textContent = "Keine Daten – zuerst `python -m aktionen.export` ausführen";
    return;
  }
  const g = r.gueltig_von ? `gültig ${datum(r.gueltig_von)}–${datum(r.gueltig_bis)}` : "";
  $("#gueltigkeit").textContent = `Spar ${r.name} · ${g} · ${r.angebote.length} von ${r.anzahl_angebote} Angeboten fitnessrelevant`;
  const link = $("#flugblattLink");
  if (r.flugblatt_url) link.href = r.flugblatt_url;
  $("#stand").textContent = DATEN.erstellt ? `Datenstand: ${new Date(DATEN.erstellt).toLocaleString("de-AT")}` : "";
}

function einstellungenSpeichern() {
  speichern(SPEICHER_EINST, { region: zustand.region, ziel: zustand.ziel, gruppe: zustand.gruppe });
}

function zielSetzen(ziel) {
  zustand.ziel = ziel;
  document.querySelectorAll("[data-ziel]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.ziel === ziel)));
}
function gruppeSetzen(gruppe) {
  zustand.gruppe = gruppe;
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
  zielSetzen(ZIELE[einst.ziel] ? einst.ziel : "protein");
  gruppeSetzen(einst.gruppe ?? "");

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
  document.querySelectorAll("[data-ziel]").forEach((b) =>
    b.addEventListener("click", () => {
      zielSetzen(b.dataset.ziel);
      einstellungenSpeichern();
      angeboteZeichnen();
    })
  );
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
