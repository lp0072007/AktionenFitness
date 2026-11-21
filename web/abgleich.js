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
    ["huttenkase", "cottage"],
    ["huhnerbrust", "huhnerfilet", "hendlfilet"],
    ["erdnussbutter", "erdnussmus", "erdnusscreme"],
    ["haferflocken", "haferflocke"],
    ["griechisch", "greek"],
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

  // Aufzählungszeichen und Abhakkästchen am Zeilenanfang: "- ", "• ", "1. ", "[ ] ", "☐ ", "- [x] "
  const AUFZAEHLUNG = /^\s*(?:(?:[-*•·–>+]|\d+[.)])\s*)?(?:\[[ xX]?\]|[☐☑✓✔])?\s*/;

  function parseZeile(zeile) {
    const original = zeile.replace(AUFZAEHLUNG, "").trim();
    let text = original;
    if (!text || text.startsWith("#") || /:\s*$/.test(text)) return null; // leer, Kommentar, Überschrift "Kühlregal:"
    let anzahl = 1, menge = null, einheit = null;

    // Klammern sind Notizen: Mengen darin zählen, der Rest nicht ("Eier (10er)", "Skyr (Natur, 2 Stk)")
    text = text.replace(/\(([^)]*)\)/g, (_, innen) => {
      const m = innen.match(/\d+(?:[.,]\d+)?\s*(?:er\b|[x×]|kg|kilo|gramm|g|ml|liter|l|stk|stück|stuck|st|pkg|packungen?|flaschen?|dosen?)\b\.?/i);
      return m ? ` ${m[0]} ` : " ";
    });
    // "½ kg", "1/2 l"
    text = text.replace(/½/g, "0.5 ").replace(/\b1\/2\s*(?=[a-z])/gi, "0.5 ").replace(/\b1\/4\s*(?=[a-z])/gi, "0.25 ");
    // "10er Eier", "Eier 6er" -> Packung mit 10 Stück
    text = text.replace(/(\d+)\s*er\b(?:\s*(?:pack(?:ung)?|pkg))?/i, (_, n) => { menge = Number(n); einheit = "stk"; return " "; });

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
    // Anzeigename: wie eingegeben, nur ohne Mengen ("Hüttenkäse", nicht "huttenkase")
    const name = text.replace(/\s+/g, " ").trim().replace(/^[,.\s]+|[,.\s]+$/g, "") || woerter.join(" ");
    return { text: original, name, begriff: woerter.join(" "), woerter, anzahl, menge, einheit,
      bio: woerter.includes("bio") };
  }

  function parseListe(text) {
    // Zeilen, Strichpunkte und Kommas trennen Produkte – aber nicht das Komma in "1,5 kg"
    // (Kommas in Klammern gehören zur Notiz und trennen nichts)
    const geschuetzt = String(text).replace(/\([^)\n]*\)/g, (k) => k.replace(/,/g, "\u0001"));
    return geschuetzt.split(/\r?\n|;|,(?!\d)/).map((z) => parseZeile(z.replace(/\u0001/g, ","))).filter(Boolean);
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

  // Eigenschaften, die nicht jeder Produktname nennt: fehlen sie, passt das Produkt trotzdem (etwas schlechter)
  const EIGENSCHAFTEN = new Set(["light", "mager", "natur", "griechisch", "griechischer", "griechisches", "fettarm", "halbfett",
    "vollfett", "laktosefrei", "ungesusst", "ungezuckert", "zuckerfrei", "tk", "tiefgekuhlt", "gefroren", "gross", "klein",
    "billig", "gunstig", "regional", "osterreichisch", "pur", "plain", "high", "protein", "pro", "frei", "freiland",
    "bodenhaltung", "mittel", "zart", "fein", "grob", "gemischt", "weiss", "braun", "vollkorn"]);
  // Bestimmungswörter, die man vom gesuchten Kompositum abtrennen darf: "Magertopfen" -> auch "Speisetopfen"
  const MODIFIKATOREN = ["mager", "light", "griechisch", "natur", "bio", "fettarm", "halbfett",
    "laktosefrei", "protein", "high"];

  // Sorten, die für ein Produkt praktisch dasselbe sind: "Vollmilch" ~ "H-Milch 3,5 %" ~ "Bergbauernmilch"
  const KOPF_SORTEN = {
    milch: ["voll", "frisch", "h", "haltbar", "haltbare", "heu", "berg", "bergbauern", "alpen", "land", "weide", "fettarm",
      "leicht", "teilentrahmt", "mager", "bio", "roh", "esl", "vollfrisch"],
    joghurt: ["natur", "voll", "mager", "fettarm", "bio", "berg", "bergbauern", "heu"],
    topfen: ["mager", "speise", "halbfett", "bio", "heu"],
    eier: ["freiland", "bodenhaltung", "bio", "frisch"],
  };

  function besterTreffer(s, namensWoerter) {
    let best = 0;
    for (const w of namensWoerter) best = Math.max(best, wortTreffer(s, w));
    if (best < 0.8) {
      const mod = MODIFIKATOREN.find((m) => s.startsWith(m) && s.length - m.length >= 4);
      if (mod) for (const w of namensWoerter) best = Math.max(best, 0.8 * wortTreffer(s.slice(mod.length), w));
    }
    if (best < 0.9) {
      for (const [kopf, sorten] of Object.entries(KOPF_SORTEN)) {
        if (!s.endsWith(kopf) || !sorten.includes(s.slice(0, -kopf.length))) continue;
        for (const w of namensWoerter) best = Math.max(best, 0.9 * wortTreffer(kopf, w));
      }
    }
    return best;
  }

  function bewerte(eintrag, angebot) {
    const namensWoerter = norm(angebot.name).split(" ").filter(Boolean);
    const woerter = eintrag.woerter.filter((w) => w !== "bio");
    if (!woerter.length) return 0;
    const pflicht = woerter.filter((w) => !EIGENSCHAFTEN.has(w));
    const kern = pflicht.length ? pflicht : woerter; // nur Eigenschaften ("Protein")? dann sind sie Pflicht
    let summe = 0, fehlend = 0;
    for (const s of kern) {
      const best = besterTreffer(s, namensWoerter);
      if (best === 0) return 0; // jedes Hauptwort muss vorkommen
      summe += best;
    }
    for (const s of woerter) if (!kern.includes(s) && besterTreffer(s, namensWoerter) < 0.6) fehlend++;
    let punkte = (summe / kern.length) * Math.pow(0.85, fehlend);
    // Steht im Namen eine andere Produktart, die man nicht sucht, ist es etwas anderes:
    // "Milch" -> nicht "Heumilch Gouda" oder "Salzburg Milch Almkönig Scheiben" (beides Käse)
    if (namensWoerter.some((w) => istProduktart(w) && !woerter.some((s) => besterTreffer(s, [w]) >= 0.6))) punkte *= 0.5;
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
    "wurfel", "noodles", "suppe", "laibchen", "nudelgericht", "fertiggericht", "tasche", "taschen", "tascherl", "sandwich",
    "sticks", "stick", "roulade", "likor", "praline", "pralinen", "lebkuchen", "stollen"];
  function istVerarbeitet(w) {
    return VERARBEITET.some((m) => w === m || (m.length >= 4 && w.endsWith(m)));
  }
  // Produktarten: Wörter, die sagen, was ein Produkt eigentlich ist (auch als Kopf eines Kompositums: "Bergkäse")
  const PRODUKTARTEN = ["kase", "gouda", "emmentaler", "edamer", "camembert", "scheiben", "joghurt", "jogurt", "butter",
    "schokolade", "creme", "topfen", "rahm", "obers", "kakao", "wurst", "schinken", "salami", "aufstrich", "kefir",
    "buttermilch", "molke"];
  function istProduktart(w) {
    // auch am Wortanfang: "Käse-Selektion" wird zu "kaseselektion"
    return PRODUKTARTEN.some((m) => w === m || (m.length >= 4 && (w.endsWith(m) || w.startsWith(m))));
  }
  // Ersatzprodukte: Präfix + Suchwort ist etwas anderes ("Hafermilch" ist keine Milch)
  const ERSATZ_PRAEFIX = ["kokosnuss", "kokos", "hafer", "mandel", "soja", "reis", "karfiol", "schoko", "erdnuss", "kakao",
    "butter", "dinkel", "erbsen", "vanille", "erdbeer", "uberraschungs", "nougat", "kaffee", "kokosnuss", "milchreis"];
  // Händler-Kategorien für verarbeitete Produkte (Billa/Penny liefern sie mit)
  const KATEGORIE_VERARBEITET = /\beis\b|eiscreme|pizza|tiefkuhlgerichte|fertiggerichte|susses|knabber|dessert|snack/; // \b: nicht "Fleisch"

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
      let treffer = finde(e, nutzbar, optionen.tag);
      // Fest gewähltes Angebot ("+ Liste" auf einer Karte): steht immer an erster Stelle
      if (e.fest) {
        const a = nutzbar.find((x) => x.id === e.fest.id) || e.fest;
        treffer = [{ angebot: a, punkte: 1, fest: true, kosten: kosten(e, a), grundpreis: grundpreis(a) },
          ...treffer.filter((t) => t.angebot.id !== a.id)];
      }
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
      if (e.treffer[0].fest) { (aufteilung[e.treffer[0].angebot.kette] ||= []).push({ eintrag: e.eintrag, treffer: e.treffer[0] }); continue; }
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
