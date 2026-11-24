// Gemeinsame Einkaufsliste für die Startseite (Seitenleiste) und einkauf.html. Braucht abgleich.js.
//
// Jede Zeile ist ein Punkt der Liste: { id, text, erledigt, angebot?, anzahl? }.
// "angebot" ist gesetzt, wenn man auf einer Karte "+ Liste" tippt: dann gilt genau dieses Angebot.
// Sonst wird der Text mit allen Aktionen abgeglichen (abgleich.js).

(function (global) {
  "use strict";
  const A = global.Abgleich;
  const SCHLUESSEL = "aktionenfitness.einkaufsliste.v2";
  const KETTEN = { spar: "Spar", lidl: "Lidl", hofer: "Hofer", penny: "Penny", billa: "Billa", dm: "dm" };
  const euro = (x) => x.toLocaleString("de-AT", { style: "currency", currency: "EUR" });
  const datum = (iso) => new Date(iso + "T00:00:00").toLocaleDateString("de-AT", { weekday: "short", day: "2-digit", month: "2-digit" });

  let zeilen = [];
  let naechsteId = 1;
  const hoerer = new Set();

  // Nur was man zum Anzeigen und Rechnen braucht (nicht die ganzen Nährwerte usw.)
  const FELDER = ["id", "kette", "name", "preis", "normalpreis", "ab_menge", "menge", "einheit", "pro_kg", "gueltig_von",
    "gueltig_bis", "url", "bild", "zusatzpreis", "zusatz_text", "aktion", "merkmale"];
  function schnappschuss(a) {
    a = a.roh ?? a; // mit Kundenkarte umgerechnet (vorlieben.js) -> Original speichern
    const s = {};
    for (const f of FELDER) if (a[f] != null) s[f] = a[f];
    return s;
  }

  function lesen(schluessel) {
    try { return JSON.parse(localStorage.getItem(schluessel)); } catch { return null; }
  }

  // Gespeicherte Liste laden; beim ersten Mal die alten Listen (Startseite, einkauf.html) übernehmen
  function laden() {
    const gespeichert = lesen(SCHLUESSEL);
    let roh = Array.isArray(gespeichert) ? gespeichert : null;
    if (!roh) {
      roh = [];
      const v1 = lesen("aktionenfitness.einkauf.v1") || {};
      if (Array.isArray(v1.zeilen)) roh.push(...v1.zeilen);
      else if (typeof v1.liste === "string") roh.push(...A.parseListe(v1.liste).map((e) => ({ text: e.text })));
      for (const { angebot, anzahl } of Object.values(lesen("aktionenfitness.liste.v1") || {})) {
        if (angebot?.name) roh.push({ text: angebot.name, angebot: schnappschuss(angebot), anzahl: anzahl || 1 });
      }
    }
    zeilen = roh.filter((z) => z && z.text).map((z) => ({
      id: naechsteId++, text: String(z.text), erledigt: !!z.erledigt,
      ...(z.angebot ? { angebot: z.angebot, anzahl: Math.max(1, z.anzahl || 1) } : {}),
    }));
    if (!gespeichert && zeilen.length) speichern(false);
  }

  function speichern(melden = true) {
    try {
      localStorage.setItem(SCHLUESSEL, JSON.stringify(zeilen.map(({ id, ...rest }) => rest)));
    } catch { /* privater Modus */ }
    if (melden) for (const f of hoerer) f();
  }

  // ---------- Ändern ----------
  function hinzufuegen(text) {
    const neu = A.parseListe(text).map((e) => ({ id: naechsteId++, text: e.text, erledigt: false }));
    zeilen.push(...neu);
    if (neu.length) speichern();
    return neu.length;
  }
  function angebotHinzufuegen(a) {
    const z = zeilen.find((x) => x.angebot?.id === a.id);
    if (z) { z.anzahl++; z.erledigt = false; }
    else zeilen.push({ id: naechsteId++, text: a.name, erledigt: false, angebot: schnappschuss(a), anzahl: 1 });
    speichern();
  }
  const anzahlVon = (angebotId) => zeilen.find((z) => z.angebot?.id === angebotId)?.anzahl ?? 0;
  function setzeAnzahl(z, n) {
    if (n <= 0) zeilen = zeilen.filter((x) => x !== z);
    else z.anzahl = n;
    speichern();
  }
  function entfernen(z) { zeilen = zeilen.filter((x) => x !== z); speichern(); }
  function abhaken(z, ja) { z.erledigt = ja; speichern(); }
  function hakenWeg() { for (const z of zeilen) z.erledigt = false; speichern(); }
  function erledigteWeg() { zeilen = zeilen.filter((z) => !z.erledigt); speichern(); }
  function leeren() { zeilen = []; speichern(); }

  // ---------- Auswerten ----------
  function eintragFuer(z) {
    const e = A.parseZeile(z.text) || { text: z.text, name: z.text, begriff: z.text, woerter: [], anzahl: 1, menge: null, einheit: null };
    if (z.angebot) Object.assign(e, { fest: z.angebot, anzahl: z.anzahl || 1, menge: null, einheit: null, name: z.angebot.name });
    return e;
  }

  // -> { paare: [{ zeile, eintrag }], r: Ergebnis von Abgleich.auswerten, wahl: Map(eintrag -> treffer) }
  function auswerten(angebote, optionen = {}) {
    const paare = zeilen.map((zeile) => ({ zeile, eintrag: eintragFuer(zeile) }));
    const r = A.auswerten(paare.map((p) => p.eintrag), angebote, optionen);
    const wahl = new Map();
    for (const xs of Object.values(r.aufteilung)) for (const x of xs) wahl.set(x.eintrag, x.treffer);
    return { paare, r, wahl };
  }

  // Keine Aktion am Einkaufstag? Dann die nächste kommende (oder gerade abgelaufene) Aktion suchen
  function andererTag(e, angebote, tag) {
    if (!tag) return null;
    const alle = A.finde(e, angebote, null);
    const kommend = alle.filter((t) => t.angebot.gueltig_von && t.angebot.gueltig_von > tag)
      .sort((x, y) => x.angebot.gueltig_von.localeCompare(y.angebot.gueltig_von));
    if (kommend.length) return { treffer: kommend[0], text: `ab ${datum(kommend[0].angebot.gueltig_von)}` };
    const vorbei = alle.filter((t) => t.angebot.gueltig_bis && t.angebot.gueltig_bis < tag);
    if (vorbei.length) return { treffer: vorbei[0], text: `nur bis ${datum(vorbei[0].angebot.gueltig_bis)}` };
    return null;
  }

  function badge(kette) {
    const b = document.createElement("span");
    b.className = `badge badge--kette badge--${kette}`;
    b.textContent = KETTEN[kette] ?? kette;
    return b;
  }

  function mengeText(e) {
    const teile = [];
    if (e.anzahl && e.anzahl !== 1) teile.push(`${e.anzahl.toLocaleString("de-AT")} ×`);
    if (e.menge) {
      if (e.einheit === "stk") teile.push(`${e.menge}er`);
      else if (e.menge >= 1000) teile.push(`${(e.menge / 1000).toLocaleString("de-AT")} ${e.einheit === "g" ? "kg" : "l"}`);
      else teile.push(`${e.menge.toLocaleString("de-AT")} ${e.einheit}`);
    }
    return teile.join(" ");
  }

  // Symbol "Rechteck mit Pfeil" (öffnen/springen)
  function pfeilSymbol() {
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("width", "18");
    svg.setAttribute("height", "18");
    svg.setAttribute("aria-hidden", "true");
    for (const d of ["M14 4h6v6", "M20 4l-9 9", "M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"]) {
      const p = document.createElementNS(ns, "path");
      p.setAttribute("d", d);
      svg.append(p);
    }
    return svg;
  }

  // Knopf zur Aktion: Händlerseite (neuer Tab) oder – ohne Händlerseite, z. B. Spar-Flugblatt – ctx.zeigen(angebot)
  function zurAktion(a, ctx) {
    const url = sichereUrl(a.url);
    let el;
    if (url) {
      el = document.createElement("a");
      el.href = url;
      el.target = "_blank";
      el.rel = "noopener noreferrer";
      el.title = `${a.name} bei ${KETTEN[a.kette] ?? a.kette} öffnen`;
    } else if (ctx.zeigen) {
      el = document.createElement("button");
      el.type = "button";
      el.title = `${a.name} anzeigen`;
      el.addEventListener("click", () => ctx.zeigen(a));
    } else return null;
    el.className = "ek-vorschau__link";
    el.setAttribute("aria-label", el.title);
    el.append(pfeilSymbol());
    return el;
  }

  // Liste in ein <ul> zeichnen: Kreis zum Abhaken, Name + Menge, bestes Angebot, ✕ zum Löschen.
  // ctx: { angebote, tag, mitDaten } – für den Hinweis "ab Do 26.11." bei Aktionen an einem anderen Tag
  function zeichnen(ul, { paare, wahl }, ctx = {}) {
    ul.replaceChildren(...paare.map(({ zeile, eintrag: e }) => {
      const li = document.createElement("li");
      const t = wahl.get(e);
      li.className = (t ? "ok" : "fehlt") + (zeile.erledigt ? " erledigt" : "");

      const haken = document.createElement("input");
      haken.type = "checkbox";
      haken.className = "ek-vorschau__haken";
      haken.checked = zeile.erledigt;
      haken.setAttribute("aria-label", `${e.name} abhaken`);
      haken.addEventListener("change", () => abhaken(zeile, haken.checked));

      const name = document.createElement("span");
      name.className = "ek-vorschau__name";
      name.textContent = e.name;
      const menge = mengeText(e);
      if (menge) {
        const m = document.createElement("small");
        m.textContent = menge;
        name.append(" ", m);
      }

      const rechts = document.createElement("span");
      rechts.className = "ek-vorschau__wo";
      if (t) {
        rechts.append(badge(t.angebot.kette), " ", euro(t.kosten.preis));
        rechts.title = t.angebot.name;
        // Darunter: wie viele Packungen, Mengenaktion, Kartenpreis
        const detail = [A.packungText(t), t.kosten.hinweis, t.angebot.karte ? `💳 ${t.angebot.karte}` : null].filter(Boolean);
        if (detail.length) {
          const d = document.createElement("small");
          d.className = "ek-vorschau__detail" + (t.kosten.aktionGilt ? "" : " ek-vorschau__detail--warn");
          d.textContent = detail.join(" · ");
          name.append(d);
        }
      } else {
        const anders = ctx.mitDaten === false ? null : andererTag(e, ctx.angebote || [], ctx.tag);
        if (anders) {
          li.classList.add("spaeter");
          rechts.append(badge(anders.treffer.angebot.kette), " ", anders.text);
          rechts.title = `${anders.treffer.angebot.name}: am Einkaufstag nicht gültig`;
        } else rechts.textContent = ctx.mitDaten === false ? "keine Daten" : "keine Aktion";
      }

      const label = document.createElement("label");
      label.append(haken, name, rechts);
      li.append(label);
      const ziel = t?.angebot ?? (li.classList.contains("spaeter") ? andererTag(e, ctx.angebote || [], ctx.tag)?.treffer.angebot : null);
      const link = ziel && zurAktion(ziel, ctx);
      if (link) li.append(link);

      if (zeile.angebot) { // fest gewähltes Angebot: Stückzahl mit − / +
        const stepper = document.createElement("span");
        stepper.className = "ek-stepper";
        const minus = document.createElement("button");
        minus.type = "button"; minus.textContent = "−"; minus.setAttribute("aria-label", `${e.name}: eins weniger`);
        minus.addEventListener("click", () => setzeAnzahl(zeile, zeile.anzahl - 1));
        const plus = document.createElement("button");
        plus.type = "button"; plus.textContent = "+"; plus.setAttribute("aria-label", `${e.name}: eins mehr`);
        plus.addEventListener("click", () => setzeAnzahl(zeile, zeile.anzahl + 1));
        stepper.append(minus, plus);
        li.append(stepper);
      }

      const weg = document.createElement("button");
      weg.type = "button";
      weg.className = "icon-knopf ek-vorschau__weg";
      weg.textContent = "✕";
      weg.setAttribute("aria-label", `${e.name} löschen`);
      weg.addEventListener("click", () => entfernen(zeile));
      li.append(weg);
      return li;
    }));
  }

  // Nur sichere Links/Bilder aus den Daten übernehmen: https/http oder relative Pfade (data/bilder/…),
  // niemals "javascript:" o. ä.
  function sichereUrl(url) {
    if (typeof url !== "string" || !url) return null;
    try {
      const u = new URL(url, global.location?.href ?? "https://example.invalid/");
      if (u.protocol === "https:" || u.protocol === "http:") return u.href;
      if (u.protocol === "file:" && !/^[a-z][a-z0-9+.-]*:/i.test(url)) return url; // relativer Pfad bei Doppelklick-Öffnen
    } catch { /* ungültig */ }
    return null;
  }

  // Für die Notizen-App: "* 12x Eier", "* 1kg Karotten" – nur für die gewählten Geschäfte.
  // optionen: { ketten: Set (leer = alle), ohneAktion: true, erledigte: false }
  function alsNotiz({ paare, wahl }, optionen = {}) {
    const ketten = optionen.ketten ?? new Set();
    const gruppen = new Map();
    for (const { zeile, eintrag: e } of paare) {
      if (zeile.erledigt && !optionen.erledigte) continue;
      const t = wahl.get(e);
      let gruppe;
      if (t) {
        if (ketten.size && !ketten.has(t.angebot.kette)) continue;
        gruppe = KETTEN[t.angebot.kette] ?? t.angebot.kette;
      } else {
        if (optionen.ohneAktion === false) continue;
        gruppe = "Sonstiges";
      }
      const text = zeile.angebot ? `${zeile.anzahl > 1 ? `${zeile.anzahl}x ` : ""}${zeile.angebot.name}` : zeile.text;
      if (!gruppen.has(gruppe)) gruppen.set(gruppe, []);
      gruppen.get(gruppe).push(`* ${text.replace(/\s+/g, " ").trim()}`);
    }
    // Ein Geschäft (plus Sonstiges): einfache Liste ohne Überschriften
    const mitAktion = [...gruppen.keys()].filter((g) => g !== "Sonstiges");
    if (mitAktion.length <= 1) return [...gruppen.values()].flat().join("\n");
    return [...gruppen].map(([g, xs]) => `${g}:\n${xs.join("\n")}`).join("\n\n");
  }

  // Als Text zum Teilen/Kopieren, nach Geschäft gruppiert
  function alsText({ paare, wahl }) {
    const gruppen = new Map();
    for (const { zeile, eintrag: e } of paare) {
      const t = wahl.get(e);
      const k = t ? KETTEN[t.angebot.kette] ?? t.angebot.kette : "Ohne Aktion";
      if (!gruppen.has(k)) gruppen.set(k, []);
      gruppen.get(k).push(`${zeile.erledigt ? "☑" : "☐"} ${zeile.angebot && zeile.anzahl > 1 ? `${zeile.anzahl}× ` : ""}${zeile.angebot ? e.name : zeile.text}` +
        (t ? ` – ${euro(t.kosten.preis)}` : ""));
    }
    const zeilenText = ["Einkaufsliste"];
    for (const [k, xs] of gruppen) zeilenText.push("", `${k}:`, ...xs);
    return zeilenText.join("\n");
  }

  global.addEventListener?.("storage", (ev) => {
    if (ev.key !== SCHLUESSEL) return;
    laden();
    for (const f of hoerer) f();
  });

  laden();
  global.Einkaufsliste = {
    get zeilen() { return zeilen; },
    hinzufuegen, angebotHinzufuegen, anzahlVon, setzeAnzahl, entfernen, abhaken, hakenWeg, erledigteWeg, leeren,
    auswerten, zeichnen, alsText, alsNotiz, sichereUrl, badge, KETTEN,
    beiAenderung(f) { hoerer.add(f); },
  };
})(typeof window !== "undefined" ? window : globalThis);
