// Einkaufsliste ↔ Aktionen abgleichen. Reine Logik ohne Oberfläche, läuft im Browser und in Node (Tests).
//
//   parseListe("- 2x Milch\n• Haferflocken 1kg")  -> [{ text, begriff, anzahl, menge, einheit }, …]
//   finde(eintrag, angebote)                      -> Treffer sortiert nach Passgenauigkeit
//   auswerten(liste, angebote, optionen)          -> Treffer pro Eintrag + Zusammenfassung pro Geschäft

(function (global) {
  "use strict";

  // ---------- Normalisierung ----------
  function norm(text) {
    return String(text)
      .toLowerCase()
      .replace(/ä/g, "a").replace(/ö/g, "o").replace(/ü/g, "u").replace(/ß/g, "ss")
      .replace(/[‘’'`´]/g, "")
      .replace(/(\w)-(\w)/g, "$1$2") // "Hühner-Innenfilet" -> "huhnerinnenfilet" (Komposita)
      .replace(/[^a-z0-9%]+/g, " ")
      .trim();
  }

  // Einfache Stammform: Mehrzahl/Endungen weg ("tomaten" -> "tomat", "eier" -> "eier")
  function stamm(w) {
    return w.length > 4 ? w.replace(/(en|n|e|s)$/, "") : w;
  }

  // Synonyme (normalisiert). Gilt auch für Wortteile: "hendlfilet" -> "huhnfilet", "hahnchenfilet" …
  const SYNONYME = [
    ["topfen", "quark"],
    ["erdapfel", "kartoffel"],
    ["hendl", "huhn", "huhner", "hahnchen", "haehnchen"],
    ["brust", "filet"],
    ["faschiert", "hackfleisch", "hack"],
    ["paradeiser", "tomate"],
    ["karfiol", "blumenkohl"],
    ["schlagobers", "schlagsahne", "obers", "sahne"],
    ["marille", "aprikose"],
    ["semmel", "brotchen", "weckerl"],
    ["kren", "meerrettich"],
    ["jogurt", "joghurt"],
    ["nudeln", "pasta", "teigwaren"],
    ["faschiertes", "hackfleisch"],
    ["eierschwammerl", "pfifferling"],
    ["zwetschke", "pflaume"],
    ["fisolen", "grune bohnen"],
    ["kohlsprossen", "rosenkohl"],
    ["melanzani", "aubergine"],
    ["ribisel", "johannisbeere"],
    ["rindfleisch", "rind", "rinds"],
    ["schweinefleisch", "schwein", "schweins"],
    ["klopapier", "toilettenpapier"],
    ["rote bete", "rote ruben", "rote rube", "randen"],
  ];

  // Alle Schreibweisen eines Wortes über Synonyme, auch kombiniert ("huhnerbrust" -> "hendlfilet")
  const _varianten = new Map();
  function varianten(wort) {
    if (_varianten.has(wort)) return _varianten.get(wort);
    const v = new Set([wort]);
    for (let runde = 0; runde < 2; runde++) {
      for (const w of [...v]) {
        for (const gruppe of SYNONYME) {
          for (const a of gruppe) {
            if (a.includes(" ") || !w.includes(a)) continue;
            for (const b of gruppe) if (b !== a && !b.includes(" ")) v.add(w.replace(a, b));
          }
        }
      }
    }
    const liste = [...v];
    _varianten.set(wort, liste);
    return liste;
  }

  // ---------- Liste parsen ----------
  const EINHEITEN = { g: ["g", 1], gramm: ["g", 1], kg: ["g", 1000], kilo: ["g", 1000], ml: ["ml", 1], l: ["ml", 1000],
    liter: ["ml", 1000], stk: ["stk", 1], stuck: ["stk", 1], st: ["stk", 1], pkg: ["stk", 1], packung: ["stk", 1],
    packungen: ["stk", 1], flasche: ["stk", 1], flaschen: ["stk", 1], dose: ["stk", 1], dosen: ["stk", 1] };
  const FUELLWOERTER = new Set(["und", "oder", "von", "vom", "fur", "mit", "ohne", "eine", "einen", "ein", "etwas", "paar",
    "viel", "frisch", "frische", "frischer", "frisches", "die", "der", "das"]);

  function parseZeile(zeile) {
    let text = zeile.replace(/^\s*(?:[-*•·–>]|\d+[.)])\s*/, "").trim(); // Aufzählungszeichen weg
    if (!text) return null;
    let anzahl = 1, menge = null, einheit = null;

    // "2x Milch", "Milch x2", "2 x Milch"
    text = text.replace(/(?:^|\s)(\d+)\s*[x×]\s*|\s*[x×]\s*(\d+)\s*$/i, (_, a, b) => { anzahl = Number(a || b); return " "; });
    // "500g", "1,5 kg", "2 l", "3 Stk"
    text = text.replace(/(\d+(?:[.,]\d+)?)\s*(kg|kilo|gramm|g|ml|liter|l|stk|stück|stuck|st|pkg|packungen?|flaschen?|dosen?)\b\.?/i,
      (_, zahl, e) => {
        const [einh, faktor] = EINHEITEN[norm(e)] || [null, 1];
        const wert = Number(zahl.replace(",", ".")) * faktor;
        if (einh === "stk") anzahl = wert; else { menge = wert; einheit = einh; }
        return " ";
      });
    // "3 Bananen" (Zahl ohne Einheit am Anfang)
    text = text.replace(/^\s*(\d+)\s+(?=\D)/, (_, a) => { anzahl = Number(a); return ""; });

    const woerter = norm(text).split(" ").filter((w) => w && !FUELLWOERTER.has(w) && !/^\d+$/.test(w));
    if (!woerter.length) return null;
    return { text: zeile.trim().replace(/^\s*(?:[-*•·–>]|\d+[.)])\s*/, ""), begriff: woerter.join(" "), woerter, anzahl, menge, einheit,
      bio: woerter.includes("bio") };
  }

  function parseListe(text) {
    return String(text).split(/\r?\n|;/).map(parseZeile).filter(Boolean);
  }

  // ---------- Passgenauigkeit ----------
  // Wie gut passt ein Suchwort zu einem Wort im Produktnamen? Deutsche Komposita: Kopf steht hinten.
  //   "milch" ~ "milch"         1.0  (genau)
  //   "milch" ~ "vollmilch"     0.9  (Kopf des Kompositums: ist Milch)
  //   "milch" ~ "milchschnitte" 0.3  (nur Bestimmungswort: ist keine Milch)
  function wortTreffer(such, wort) {
    let best = 0;
    for (const s of varianten(such)) {
      const ss = stamm(s), ws = stamm(wort);
      if (wort === s || ws === ss) best = Math.max(best, 1);
      else if (s.length >= 3 && (wort.endsWith(s) || ws.endsWith(ss))) {
        const praefix = wort.slice(0, wort.length - s.length);
        best = Math.max(best, ERSATZ_PRAEFIX.some((p) => praefix.endsWith(p)) ? 0.45 : 0.9);
      }
      else if (s.length >= 4 && wort.startsWith(ss)) best = Math.max(best, 0.3);
      else if (s.length >= 5 && wort.includes(ss)) best = Math.max(best, 0.25);
      // Kompositum mit Einschub: "huhnerfilet" ~ "huhnerinnenfilet" (Anfang und Kopf stimmen überein)
      for (let k = 4; k <= s.length - 4; k++) {
        if (wort.length > s.length && wort.startsWith(s.slice(0, k)) && wort.endsWith(s.slice(k))) {
          best = Math.max(best, 0.85);
          break;
        }
      }
    }
    return best;
  }

  function bewerte(eintrag, angebot) {
    const namensWoerter = norm(angebot.name).split(" ").filter(Boolean);
    const woerter = eintrag.woerter.filter((w) => w !== "bio");
    if (!woerter.length) return 0;
    let summe = 0;
    for (const s of woerter) {
      let best = 0;
      for (const w of namensWoerter) best = Math.max(best, wortTreffer(s, w));
      // Mehrwortsynonyme ("rote bete" ~ "rote ruben")
      if (!best && woerter.length > 1) best = 0;
      if (best === 0) return 0; // jedes Suchwort muss vorkommen
      summe += best;
    }
    let punkte = summe / woerter.length;
    // Verarbeitete Produkte abwerten, außer man sucht genau danach
    const sucheText = woerter.join(" ");
    if (namensWoerter.some((w) => istVerarbeitet(w) && !woerter.some((s) => w.includes(s) && istVerarbeitet(s))
        && !sucheText.includes(w))) punkte *= 0.5;
    const kat = angebot.kategorie ? norm(angebot.kategorie) : "";
    if (kat && KATEGORIE_VERARBEITET.test(kat) && !woerter.some((w) => kat.includes(stamm(w)))) punkte *= 0.5;
    if (eintrag.bio && !namensWoerter.includes("bio") && !namensWoerter.some((w) => w.startsWith("bio"))) punkte *= 0.6;
    // kurze, eindeutige Namen leicht bevorzugen ("Vollmilch 1l" vor "Vollmilch Schokolade mit …")
    punkte += 0.05 / Math.max(1, namensWoerter.length - woerter.length);
    return Math.min(1, punkte);
  }

  // Wörter, die ein verarbeitetes Produkt kennzeichnen. Stehen sie im Namen, aber nicht in der Suche,
  // ist es wahrscheinlich nicht das Gesuchte ("Bananen" -> nicht "Bananen-Eis").
  // Gilt für ganze Wörter und für das Ende zusammengesetzter Wörter ("proteindrink", "laugenbaguette").
  const VERARBEITET = ["eis", "strudel", "croissant", "plunderteig", "blatterteig", "pizzateig", "germteig", "drink", "shake",
    "riegel", "chips", "curry", "auflauf", "pfanne", "dippers", "basis", "fix", "baguette", "pizza", "snack", "kuchen",
    "torte", "tortina", "pudding", "dessert", "chicken", "nugget", "nuggets", "cremissimo", "magnum", "sauce", "sugo",
    "aufstrich", "schnitte", "rulade", "nikolo", "krampus", "adventkalender", "intermezzo", "bonbon", "keks", "kekse",
    "wurfel", "noodles", "suppe", "laibchen", "nudelgericht", "fertiggericht"];
  function istVerarbeitet(w) {
    return VERARBEITET.some((m) => w === m || (m.length >= 4 && w.endsWith(m)));
  }
  // Ersatzprodukte: Präfix + Suchwort ist etwas anderes ("Hafermilch" ist keine Milch)
  const ERSATZ_PRAEFIX = ["kokosnuss", "kokos", "hafer", "mandel", "soja", "reis", "karfiol", "schoko", "erdnuss", "kakao",
    "butter", "dinkel", "erbsen", "vanille", "erdbeer"];
  // Händler-Kategorien für verarbeitete Produkte (Billa/Penny liefern sie mit)
  const KATEGORIE_VERARBEITET = /\beis\b|eiscreme|tiefkuhlgerichte|fertiggerichte|susses|knabber|dessert|snack/; // \b: nicht "Fleisch"

  const SCHWELLE = 0.6;

  // ---------- Preise ----------
  function grundpreis(a, preis = a.preis) {
    if (a.pro_kg) return { wert: preis, einheit: "kg" };
    if (!a.menge) return null;
    if (a.einheit === "g") return { wert: (preis / a.menge) * 1000, einheit: "kg" };
    if (a.einheit === "ml") return { wert: (preis / a.menge) * 1000, einheit: "l" };
    if (a.einheit === "stk") return { wert: preis / a.menge, einheit: "Stück" };
    return null;
  }

  // Wie viele Packungen braucht man, was kostet das? Berücksichtigt "ab 2 Stück"-Aktionen.
  function kosten(eintrag, a) {
    let stueck = eintrag.anzahl || 1;
    if (eintrag.menge && a.menge && eintrag.einheit === a.einheit) stueck = Math.max(1, Math.ceil(eintrag.menge / a.menge - 1e-9));
    if (eintrag.menge && a.pro_kg && eintrag.einheit === "g") stueck = eintrag.menge / 1000; // kg-Ware
    const aktionGilt = !a.ab_menge || stueck >= a.ab_menge;
    const einzel = aktionGilt ? a.preis : (a.normalpreis || a.preis);
    const normal = a.normalpreis || null;
    return {
      stueck,
      preis: einzel * stueck,
      ersparnis: normal && aktionGilt ? (normal - a.preis) * stueck : 0,
      aktionGilt,
      hinweis: !aktionGilt ? `Aktion erst ab ${a.ab_menge} Stück` : null,
    };
  }

  // ---------- Suchen ----------
  function gueltigAm(a, tag) {
    if (!tag) return true;
    if (a.gueltig_von && a.gueltig_von > tag) return false;
    if (a.gueltig_bis && a.gueltig_bis < tag) return false;
    return true;
  }

  function finde(eintrag, angebote, tag) {
    const treffer = [];
    for (const a of angebote) {
      if (!gueltigAm(a, tag)) continue;
      const p = bewerte(eintrag, a);
      if (p >= SCHWELLE) treffer.push({ angebot: a, punkte: p, kosten: kosten(eintrag, a), grundpreis: grundpreis(a) });
    }
    // Erst Passgenauigkeit (gerundet, damit fast gleich gute Treffer nach Preis sortiert werden), dann Grundpreis
    return treffer.sort((x, y) =>
      Math.round(y.punkte * 10) - Math.round(x.punkte * 10) ||
      (x.grundpreis?.wert ?? x.kosten.preis) - (y.grundpreis?.wert ?? y.kosten.preis));
  }

  // Was man tatsächlich pro kg/l/Stück zahlt (Mengenaktion nicht erreicht -> Normalpreis).
  // Ohne Mengenangabe: Gesamtpreis für den Eintrag.
  function effektiv(eintrag, t) {
    const a = t.angebot;
    if (a.pro_kg) return t.kosten.preis / Math.max(t.kosten.stueck, 1e-9);
    if (a.menge && t.kosten.stueck) return t.kosten.preis / (t.kosten.stueck * a.menge) * 1000;
    return t.kosten.preis;
  }

  // ---------- Auswertung ----------
  // optionen: { tag: "2026-11-20", ausgeschlossen: Set(angebot.id) }
  function auswerten(liste, angebote, optionen = {}) {
    const aus = optionen.ausgeschlossen || new Set();
    const nutzbar = angebote.filter((a) => !aus.has(a.id));
    const eintraege = liste.map((e) => {
      const treffer = finde(e, nutzbar, optionen.tag);
      const bestProKette = {};
      for (const t of treffer) if (!bestProKette[t.angebot.kette]) bestProKette[t.angebot.kette] = t;
      return { eintrag: e, treffer, bestProKette };
    });

    // Pro Geschäft: wie viele Einträge sind dort in Aktion, was kosten sie, wie viel spart man?
    const ketten = {};
    for (const { bestProKette } of eintraege) {
      for (const [k, t] of Object.entries(bestProKette)) {
        const z = (ketten[k] ||= { kette: k, anzahl: 0, preis: 0, ersparnis: 0 });
        z.anzahl++;
        z.preis += t.kosten.preis;
        z.ersparnis += t.kosten.ersparnis;
      }
    }
    const rangliste = Object.values(ketten).sort((a, b) => b.anzahl - a.anzahl || b.ersparnis - a.ersparnis || a.preis - b.preis);

    // Günstigste Aufteilung: jeder Eintrag im Geschäft mit dem besten (passenden) Angebot.
    // Unter den gut passenden Treffern (≥ 90 % der besten Punktzahl) zählt der Grundpreis.
    const aufteilung = {};
    const ohneAktion = [];
    for (const e of eintraege) {
      if (!e.treffer.length) { ohneAktion.push(e.eintrag); continue; }
      const spitze = e.treffer[0].punkte;
      const gut = e.treffer.filter((t) => t.punkte >= spitze * 0.8);
      const wahl = gut.reduce((m, t) => (effektiv(e.eintrag, t) < effektiv(e.eintrag, m) ? t : m));
      (aufteilung[wahl.angebot.kette] ||= []).push({ eintrag: e.eintrag, treffer: wahl });
    }
    return { eintraege, rangliste, aufteilung, ohneAktion };
  }

  const api = { norm, stamm, varianten, parseZeile, parseListe, wortTreffer, bewerte, grundpreis, kosten, effektiv, finde, auswerten, SCHWELLE };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else global.Abgleich = api;
})(typeof window !== "undefined" ? window : globalThis);
