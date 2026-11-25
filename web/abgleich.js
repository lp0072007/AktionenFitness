// Einkaufsliste ↔ Aktionen abgleichen. Reine Logik ohne Oberfläche, läuft im Browser und in Node (Tests).
//
//   parseListe("- 2x Milch\n• Haferflocken 1kg")  -> [{ text, begriff, anzahl, menge, einheit }, …]
//   finde(eintrag, angebote)                      -> Treffer sortiert nach Passgenauigkeit
//   auswerten(liste, angebote, optionen)          -> Treffer pro Eintrag + Zusammenfassung pro Geschäft

(function (global) {
  "use strict";

  // ---------- Normalisierung ----------
  // Wortgruppen, die zusammen ein Produkt sind, werden zu einem Wort (gilt für Suche und Produktnamen gleich):
  // "Rote Rüben", "Rote Bete", "Rote Beete", "Rotebeete" -> "roteruben"; "grüne Bohnen" -> "fisolen"
  const WORTGRUPPEN = [
    [/\brote ?(?:ruben|rube|beete|bete|beten|beeten)\b/g, "roteruben"],
    [/\bgelbe ?(?:ruben|rube)\b/g, "karotten"],
    [/\bgrune ?bohnen\b/g, "fisolen"],
    [/\bsaure ?(?:sahne|rahm)\b/g, "sauerrahm"],
    [/\bweisse ?bohnen\b/g, "weissebohnen"],
    [/\bstangen ?sellerie\b/g, "staudensellerie"],
    [/\bfrische ?milch\b/g, "frischmilch"],
  ];

  function norm(text) {
    let s = String(text)
      .toLowerCase()
      .replace(/ä/g, "a").replace(/ö/g, "o").replace(/ü/g, "u").replace(/ß/g, "ss")
      .replace(/[‘’'`´]/g, "")
      .replace(/(\w)-(\w)/g, "$1$2") // "Hühner-Innenfilet" -> "huhnerinnenfilet" (Komposita)
      .replace(/[^a-z0-9%]+/g, " ")
      .trim();
    for (const [muster, ersatz] of WORTGRUPPEN) s = s.replace(muster, ersatz);
    return s;
  }

  // Einfache Stammform: Mehrzahl/Endungen weg ("tomaten" -> "tomat", "eier" -> "eier")
  function stamm(w) {
    return w.length > 4 ? w.replace(/(en|n|e|s)$/, "") : w;
  }

  // Synonyme (normalisiert). Gilt auch für Wortteile: "hendlfilet" -> "huhnfilet", "hahnchenfilet" …
  const SYNONYME = [
    ["topfen", "quark"],
    ["erdapfel", "kartoffel"],
    ["hendl", "hendel", "huhn", "huhner", "hahnchen", "haehnchen", "huhnchen", "poulet"],
    ["brust", "filet"],
    ["faschiert", "hackfleisch", "hack"],
    ["paradeiser", "tomate"],
    ["paradeismark", "tomatenmark"],
    ["karfiol", "blumenkohl"],
    ["schlagobers", "schlagsahne", "obers", "sahne"],
    ["marille", "aprikose"],
    ["semmel", "brotchen", "weckerl", "schrippe"],
    ["kren", "meerrettich"],
    ["jogurt", "joghurt"],
    ["nudeln", "pasta", "teigwaren"],
    ["faschiertes", "hackfleisch"],
    ["eierschwammerl", "pfifferling"],
    ["zwetschke", "zwetschge", "pflaume"],
    ["fisolen", "brechbohnen", "prinzessbohnen"],
    ["kohlsprossen", "rosenkohl"],
    ["melanzani", "aubergine"],
    ["ribisel", "ribisl", "johannisbeere"],
    ["rindfleisch", "rind", "rinds"],
    ["schweinefleisch", "schwein", "schweins"],
    ["klopapier", "toilettenpapier"],
    ["roteruben", "randen"],
    ["huttenkase", "cottage"],
    ["huhnerbrust", "huhnerfilet", "hendlfilet"],
    ["erdnussbutter", "erdnussmus", "erdnusscreme"],
    ["haferflocken", "haferflocke"],
    ["griechisch", "greek"],
    ["brokkoli", "broccoli"],
    ["zero", "0%", "zuckerfrei", "fyl"],
    ["riegel", "bar"],
    // Österreichisch <-> Deutsch (weitere)
    ["pute", "puten", "truthahn"],
    ["sauerrahm", "schmand"],
    ["kukuruz", "mais"],
    ["schwammerl", "pilz"],
    ["vogerlsalat", "feldsalat", "rapunzel"],
    ["hauptelsalat", "kopfsalat"],
    ["karotte", "mohre", "mohrrube"],
    ["lauch", "porree"],
    ["pfefferoni", "peperoni"],
    ["heidelbeere", "blaubeere", "schwarzbeere"],
    ["holler", "holunder"],
    ["germ", "hefe"],
    ["staubzucker", "puderzucker"],
    ["grammeln", "grieben"],
    ["geselchte", "selchfleisch", "kassler", "kasseler"],
    ["beiried", "roastbeef"],
    ["schlogel", "keule"],
    ["polenta", "maisgriess"],
    ["kipferl", "croissant"],
    ["krapfen", "berliner"],
    ["palatschinke", "crepe"],
    ["zuckerl", "bonbon"],
    ["powidl", "pflaumenmus"],
    ["leberkase", "fleischkase"],
    ["wurstel", "wurstchen"],
    ["kracherl", "limonade", "limo"],
    ["sprudel", "mineralwasser"],
    ["marmelade", "konfiture"],
    ["nockerl", "spatzle"],
    ["weisskraut", "weisskohl"],
    ["rotkraut", "rotkohl", "blaukraut"],
    ["sauerkraut", "sauerkohl"],
    ["zucchini", "zucchetti"],
    ["eidotter", "dotter", "eigelb"],
    ["hafermilch", "haferdrink"],
    ["sojamilch", "sojadrink"],
    ["mandelmilch", "mandeldrink"],
    ["reismilch", "reisdrink"],
  ];

  // Alle Schreibweisen eines Wortes über Synonyme, auch kombiniert ("huhnerbrust" -> "hendlfilet")
  const _varianten = new Map();
  // Oberbegriffe (nur in eine Richtung): "Nudeln" findet Spaghetti, "Spaghetti" aber keine Penne
  const OBERBEGRIFFE = {
    nudel: ["spaghetti", "penne", "fusilli", "farfalle", "tagliatelle", "linguine", "makkaroni", "maccheroni", "spirelli",
      "rigatoni", "conchiglie", "fleckerl", "hornchen"],
    nuss: ["walnuss", "haselnuss", "cashew", "cashews", "pekannuss", "paranuss", "macadamia"],
    fisch: ["lachs", "thunfisch", "forelle", "kabeljau", "dorsch", "seelachs", "pangasius", "zander", "makrele", "hering"],
  };

  function varianten(wort) {
    if (_varianten.has(wort)) return _varianten.get(wort);
    const v = new Set([wort, stamm(wort)]); // Stammform auch: "semmeln" -> "semmel" -> "brotchen"
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
    for (const [ober, unter] of Object.entries(OBERBEGRIFFE)) {
      if (stamm(wort) === ober || wort === ober || stamm(wort) === ober + "s") unter.forEach((u) => v.add(u));
    }
    const liste = [...v];
    _varianten.set(wort, liste);
    return liste;
  }

  // ---------- Liste parsen ----------
  // Einheiten in allen üblichen Schreibweisen (Groß/Klein egal, Punkt dahinter erlaubt: "1 Kg.", "250 gr")
  //   Gewicht -> g, Volumen -> ml, Gebinde ("Becher", "Glas", "Sack" …) -> Stück
  const EINHEIT_GRUPPEN = [
    ["g", 1, ["g", "gr", "grm", "gramm", "gram"]],
    ["g", 1000, ["kg", "kilo", "kilos", "kilogramm", "kilogram", "kilogr"]],
    ["g", 10, ["dag", "dkg", "deka", "dekagramm"]],
    ["g", 500, ["pfund"]],
    ["ml", 1, ["ml", "milliliter"]],
    ["ml", 10, ["cl", "zentiliter"]],
    ["ml", 100, ["dl", "deziliter"]],
    ["ml", 1000, ["l", "lt", "ltr", "liter", "litre", "litres", "liters"]],
    ["stk", 1, ["stk", "stück", "stueck", "stuck", "st", "pkg", "pck", "pack", "packs", "packung", "packungen", "packerl",
      "flasche", "flaschen", "fl", "dose", "dosen", "becher", "glas", "gläser", "glaeser", "glaser", "sack", "säcke", "saecke",
      "sackerl", "kiste", "kisten", "tray", "trays", "beutel", "netz", "netze", "bund", "bünde", "stange", "stangen",
      "tafel", "tafeln", "schale", "schalen", "tube", "tuben", "karton", "kartons", "rolle", "rollen", "laib", "laibe", "kopf",
      "köpfe", "stange"]],
  ];
  const EINHEITEN = {};
  for (const [einheit, faktor, namen] of EINHEIT_GRUPPEN) for (const n of namen) EINHEITEN[norm(n)] = [einheit, faktor];
  // Längste zuerst, damit "kilogramm" nicht als "kg"/"g" endet; danach Wortende (kein Buchstabe, auch kein Umlaut)
  const EINHEIT_RE = [...new Set(EINHEIT_GRUPPEN.flatMap(([, , n]) => n))].sort((a, b) => b.length - a.length).join("|");
  const NACH_EINHEIT = "(?![a-zäöüß])\\.?";
  const FUELLWOERTER = new Set(["und", "oder", "von", "vom", "fur", "mit", "ohne", "eine", "einen", "ein", "etwas", "paar",
    "viel", "frisch", "frische", "frischer", "frisches", "die", "der", "das", "in", "im", "auf", "aus", "nach", "art", "zum", "zur"]);

  // Aufzählungszeichen und Abhakkästchen am Zeilenanfang: "- ", "• ", "1. ", "[ ] ", "☐ ", "- [x] "
  // "1." nur als Nummer, wenn keine Ziffer folgt: "1.5kg Topfen" ist eine Menge, keine Aufzählung
  const AUFZAEHLUNG = /^\s*(?:(?:[-*•·–>+]|\d+[.)](?!\d))\s*)?(?:\[[ xX]?\]|[☐☑✓✔])?\s*/;

  function parseZeile(zeile) {
    const original = zeile.replace(AUFZAEHLUNG, "").trim();
    let text = original;
    if (!text || text.startsWith("#") || /:\s*$/.test(text)) return null; // leer, Kommentar, Überschrift "Kühlregal:"
    let anzahl = 1, menge = null, einheit = null;

    // Klammern sind Notizen: Mengen darin zählen, der Rest nicht ("Eier (10er)", "Skyr (Natur, 2 Stk)")
    text = text.replace(/\(([^)]*)\)/g, (_, innen) => {
      const m = innen.match(new RegExp(`\\d+(?:[.,]\\d+)?\\s*(?:er\\b|[x×]|(?:${EINHEIT_RE})${NACH_EINHEIT})`, "i"));
      return m ? ` ${m[0]} ` : " ";
    });
    // "½ kg", "1/2 l"
    text = text.replace(/½/g, "0.5 ").replace(/\b1\/2\s*(?=[a-z])/gi, "0.5 ").replace(/\b1\/4\s*(?=[a-z])/gi, "0.25 ");
    // "10er Eier", "Eier 6er" -> Packung mit 10 Stück
    text = text.replace(/(\d+)\s*er\b(?:\s*(?:pack(?:ung)?|pkg))?/i, (_, n) => { menge = Number(n); einheit = "stk"; return " "; });

    // "2x Milch", "Milch x2", "2 x Milch"
    text = text.replace(/(?:^|\s)(\d+)\s*[x×]\s*|\s*[x×]\s*(\d+)\s*$/i, (_, a, b) => { anzahl = Number(a || b); return " "; });
    // "500g", "1,5 kg", "1.5kg", "1 Kilogramm", "250 gr", "10 dag", "2 l", "33cl", "3 Stk", "2 Becher"
    text = text.replace(new RegExp(`(\\d+(?:[.,]\\d+)?)\\s*(${EINHEIT_RE})${NACH_EINHEIT}`, "i"),
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
  // Zuschnitt/Form am Ende eines Wortes: "Lachsfilet" ist Lachs, "Walnusskerne" sind Nüsse, "Paprika-Mix" ist Paprika
  const ZUSCHNITTE = ["kernmischung", "aufschnitt", "schnitzel", "cocktail", "filets", "filet", "steaks", "steak", "stucke",
    "wurfel", "kerne", "kern", "mix"];
  // Sehr kurze Suchwörter, die trotzdem als Ende eines Kompositums zählen ("Öl" ~ "Olivenöl")
  const KURZE_KOEPFE = new Set(["ol"]);
  // Synonyme, die nur als ganzes Wort zählen ("Protein Bar" ja, "haltbare" nein)
  const NUR_GENAU = new Set(["bar"]);

  // Grundvergleich ohne Zuschnitt: genau (1), Kopf eines Kompositums (0.9, bei Ersatz-Präfix 0.45)
  // Wortenden, die nur zufällig wie das Suchwort enden: "Reis", "Preis", "weiß"/"Weiss" enden auf "eis", sind aber
  // kein Eis ("Wassereis" schon). Geprüft auch an der Stammform ("weiss" -> "weis").
  // "Gurkentopf", "Eintopf" sind kein Topfen (gesucht wird auch die Stammform "topf"); "Pflügelmeier" sind keine Eier.
  const TOPF = /(^|gurken|ein|blumen|koch|suppen|fleisch|linsen|bohnen|erbsen|gemuse|kartoffel|erdapfel|reis|nudel)topf$/;
  const FALSCHE_KOEPFE = { eis: /((?<!wasse)r|w|gl|kr)eiss?$/, topfen: TOPF, topf: TOPF, eier: /(m|schl|f|l|g|matr)eier$/,
    lauch: /(knob|schnitt|bar)lauch$/ };
  // "topf" ist nur die Stammform von "Topfen": auch das Wort "Topf" selbst ("Petersilie im Topf") ist kein Topfen
  const falscherKopf = (s, wort) => (wort !== s || s === "topf") && !!FALSCHE_KOEPFE[s] &&
    (FALSCHE_KOEPFE[s].test(wort) || FALSCHE_KOEPFE[s].test(stamm(wort)));

  function kopfTreffer(s, wort) {
    if (NUR_GENAU.has(s)) return wort === s ? 1 : 0;
    if (falscherKopf(s, wort)) return 0;
    const ss = stamm(s), ws = stamm(wort);
    if (wort === s || ws === ss) return 1;
    if ((s.length >= 3 || KURZE_KOEPFE.has(s)) && (wort.endsWith(s) || ws.endsWith(ss))) {
      const praefix = wort.endsWith(s) ? wort.slice(0, wort.length - s.length) : ws.slice(0, ws.length - ss.length);
      return ERSATZ_PRAEFIX.some((p) => praefix.endsWith(p)) ? 0.45 : 0.9;
    }
    return 0;
  }

  // Ergebnisse merken: Im Sortiment (20 000 Produkte) kommen dieselben Wörter tausendfach vor
  const _wortTreffer = new Map();
  function wortTreffer(such, wort) {
    const schluessel = such + "|" + wort;
    let w = _wortTreffer.get(schluessel);
    if (w === undefined) {
      if (_wortTreffer.size > 500000) _wortTreffer.clear(); // Speicher begrenzen
      _wortTreffer.set(schluessel, (w = wortTrefferRechnen(such, wort)));
    }
    return w;
  }

  function wortTrefferRechnen(such, wort) {
    let best = 0;
    for (const s of varianten(such)) {
      if (NUR_GENAU.has(s)) { if (wort === s) best = 1; continue; }
      if (falscherKopf(s, wort)) continue;
      const ss = stamm(s), ws = stamm(wort);
      for (const z of ZUSCHNITTE) {
        if (wort.endsWith(z) && wort.length - z.length >= 3 && !s.endsWith(z)) {
          best = Math.max(best, 0.95 * kopfTreffer(s, wort.slice(0, -z.length)));
          break;
        }
      }
      if (wort === s || ws === ss) best = Math.max(best, 1);
      else if ((s.length >= 3 || KURZE_KOEPFE.has(s)) && (wort.endsWith(s) || ws.endsWith(ss))) {
        const praefix = wort.endsWith(s) ? wort.slice(0, wort.length - s.length) : ws.slice(0, ws.length - ss.length);
        best = Math.max(best, ERSATZ_PRAEFIX.some((p) => praefix.endsWith(p)) ? 0.45 : 0.9);
      }
      else if (s.length >= 4 && wort.startsWith(ss)) best = Math.max(best, 0.3);
      else if (s.length >= 5 && wort.includes(ss)) best = Math.max(best, 0.25);
      // Kompositum mit Einschub: "huhnerfilet" ~ "huhnerinnenfilet", "hendlfilet" ~ "maishendlinnenfilet"
      for (let k = 4; k <= s.length - 4; k++) {
        const vorne = s.slice(0, k), hinten = s.slice(k), pos = wort.indexOf(vorne);
        if (wort.length > s.length && pos >= 0 && pos + k <= wort.length - hinten.length &&
            (wort.endsWith(hinten) || ws.endsWith(stamm(hinten)))) {
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
    "laktosefrei", "protein", "high", "tiefkuhl", "tk"];

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
        const faktor = kopf === "milch" ? 0.9 : 0.75; // Milchsorten sind gleichwertig, Joghurtsorten nicht ganz
        for (const w of namensWoerter) best = Math.max(best, faktor * wortTreffer(kopf, w));
      }
    }
    // Kompositum der Suche auf zwei Wörter im Namen verteilt: "Basmatireis" ~ "Express Reis, Basmati"
    if (best < 0.8 && s.length >= 8 && namensWoerter.length > 1) {
      for (let k = 4; k <= s.length - 4; k++) {
        const a = Math.max(...namensWoerter.map((w) => kopfTreffer(s.slice(0, k), w)));
        if (a < 0.85) continue;
        const b = Math.max(...namensWoerter.map((w) => wortTreffer(s.slice(k), w)));
        if (b >= 0.85) best = Math.max(best, 0.85 * Math.min(a, b));
      }
    }
    return best;
  }

  // Schneller Vorfilter (wichtig fürs Sortiment mit 20 000 Produkten): Damit besterTreffer(s, …) > 0 sein kann,
  // muss der Name den Anfang (bis 4 Zeichen) einer Schreibweise von s enthalten – das gilt für alle Wege in
  // wortTreffer (Ende, Anfang, Teil, Einschub) und besterTreffer (Modifikator weg, Sorte, auf zwei Wörter verteilt).
  // Fehlt jeder dieser Anfänge, ist das Ergebnis sicher 0 und die teure Rechnung entfällt.
  const _anfaenge = new Map();
  function anfaenge(s) {
    let a = _anfaenge.get(s);
    if (a) return a;
    const quellen = [s];
    const mod = MODIFIKATOREN.find((m) => s.startsWith(m) && s.length - m.length >= 4);
    if (mod) quellen.push(s.slice(mod.length));
    for (const kopf of Object.keys(KOPF_SORTEN)) if (s.endsWith(kopf)) quellen.push(kopf);
    const set = new Set([s.slice(0, 4)]);
    for (const q of quellen) for (const v of varianten(q)) set.add(v.slice(0, Math.min(4, stamm(v).length)));
    a = [...set].filter(Boolean);
    _anfaenge.set(s, a);
    return a;
  }

  function bewerte(eintrag, angebot) {
    const namensWoerter = angebot._woerter ??= norm(angebot.name).split(" ").filter(Boolean);
    const woerter = eintrag.woerter.filter((w) => w !== "bio");
    if (!woerter.length) return 0;
    const pflicht = woerter.filter((w) => !EIGENSCHAFTEN.has(w));
    const kern = pflicht.length ? pflicht : woerter; // nur Eigenschaften ("Protein")? dann sind sie Pflicht
    const text = angebot._text ??= namensWoerter.join(" ");
    if (api.vorfilter) for (const s of kern) if (!NUR_GENAU.has(s) && !anfaenge(s).some((a) => text.includes(a))) return 0;
    let summe = 0, fehlend = 0;
    for (const s of kern) {
      const best = besterTreffer(s, namensWoerter);
      if (best === 0) return 0; // jedes Hauptwort muss vorkommen
      summe += best;
    }
    for (const s of woerter) if (!kern.includes(s) && besterTreffer(s, namensWoerter) < 0.6) fehlend++;
    let punkte = (summe / kern.length) * Math.pow(0.85, fehlend);
    // "Blattspinat mit Schafskäse" ist kein Käse, "Thunfisch in Olivenöl" kein Olivenöl: Steht ein Suchwort nur hinter
    // "mit" oder "in", ist es eine Zutat
    const mitPos = namensWoerter.findIndex((w) => w === "mit" || w === "in");
    const vorne = mitPos > 0 ? namensWoerter.slice(0, mitPos) : namensWoerter; // was das Produkt eigentlich ist
    // Nur wenn vorne gar nichts Gesuchtes steht: "Thunfisch in Öl" findet weiterhin "Thunfisch in Olivenöl"
    if (mitPos > 0 && kern.every((s) => besterTreffer(s, vorne) < 0.6)) punkte *= 0.5;
    // Steht im Namen eine andere Produktart, die man nicht sucht, ist es etwas anderes:
    // "Milch" -> nicht "Heumilch Gouda" oder "Salzburg Milch Almkönig Scheiben" (beides Käse)
    // (nur vor "mit": in "Spinat mit Schafskäse" ist Käse eine Zutat, keine andere Produktart)
    if (vorne.some((w) => istProduktart(w) && !woerter.some((s) => besterTreffer(s, [w]) >= 0.6))) punkte *= 0.5;
    // Verarbeitete Produkte abwerten, außer man sucht genau danach – auch über ein Synonym:
    // "Zuckerl" sucht Bonbons, "Hafermilch" sucht Haferdrinks, "Feldsalat" sucht Vogerlsalat
    const sucheVarianten = eintrag._varianten ??= [...new Set(woerter.flatMap(varianten))];
    const sucheText = sucheVarianten.join(" ");
    if (namensWoerter.some((w) => istVerarbeitet(w) && !sucheVarianten.some((s) => w.includes(s) && istVerarbeitet(s))
        && !sucheText.includes(w))) punkte *= 0.5;
    const kat = angebot._kat ??= angebot.kategorie ? norm(angebot.kategorie) : "";
    // Sucht man selbst ein verarbeitetes Produkt und steht es so im Namen ("Topfenstrudel"), ist die Kategorie
    // kein Gegenargument. Nur als ganzes Wort: "Proteinriegel" macht "Kinder Riegel" nicht passend.
    const gesuchtVerarbeitet = (w) => istVerarbeitet(w) &&
      [w, w.replace(/^(tiefkuhl|tk)(?=.{4})/, "")].some((x) => namensWoerter.some((nw) => wortTreffer(x, nw) >= 0.9)); // "Tiefkühlpizza"
    // Synonyme zählen auch ("Zuckerl" in der Bonbon-Abteilung) – außer bei Fertiggerichten: "Nudeln" ~ "Pasta" macht
    // "Tiefkühlgerichte > Reis & Pasta" (Iglo Pasta Carbonara) nicht passend
    const ausnahme = /gerichte/.test(kat) ? woerter : sucheVarianten;
    if (kat && KATEGORIE_VERARBEITET.test(kat) && !ausnahme.some((w) => kat.includes(stamm(w))) && !woerter.some(gesuchtVerarbeitet)) punkte *= 0.5;
    // Ganzer Produktname gesucht ("Tiroler Adler", "Kaiser Max"): dann gilt die Abteilung nicht als Gegenargument
    const genauerName = kern.length >= 2 && kern.every((s) => namensWoerter.some((w) => wortTreffer(s, w) >= 0.95));
    if (!genauerName) {
      for (const [katRegel, sucheRegel] of KATEGORIE_REGELN) if (kat && katRegel.test(kat) && !sucheRegel.test(sucheText)) punkte *= 0.5;
    }
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
    // kein "cremissimo": "Eis" soll Cremissimo finden (die Eis-Kategorie der Händler reicht zum Abwerten)
    "torte", "tortina", "pudding", "dessert", "chicken", "nugget", "nuggets", "magnum", "sauce", "sugo",
    "aufstrich", "schnitte", "rulade", "nikolo", "krampus", "adventkalender", "intermezzo", "bonbon", "keks", "kekse",
    "wurfel", "noodles", "suppe", "laibchen", "nudelgericht", "fertiggericht", "tasche", "taschen", "tascherl", "sandwich",
    "sticks", "stick", "roulade", "likor", "praline", "pralinen", "lebkuchen", "stollen", "beilage", "ciambella", "milchreis",
    "ketchup", "senf", "salat", "fruchtgummi", "kitkat", "torte", "eiskaffee", "ostereier", "palatschinke", "palatschinken"]; // kein "eis…"-Präfix: Eissalat ist Salat
  function istVerarbeitet(w) {
    return VERARBEITET.some((m) => w === m || (m.length >= 4 && w.endsWith(m)));
  }
  // Produktarten: Wörter, die sagen, was ein Produkt eigentlich ist (auch als Kopf eines Kompositums: "Bergkäse")
  const PRODUKTARTEN = ["kase", "gouda", "emmentaler", "edamer", "camembert", "joghurt", "jogurt", "butter",
    "schokolade", "creme", "topfen", "rahm", "obers", "kakao", "wurst", "schinken", "salami", "aufstrich", "kefir",
    "buttermilch", "molke", "gewurz"];
  function istProduktart(w) {
    // auch am Wortanfang: "Käse-Selektion" wird zu "kaseselektion"
    return PRODUKTARTEN.some((m) => w === m || (m.length >= 4 && (w.endsWith(m) || w.startsWith(m))));
  }
  // Ersatzprodukte: Präfix + Suchwort ist etwas anderes ("Hafermilch" ist keine Milch)
  const ERSATZ_PRAEFIX = ["kokosnuss", "kokos", "hafer", "mandel", "soja", "reis", "karfiol", "schoko", "erdnuss", "kakao",
    "butter", "dinkel", "erbsen", "vanille", "erdbeer", "uberraschungs", "nougat", "kaffee", "see", "lamm", "erd", "granat",
    "zahn", "knusper", "hering", "herings", "makrelen", "nudel", "wurst", "kartoffel", "erdapfel", "ge"]; // "ge": Genuss ≠ Nuss
  // Händler-Kategorien für verarbeitete Produkte (Billa/Penny liefern sie mit)
  const KATEGORIE_VERARBEITET = /\beis\b|eiscreme|pizza|tiefkuhlgerichte|fertiggerichte|susses|knabber|dessert|pudding|snack|torten|mehlspeisen/; // \b: nicht "Fleisch"
  // Händler-Kategorie passt nur, wenn die Suche dazu passt: "Himbeeren" -> kein Himbeer-Sirup (Getränke)
  const KATEGORIE_REGELN = [
    [/\bgetranke\b/, /wasser|cola|saft|sirup|tee\b|kaffee|bier|wein|limo|drink|smoothie|energy|milch|sekt|schnaps|likor|gin\b|rum\b|vodka|whisk|spritzer|soda|tonic|getrank|zero/],
    [/milchalternativ/, /milch|drink/],
    [/susse aufstrich/, /aufstrich|marmelade|konfit|jam\b|honig|nutella|creme/],
    [/\bkase\b|hartkase|frischkase/, /kase|gouda|emmentaler|edamer|mozzarella|cottage|feta|parmesan|cheddar|camembert|brie|raclette|aufstrich|halloumi|ricotta|mascarpone|scheiben/],
    // MPreis-Kategorien (gelten auch für andere Händler mit gleichen Namen)
    [/baby/, /baby|brei|quetsch|kinder|hipp|bebivita|milupa|alete/],
    [/\bbrot gebac|backwaren|\bgebac/, /brot|gebac|semmel|weckerl|kipferl|brotle|brotchen|baguette|toast|zopf|brioche|strudel|croissant|kuchen|krapfen|stangerl|flesserl|gipfel|knodel|laugen|ciabatta|bagel|wrap|tortilla|fladen|pita|muffin|donut|schnecke|golatsche|plunder|reindling|striezel/],
    [/milchgetranke/, /milch|drink|actimel|kefir|shake|getrank|kakao|yakult|lassi|ayran|smoothie/],
    [/teigwaren|\bpasta\b|\bnudeln\b/, /nudel|pasta|spaghetti|penne|fusilli|fleckerl|lasagne|makkaroni|maccheroni|tagliatelle|teigwar|hornchen|spatzle|gnocchi|tortellini|ravioli|reis|couscous|bulgur|quinoa|polenta|beilage|knodel|suppeneinlage/],
    [/eiskaffee/, /eiskaffee|frappuccino|macchiato|latte|cold brew|kaffeegetrank|kaffeedrink/],
  ];

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

  // Wie viele Packungen braucht man, was kostet das?
  //   "1 kg Topfen", Packung 250 g        -> 4 Packungen
  //   "2x 500g Topfen", Packung 250 g     -> 4 Packungen (Anzahl × Menge)
  //   "1,5 kg Äpfel", Preis per kg        -> 1,5 × Kilopreis
  // Mengenaktionen ("ab 2 Stück", "1+1 gratis"): Wird die Mindestmenge nicht erreicht, gilt der Einzelpreis.
  // Kostet die Mindestmenge aber höchstens so viel wie die gebrauchte Menge einzeln, wird aufgerundet
  // ("1+1 gratis": 2 Stück kosten so viel wie 1) – mit Hinweis.
  function kosten(eintrag, a) {
    const anzahl = eintrag.anzahl || 1;
    let stueck = anzahl;
    if (eintrag.menge && a.menge && eintrag.einheit === a.einheit) {
      stueck = Math.max(1, Math.ceil((eintrag.menge * anzahl) / a.menge - 1e-9));
    } else if (eintrag.menge && a.pro_kg && eintrag.einheit === "g") {
      stueck = (eintrag.menge * anzahl) / 1000; // kg-Ware
    }
    const normal = a.normalpreis && a.normalpreis > a.preis ? a.normalpreis : null;
    let aktionGilt = !a.ab_menge || stueck >= a.ab_menge;
    let hinweis = null, aufgerundet = false;
    if (!aktionGilt && normal && !a.pro_kg) {
      const mitAktion = a.ab_menge * a.preis, einzeln = stueck * normal;
      if (mitAktion <= einzeln + 0.02) {
        hinweis = `${a.ab_menge} nehmen: ${mitAktion >= einzeln - 0.02 ? "kostet gleich viel wie" : "billiger als"} ${zahlText(stueck)} einzeln`;
        stueck = a.ab_menge;
        aktionGilt = aufgerundet = true;
      }
    }
    if (!aktionGilt) hinweis = normal ? `Aktion erst ab ${a.ab_menge} Stück` : `Aktion erst ab ${a.ab_menge} Stück, Einzelpreis unbekannt`;
    const einzel = aktionGilt ? a.preis : (normal || a.preis);
    return {
      stueck,
      einzel,                 // Preis pro Packung (bzw. pro kg), der tatsächlich gezahlt wird
      preis: einzel * stueck,
      ersparnis: normal && aktionGilt ? (normal - a.preis) * stueck : 0,
      aktionGilt,
      aufgerundet,            // auf die Aktionsmenge aufgerundet, weil das nicht mehr kostet
      hinweis,
    };
  }

  const zahlText = (x) => x.toLocaleString("de-AT", { maximumFractionDigits: 2 });

  // "4 × 0,99 €", "1,5 kg × 9,99 €/kg" – nur wenn mehr als eine Packung gebraucht wird (sonst null)
  function packungText(t) {
    const { stueck, einzel } = t.kosten;
    const euro = (x) => x.toLocaleString("de-AT", { style: "currency", currency: "EUR" });
    if (t.angebot.pro_kg) return stueck && stueck !== 1 ? `${zahlText(stueck)} kg × ${euro(einzel)}/kg` : null;
    if (stueck === 1) return null;
    return `${zahlText(stueck)} × ${euro(einzel)}`;
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

  // ---------- Normalpreise (ganzes Sortiment aus den Online-Shops, data/sortiment.js) ----------
  // Kompaktes Format aus python -m aktionen.sortiment -> Angebote im gleichen Aufbau wie die Aktionen
  function sortimentAuspacken(sortiment) {
    const aus = [];
    for (const [kette, k] of Object.entries(sortiment?.ketten ?? {})) {
      for (const [pid, name, preis, menge, einheit, kg, normal, kat] of k.produkte ?? []) {
        aus.push({
          id: `s:${kette}:${pid}`, kette, name, preis, menge, einheit, pro_kg: !!kg, normalpreis: normal,
          kategorie: kat != null ? k.kategorien?.[kat] ?? null : null,
          url: k.link ? k.link.replace("{}", encodeURIComponent(pid)) : null, dauerpreis: true, stand: k.stand,
        });
      }
    }
    return aus;
  }

  // r = Ergebnis von auswerten() (nur Aktionen), produkte = sortimentAuspacken(…)
  //   proEintrag:  pro Listeneintrag der günstigste gut passende Normalpreis je Geschäft (bestProKette)
  //   einGeschaeft: pro Geschäft mit Sortiment "alles dort kaufen" – Aktion, wenn billiger, sonst Normalpreis
  //   ohneAktion:  für Einträge ohne Aktion der günstigste Normalpreis überhaupt (oder null)
  // "Gut passend" = mindestens 80 % der besten Punktzahl über alle Geschäfte, damit z. B. "Milch" bei einem
  // Geschäft nicht auf "Milchreis" ausweicht, nur weil es dort keine Milch gefunden hat.
  // Welcher Sortiments-Treffer (alle schon gut passend) ist günstiger? Mit Mengenangabe: was man für die Menge zahlt.
  // Ohne: bei gleicher Einheit der Preis pro kg/l/Stück (sonst gewinnt die kleinste Packung), sonst der Packungspreis.
  // Die Punkte taugen hier nicht als Kriterium: Viele Treffer haben 1,0 ("Milch" ~ "Milch Milkimumm Schoko").
  function besserImSortiment(eintrag, t, u) {
    if (eintrag.menge) return effektiv(eintrag, t) < effektiv(eintrag, u);
    if (t.grundpreis && u.grundpreis && t.grundpreis.einheit === u.grundpreis.einheit) return t.grundpreis.wert < u.grundpreis.wert;
    return t.kosten.preis < u.kosten.preis;
  }

  function mitNormalpreisen(r, produkte, optionen = {}) {
    const aus = optionen.ausgeschlossen || new Set();
    const nutzbar = produkte.filter((a) => !aus.has(a.id));
    const ketten = [...new Set(nutzbar.map((a) => a.kette))];
    const proEintrag = r.eintraege.map((x) => {
      const treffer = finde(x.eintrag, nutzbar);
      const spitze = Math.max(treffer[0]?.punkte ?? 0, x.treffer[0]?.punkte ?? 0);
      const bestProKette = {};
      for (const t of treffer) {
        if (t.punkte < spitze * 0.8) continue;
        const k = t.angebot.kette;
        if (!bestProKette[k] || besserImSortiment(x.eintrag, t, bestProKette[k])) bestProKette[k] = t;
      }
      // Günstigster überhaupt (für Einträge ohne Aktion): hier zählt der Preis, die Passgenauigkeit ist schon ≥ 80 %
      const guenstigster = Object.values(bestProKette)
        .reduce((m, t) => (!m || effektiv(x.eintrag, t) < effektiv(x.eintrag, m) ? t : m), null);
      return { eintrag: x.eintrag, treffer, bestProKette, aktion: x.bestProKette, guenstigster };
    });
    const einGeschaeft = ketten.map((k) => {
      const z = { kette: k, preis: 0, aktion: 0, normal: 0, posten: [], fehlt: [] };
      for (const e of proEintrag) {
        const a = e.aktion[k], n = e.bestProKette[k];
        const wahl = a && (!n || a.kosten.preis <= n.kosten.preis) ? a : n;
        if (!wahl) { z.fehlt.push(e.eintrag); continue; }
        if (wahl === a) z.aktion++; else z.normal++;
        z.preis += wahl.kosten.preis;
        z.posten.push({ eintrag: e.eintrag, treffer: wahl });
      }
      return z;
    }).sort((x, y) => y.posten.length - x.posten.length || x.preis - y.preis);
    const ohneAktion = r.ohneAktion.map((e) => ({ eintrag: e, treffer: proEintrag.find((p) => p.eintrag === e)?.guenstigster ?? null }));
    return { proEintrag, einGeschaeft, ohneAktion };
  }

  const api = { norm, stamm, varianten, parseZeile, parseListe, wortTreffer, bewerte, grundpreis, kosten, packungText, effektiv, finde, auswerten,
    sortimentAuspacken, mitNormalpreisen, SCHWELLE, vorfilter: true }; // vorfilter: nur für Tests abschaltbar
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else global.Abgleich = api;
})(typeof window !== "undefined" ? window : globalThis);
