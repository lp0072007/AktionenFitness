// Einstellungen (⚙️ in der Kopfzeile): Kundenkarten und Vorlieben. Gilt auf allen Seiten, im Browser gespeichert.
//
//   Vorlieben.lesen()                 -> { karten: ["lidlplus", …], ernaehrung: "alles"|"vegetarisch"|"vegan",
//                                          nurBio: false, ohneEigenmarken: false }
//   Vorlieben.anwenden(angebote, v)   -> gefilterte Angebote; mit Karte zählt der Kartenpreis als Preis
//   Vorlieben.merkmale(angebot)       -> { vegetarisch, vegan, bio, eigenmarke } (true / false / null = unbekannt)
//
// Die Logik läuft auch in Node (Tests: tests/vorlieben.test.mjs), die Oberfläche nur im Browser.

(function (global) {
  "use strict";
  const SCHLUESSEL = "aktionenfitness.vorlieben.v1";
  const STANDARD = { karten: [], ernaehrung: "alles", nurBio: false, ohneEigenmarken: false };
  const ERNAEHRUNG = ["alles", "vegetarisch", "vegan"];

  // Kundenkarten: Welcher Zusatzpreis gehört zu welcher Karte? (zusatz_text aus dem Export)
  const KARTEN = {
    lidlplus: { name: "Lidl Plus", wo: "Lidl", ketten: ["lidl"], passt: (t) => /lidl\s*plus/i.test(t) },
    joe: { name: "jö Bonus Club", wo: "Billa, Penny", ketten: ["billa", "penny"], passt: (t) => /^j(ö|oe?)(\s|$)/i.test(t) }, // kein \b: "ö" zählt dort nicht als Buchstabe
    sparapp: { name: "SPAR-App", wo: "Spar-Gutscheine im Flugblatt", ketten: ["spar"], passt: (t) => /spar-?app/i.test(t) },
  };

  // ---------- Merkmale eines Produkts ----------
  // Kleinbuchstaben, Umlaute vereinfacht, Satzzeichen zu Leerzeichen (Bindestriche trennen: "Bio-Joghurt" -> "bio joghurt")
  function einfach(text) {
    return String(text || "").toLowerCase()
      .replace(/ä/g, "a").replace(/ö/g, "o").replace(/ü/g, "u").replace(/ß/g, "ss")
      .replace(/[^a-z0-9!*]+/g, " ").trim();
  }

  // Ausdrücklich fleischlos ("Veggie Burger", "vegane Bratwurst") – schlägt die Fleisch-Wörter
  const VEGGIE = /vegan|vegetar|veggie|pflanzlich|plant ?based|fleischlos|ohne fleisch/;
  const VEGAN = /vegan|pflanzlich|plant ?based/;
  // Fleisch und Fisch (auch als Teil eines Wortes: "Hühnerbrust", "Thunfischsalat")
  const FLEISCH = new RegExp([
    "fleisch(?!tomate)", "wurst", "wurstel", "schinken", "speck", "salami", "mortadella", "prosciutto", "pancetta", "chorizo",
    "kabanos", "cabanossi", "leberkas", "leberkase", "leberpastete", "\\bleber", "frankfurter", "debreziner", "krainer",
    "cevapcici", "kebap", "kebab", "gyros", "gulasch", "bolognese", "faschiert", "hackfleisch", "\\bhack\\b", "nugget",
    "schwein", "\\brind", "kalb", "\\blamm", "hirsch", "\\breh\\b", "\\bgans", "\\bente\\b", "\\benten", "truthahn",
    "puten", "\\bpute\\b", "huhn", "huhner", "hendl", "hahnchen", "geflugel", "chicken", "\\bbeef", "\\bpork", "bacon", "\\bham\\b",
    "fisch", "lachs", "forelle", "hering", "matjes", "makrele", "sardin", "sardell", "anchov", "kabeljau", "dorsch",
    "zander", "karpfen", "pangasius", "seelachs", "\\balaska", "garnele", "shrimp", "scampi", "calamar", "tintenfisch",
    "muschel", "krabbe", "surimi", "kaviar", "gabelbissen", "rollmops", "\\btuna\\b", "gelatine",
  ].join("|"));
  // Milch, Ei, Honig (nicht vegan). "Hafermilch", "Kokosjoghurt", "Erdnussbutter" sind pflanzlich.
  const PFLANZEN_PRAEFIX = "(?<!hafer|soja|mandel|kokos|kokosnuss|reis|dinkel|erbsen|cashew|erdnuss|nuss|kakao|shea|hasel)";
  const TIERISCH = new RegExp([
    `${PFLANZEN_PRAEFIX}milch`, `${PFLANZEN_PRAEFIX}joghurt`, `${PFLANZEN_PRAEFIX}jogurt`, `${PFLANZEN_PRAEFIX}butter(?!bohne)`,
    "kase", "topfen", "quark", "skyr", "\\brahm", "sauerrahm", "obers", "sahne", "kefir", "molke", "whey", "mozzarella",
    "gouda", "emmentaler", "edamer", "parmesan", "\\bgrana\\b", "\\bfeta\\b", "cottage", "mascarpone", "ricotta", "burrata",
    "camembert", "\\bbrie\\b", "halloumi", "creme fraiche", "mayonnaise", "\\bmayo\\b", "\\blatte\\b", "honig",
    "\\bei\\b", "eier", "freilandei", "eiklar", "eigelb",
  ].join("|"));
  const KATEGORIE_FLEISCH = /fleisch|wurst|fisch|geflugel|meeresfrucht/;
  const KATEGORIE_TIERISCH = /milchprodukt|molkerei|\bkase|\beier\b|joghurt|\bmilch\b|butter/;
  const KATEGORIE_PFLANZLICH = /ersatz|alternativ|pflanzlich|vegan|vegetar/;
  const BIO = /\bbio|ja! ?naturlich|natur ?\*? ?pur|zuruck zum ursprung|echt b!o|naturlich fur uns|\bdmbio|\bnaturland/;

  // Eigenmarken der Händler (Anfang des Namens). Nicht vollständig – bei Bedarf ergänzen.
  const EIGENMARKEN = {
    spar: /^(s ?budget|spar|despar|interspar)\b/,
    billa: /^(clever|billa|ja! ?naturlich|vegavita|da komm ich her|simply good)\b/,
    penny: /^(penny|echt b!o|ich bin osterreich)\b/,
    lidl: /^(milbona|pilos|chef select|combino|lidl|vemondo|solevita|freeway|crownfield|alpenfest|kania|vitasia|baresa|deluxe|favorina|bellarom|tastino|snack day|maribel|golden seafood|nautica|dulano|sol ?mar|alesto|gelatelli|my best veggie|harvest basket|pikok|linessa|cien|w5|perlenbacher|mcennedy|sondey|fin carre)\b/,
    hofer: /^(milsani|zuruck zum ursprung|lyttos|golden bridge|cucina nobile|back family|choceur|rio d ?oro|river|hofer|knusperone|moser roth|wonnemeyer|just veg|happy harvest|asia green garden|almare|natur aktiv|bramwald|cantinetta|the deli|tandil)\b/,
    mpreis: /^(mpreis|m(?! m s\b)|m bio|jeden tag|therese molk)\b/, // "M&M'S" -> "m m s" ist keine Eigenmarke
    dm: /^(dmbio|dm bio|dm)\b/,
  };

  const _merkmale = new WeakMap(); // Angebote werden oft neu gefiltert – Ergebnis pro Objekt merken
  function merkmale(a) {
    let m = _merkmale.get(a);
    if (!m) { m = merkmaleBerechnen(a); _merkmale.set(a, m); }
    return m;
  }

  function merkmaleBerechnen(a) {
    const name = einfach(a.name);
    const kat = einfach([a.kategorie, a.gruppe].filter(Boolean).join(" "));
    const tags = new Set(a.merkmale || []);
    const text = `${name} ${kat}`;

    let vegetarisch = null, vegan = null;
    if (tags.has("vegan")) vegan = vegetarisch = true;
    else if (tags.has("vegetarisch")) { vegetarisch = true; vegan = false; } // Händler kennzeichnet: vegetarisch, nicht vegan
    else if (VEGGIE.test(name)) { vegetarisch = true; vegan = VEGAN.test(name) ? true : (TIERISCH.test(name) ? false : null); }
    else {
      const pflanzKat = KATEGORIE_PFLANZLICH.test(kat);
      if (FLEISCH.test(text) || (!pflanzKat && KATEGORIE_FLEISCH.test(kat))) vegetarisch = vegan = false;
      else if (TIERISCH.test(text) || (!pflanzKat && KATEGORIE_TIERISCH.test(kat))) vegan = false;
    }
    const marke = EIGENMARKEN[a.kette];
    return {
      vegetarisch,
      vegan,
      bio: tags.has("bio") || BIO.test(name),
      eigenmarke: marke ? marke.test(name) : false,
    };
  }

  // Für einen Zusatzpreis die passende Karte (Schlüssel aus KARTEN) – oder null (z. B. Spar-Aktionstag Fr/Sa)
  function karteFuer(a) {
    if (!a.zusatzpreis || !a.zusatz_text) return null;
    for (const [k, karte] of Object.entries(KARTEN)) {
      if (karte.ketten.includes(a.kette) && karte.passt(a.zusatz_text)) return k;
    }
    return null;
  }

  // Beschriftung eines Zusatzpreises: "💳 mit jö", "💳 mit Lidl Plus", "Aktionstag"
  function zusatzName(a) {
    const k = karteFuer(a);
    if (k) return `💳 mit ${k === "joe" ? "jö" : KARTEN[k].name}`;
    return a.zusatz_text || "Aktionstag";
  }

  function passt(a, v) {
    if (v.ernaehrung === "alles" && !v.nurBio && !v.ohneEigenmarken) return true;
    const m = merkmale(a);
    if (v.ernaehrung === "vegetarisch" && m.vegetarisch === false) return false;
    if (v.ernaehrung === "vegan" && m.vegan === false) return false;
    if (v.nurBio && !m.bio) return false;
    if (v.ohneEigenmarken && m.eigenmarke) return false;
    return true;
  }

  // Mit Karte: Kartenpreis wird zum Preis, der Preis ohne Karte zum Vergleichspreis.
  function mitKarte(a, v) {
    const k = karteFuer(a);
    if (!k || !v.karten.includes(k) || !(a.zusatzpreis < a.preis)) return a;
    const neu = { ...a, preis: a.zusatzpreis, karte: KARTEN[k].name, ohne_karte: a.preis };
    if (!(a.normalpreis > a.preis)) neu.normalpreis = a.preis;
    if (a.protein_pro_euro_zusatz) neu.protein_pro_euro = a.protein_pro_euro_zusatz;
    delete neu.zusatzpreis;
    delete neu.zusatz_text;
    // Original für "+ Liste" (gespeichert wird der Händlerstand, nicht der umgerechnete) – nicht aufzählbar
    Object.defineProperty(neu, "roh", { value: a });
    return neu;
  }

  function anwenden(angebote, v = lesen()) {
    const ergebnis = [];
    for (const a of angebote) if (passt(a, v)) ergebnis.push(mitKarte(a, v));
    return ergebnis;
  }

  // ---------- Speichern ----------
  function bereinigen(roh) {
    const v = { ...STANDARD, ...(roh && typeof roh === "object" ? roh : {}) };
    v.karten = Array.isArray(v.karten) ? v.karten.filter((k) => KARTEN[k]) : [];
    if (!ERNAEHRUNG.includes(v.ernaehrung)) v.ernaehrung = "alles";
    v.nurBio = !!v.nurBio;
    v.ohneEigenmarken = !!v.ohneEigenmarken;
    return v;
  }
  function lesen() {
    try { return bereinigen(JSON.parse(global.localStorage?.getItem(SCHLUESSEL))); } catch { return bereinigen(null); }
  }
  const hoerer = new Set();
  function setzen(v) {
    const sauber = bereinigen(v);
    try { global.localStorage?.setItem(SCHLUESSEL, JSON.stringify(sauber)); } catch { /* privater Modus */ }
    for (const f of hoerer) f(sauber);
  }

  // Kurzbeschreibung der aktiven Einstellungen, z. B. "🌱 vegan · 💳 Lidl Plus"
  function zusammenfassung(v = lesen()) {
    const teile = [];
    if (v.ernaehrung === "vegan") teile.push("🌱 vegan");
    if (v.ernaehrung === "vegetarisch") teile.push("🥕 vegetarisch");
    if (v.nurBio) teile.push("🍃 nur Bio");
    if (v.ohneEigenmarken) teile.push("ohne Eigenmarken");
    for (const k of v.karten) teile.push(`💳 ${KARTEN[k].name}`);
    return teile.join(" · ");
  }
  const filtertAktiv = (v = lesen()) => v.ernaehrung !== "alles" || v.nurBio || v.ohneEigenmarken;

  // ---------- Oberfläche (nur im Browser) ----------
  function el(tag, attrs = {}, ...kinder) {
    const e = document.createElement(tag);
    for (const [k, w] of Object.entries(attrs)) {
      if (k === "class") e.className = w;
      else if (k in e && typeof w !== "string") e[k] = w;
      else e.setAttribute(k, w);
    }
    e.append(...kinder);
    return e;
  }

  function dialogBauen() {
    const v = lesen();
    const option = (typ, name, wert, an, titel, info) => {
      const input = el("input", { type: typ, name, value: wert, checked: an });
      const text = el("span", { class: "einst__text" }, el("b", {}, titel));
      if (info) text.append(el("small", {}, info));
      return el("label", { class: "sb-option einst__option" }, input, text);
    };
    const form = el("form", { class: "merk-dialog__inhalt einst", method: "dialog" },
      el("fieldset", {},
        el("legend", {}, "💳 Kundenkarten"),
        el("p", { class: "ek-hinweis" }, "Welche Karten hast du? Dann zählt der Kartenpreis – bei den Angeboten, " +
          "beim Sortieren und in der Einkaufsliste. Ohne Karte steht er nur als Hinweis dabei."),
        ...Object.entries(KARTEN).map(([k, karte]) => option("checkbox", "karte", k, v.karten.includes(k), karte.name, karte.wo))),
      el("fieldset", {},
        el("legend", {}, "🥗 Ernährung"),
        option("radio", "ernaehrung", "alles", v.ernaehrung === "alles", "Alles"),
        option("radio", "ernaehrung", "vegetarisch", v.ernaehrung === "vegetarisch", "Vegetarisch", "ohne Fleisch und Fisch"),
        option("radio", "ernaehrung", "vegan", v.ernaehrung === "vegan", "Vegan", "auch ohne Milch, Ei und Honig"),
        el("p", { class: "ek-hinweis" }, "Erkannt über die Kennzeichnung des Händlers (Billa) und den Produktnamen. " +
          "Ohne Gewähr – im Zweifel aufs Etikett schauen.")),
      el("fieldset", {},
        el("legend", {}, "🛍️ Vorlieben"),
        option("checkbox", "nurBio", "ja", v.nurBio, "Nur Bio"),
        option("checkbox", "ohneEigenmarken", "ja", v.ohneEigenmarken, "Keine Eigenmarken", "z. B. S-BUDGET, Clever, Milsani, Milbona"),
        el("p", { class: "ek-hinweis" }, "Eine bestimmte Marke? Einfach mit auf die Liste schreiben, z. B. „NÖM Skyr“.")),
      el("button", { class: "knopf", type: "submit" }, "Fertig"));

    form.addEventListener("change", () => {
      const d = new FormData(form);
      setzen({
        karten: d.getAll("karte"),
        ernaehrung: d.get("ernaehrung") || "alles",
        nurBio: d.has("nurBio"),
        ohneEigenmarken: d.has("ohneEigenmarken"),
      });
    });

    const dialog = el("dialog", { class: "merk-dialog einst-dialog", "aria-labelledby": "einstTitel" },
      el("div", { class: "schublade__kopf" },
        el("h2", { id: "einstTitel" }, "⚙️ Einstellungen"),
        el("form", { method: "dialog" }, el("button", { class: "x-knopf", "aria-label": "Schließen" }, "✕"))),
      form);
    dialog.addEventListener("click", (e) => { if (e.target === dialog) dialog.close(); }); // Klick daneben schließt
    return dialog;
  }

  function knopfAktualisieren(knopf, v = lesen()) {
    const info = zusammenfassung(v);
    knopf.title = info ? `Einstellungen: ${info}` : "Einstellungen: Kundenkarten, vegan/vegetarisch, Bio";
    knopf.setAttribute("aria-label", knopf.title);
    knopf.classList.toggle("einst-knopf--aktiv", !!info);
  }

  function oberflaecheEinrichten() {
    const kopf = document.querySelector(".kopf__inhalt");
    if (!kopf) return;
    const knopf = el("button", { type: "button", class: "thema-knopf einst-knopf" }, "⚙️");
    knopfAktualisieren(knopf);
    let dialog = null;
    knopf.addEventListener("click", () => {
      dialog?.remove();
      dialog = dialogBauen(); // jedes Mal frisch, falls in einem anderen Tab geändert
      document.body.append(dialog);
      dialog.showModal();
    });
    kopf.insertBefore(knopf, kopf.lastElementChild);
    hoerer.add((v) => knopfAktualisieren(knopf, v));
  }

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", oberflaecheEinrichten);
    else oberflaecheEinrichten();
    // Andere Tabs/Seiten übernehmen die Änderung sofort
    global.addEventListener?.("storage", (e) => {
      if (e.key !== SCHLUESSEL) return;
      const v = lesen();
      for (const f of hoerer) f(v);
    });
  }

  const api = {
    KARTEN, STANDARD, merkmale, karteFuer, zusatzName, passt, mitKarte, anwenden, lesen, setzen, zusammenfassung, filtertAktiv,
    beiAenderung(f) { hoerer.add(f); },
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else global.Vorlieben = api;
})(typeof window !== "undefined" ? window : globalThis);
