// Tests für die Abgleich-Logik. Ausführen im Ordner web:  node --test
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const A = createRequire(import.meta.url)("../abgleich.js");

// Echte Produktnamen aus den Aktionen der KW 47 (Spar, Lidl, Hofer, Penny, Billa)
const angebot = (name, preis, extra = {}) => ({ id: name, kette: extra.kette || "billa", name, preis, ...extra });
const ANGEBOTE = [
  angebot("Schärdinger Formil Haltbare Vollmilch", 0.89, { kette: "penny", menge: 1000, einheit: "ml", ab_menge: 12, normalpreis: 1.29 }),
  angebot("BIO Kokosnussmilch", 1.59, { kette: "hofer", menge: 400, einheit: "ml" }),
  angebot("Müller Milchschnitte", 1.79),
  angebot("nöm PRO Banane Proteindrink", 1.14),
  angebot("Hauswirth Schokobananen", 2.49, { kette: "penny" }),
  angebot("Eskimo Cremissimo Banane, Stracciatella & Schokolade", 3.24, { kategorie: "Tiefkühl > Eis > Eiscreme" }),
  angebot("S-BUDGET Hendlfilet aus Österreich", 7.59, { kette: "spar", menge: 700, einheit: "g" }),
  angebot("Federike Hühner-Innenfilet", 6.99, { kette: "penny", menge: 1000, einheit: "g", kategorie: "Kühlwaren > Fleisch" }),
  angebot("WUNDERLINGE Erdäpfel", 2.07, { kette: "penny", menge: 2500, einheit: "g" }),
  angebot("Frosta Gemüse Pfanne Kartoffel Champignon", 3.49, { menge: 480, einheit: "g" }),
  angebot("Meisterfrost Topfen Heidelbeerstrudel", 2.99),
  angebot("Clever Bourbon Vanille Eis", 2.84, { kategorie: "Tiefkühl > Eis > Eiscreme" }),
  angebot("Milbona Butter", 1.19, { kette: "lidl", menge: 250, einheit: "g", gueltig_von: "2026-11-23", gueltig_bis: "2026-11-25" }),
  angebot("Tante Fanny Butter- Croissant- & Plunderteig", 1.59, { kette: "penny" }),
  angebot("Delikatessa Teigwaren", 0.94, { kette: "penny", menge: 1000, einheit: "g", normalpreis: 1.28 }),
  angebot("Alpro Skyr Natur Ungesüßt", 1.32, { menge: 400, einheit: "g", ab_menge: 3, normalpreis: 1.99 }),
];

test("Liste parsen: Aufzählungszeichen, Anzahl, Menge", () => {
  const l = A.parseListe("- 2x Milch\n• Haferflocken 1kg\n* 500g Hendlfilet\n3 Bananen\n1. Skyr x3\n\n- Bio Eier 10 Stk");
  assert.deepEqual(l.map((e) => [e.begriff, e.anzahl, e.menge, e.einheit]), [
    ["milch", 2, null, null],
    ["haferflocken", 1, 1000, "g"],
    ["hendlfilet", 1, 500, "g"],
    ["bananen", 3, null, null],
    ["skyr", 3, null, null],
    ["bio eier", 10, null, null],
  ]);
  assert.equal(l[5].bio, true);
});

test("Komposita: Kopf hinten zählt, Bestimmungswort nicht", () => {
  assert.equal(A.wortTreffer("milch", "vollmilch"), 0.9);
  assert.ok(A.wortTreffer("milch", "milchschnitte") < A.SCHWELLE);
  assert.ok(A.wortTreffer("milch", "kokosnussmilch") < A.SCHWELLE); // Ersatzprodukt
});

const namen = (q, tag) => A.finde(A.parseZeile(q), ANGEBOTE, tag).map((t) => t.angebot.name);

test("Milch findet Vollmilch, nicht Milchschnitte oder Kokosmilch", () => {
  assert.deepEqual(namen("Milch"), ["Schärdinger Formil Haltbare Vollmilch"]);
});

test("Verarbeitete Produkte werden abgewertet, außer man sucht danach", () => {
  assert.deepEqual(namen("Bananen"), []);
  assert.deepEqual(namen("Topfen"), []);
  assert.deepEqual(namen("Kartoffeln"), ["WUNDERLINGE Erdäpfel"]);           // Synonym + ohne Pfanne
  assert.deepEqual(namen("Butter"), ["Milbona Butter"]);
  assert.ok(namen("Eis").includes("Clever Bourbon Vanille Eis"));
});

test("Synonyme auch kombiniert: Hühnerbrust -> Hendlfilet / Hühner-Innenfilet", () => {
  const n = namen("Hühnerbrust");
  assert.ok(n.includes("S-BUDGET Hendlfilet aus Österreich"));
  assert.ok(n.includes("Federike Hühner-Innenfilet"));
  assert.deepEqual(namen("Nudeln"), ["Delikatessa Teigwaren"]);
});

test("Gültigkeit am Einkaufstag", () => {
  assert.deepEqual(namen("Butter", "2026-11-20"), []);                     // Lidl-Butter erst ab 23.11.
  assert.deepEqual(namen("Butter", "2026-11-24"), ["Milbona Butter"]);
});

test("Kosten: Packungen aus Menge, Mengenaktion erst ab x Stück", () => {
  const skyr = ANGEBOTE.find((a) => a.name.startsWith("Alpro")); // 1,32 € ab 3, einzeln 1,99 €
  const eins = A.kosten(A.parseZeile("Skyr"), skyr);
  assert.equal(eins.aktionGilt, false);                 // 3 × 1,32 = 3,96 € > 1 × 1,99 € -> nicht aufrunden
  assert.equal(eins.preis, 1.99);
  assert.match(eins.hinweis, /erst ab 3 Stück/);
  const drei = A.kosten(A.parseZeile("3x Skyr"), skyr);
  assert.ok(Math.abs(drei.preis - 3 * 1.32) < 1e-9 && Math.abs(drei.ersparnis - 3 * 0.67) < 1e-9);
  const hendl = ANGEBOTE.find((a) => a.name.startsWith("S-BUDGET Hendl"));
  assert.equal(A.kosten(A.parseZeile("1kg Hendlfilet"), hendl).stueck, 2);  // 700-g-Packungen
});

test("Kosten: aufrunden, wenn die Aktionsmenge nicht mehr kostet", () => {
  const skyr = ANGEBOTE.find((a) => a.name.startsWith("Alpro"));
  // 2 einzeln = 3,98 €, 3 mit Aktion = 3,96 € -> 3 nehmen
  const zwei = A.kosten(A.parseZeile("2x Skyr"), skyr);
  assert.deepEqual([zwei.stueck, zwei.aktionGilt, zwei.aufgerundet], [3, true, true]);
  assert.ok(Math.abs(zwei.preis - 3.96) < 1e-9);
  assert.equal(zwei.hinweis, "3 nehmen: kostet gleich viel wie 2 einzeln");
  // "1+1 GRATIS" (Spar NÖ KW 47, S. 4): 1 Packung 14,99 €, ab 2 je 7,49 € -> 2 kosten so viel wie 1
  const kaffee = { id: "k", kette: "spar", name: "Dallmayr Prodomo", preis: 7.49, normalpreis: 14.99, ab_menge: 2,
    menge: 500, einheit: "g", aktion: ["1+1 GRATIS"] };
  const k = A.kosten(A.parseZeile("Kaffee"), kaffee);
  assert.deepEqual([k.stueck, k.aufgerundet], [2, true]);
  assert.ok(Math.abs(k.preis - 14.98) < 1e-9);
  assert.equal(k.hinweis, "2 nehmen: kostet gleich viel wie 1 einzeln");
  // Ohne Einzelpreis kann nichts verglichen werden
  const unbekannt = A.kosten(A.parseZeile("Kaffee"), { ...kaffee, normalpreis: undefined });
  assert.deepEqual([unbekannt.aktionGilt, unbekannt.aufgerundet], [false, false]);
  assert.match(unbekannt.hinweis, /Einzelpreis unbekannt/);
});

// Gleiche Formatierung wie auf der Website (de-AT: "€ 0,99")
const eur = (x) => x.toLocaleString("de-AT", { style: "currency", currency: "EUR" });

test("Kosten: Anzahl × Menge und Packungstext", () => {
  const topfen = { id: "t", kette: "hofer", name: "Magertopfen", preis: 0.99, menge: 250, einheit: "g" };
  const t = { angebot: topfen, kosten: A.kosten(A.parseZeile("2x 500g Topfen"), topfen) };
  assert.equal(t.kosten.stueck, 4);                     // vorher: 2 (Anzahl ignoriert)
  assert.equal(A.packungText(t), `4 × ${eur(0.99)}`);
  const kg = { angebot: topfen, kosten: A.kosten(A.parseZeile("1 kg Topfen"), topfen) };
  assert.equal(kg.kosten.stueck, 4);
  const eine = { angebot: topfen, kosten: A.kosten(A.parseZeile("Topfen"), topfen) };
  assert.equal(A.packungText(eine), null);
  const aepfel = { id: "a", kette: "billa", name: "Äpfel", preis: 1.99, pro_kg: true };
  const lose = { angebot: aepfel, kosten: A.kosten(A.parseZeile("1,5 kg Äpfel"), aepfel) };
  assert.equal(A.packungText(lose), `1,5 kg × ${eur(1.99)}/kg`);
});

test("Auswertung: Rangliste und günstigste Aufteilung", () => {
  const liste = A.parseListe("- Milch\n- Hühnerbrust\n- Nudeln\n- Klopapier");
  const r = A.auswerten(liste, ANGEBOTE);
  assert.equal(r.rangliste[0].kette, "penny");                              // Milch, Hühnerfilet, Teigwaren
  assert.equal(r.rangliste[0].anzahl, 3);
  assert.deepEqual(r.ohneAktion.map((e) => e.begriff), ["klopapier"]);
  // Hühnerbrust: Penny 6,99 €/kg ist günstiger als Spar 10,84 €/kg
  assert.ok(r.aufteilung.penny.some((x) => x.eintrag.begriff === "huhnerbrust"));
  // ausgeschlossene Treffer (vom Nutzer abgewählt) zählen nicht
  const ohne = A.auswerten(liste, ANGEBOTE, { ausgeschlossen: new Set(["Federike Hühner-Innenfilet"]) });
  assert.ok(ohne.aufteilung.spar.some((x) => x.eintrag.begriff === "huhnerbrust"));
});

test("Aufteilung nach tatsächlich gezahltem Preis", () => {
  // 1 kg Hühnerbrust: Penny 1 kg 6,99 € schlägt Spar 2 × 700 g (15,18 €), obwohl der Name etwas schlechter passt
  const r = A.auswerten(A.parseListe("- 1kg Hühnerbrust"), ANGEBOTE);
  assert.equal(Object.keys(r.aufteilung)[0], "penny");
  // Skyr einzeln: Aktion (ab 3) gilt nicht -> es zählt der Normalpreis 1,99 €
  const skyr = ANGEBOTE.find((a) => a.name.startsWith("Alpro"));
  const t = { angebot: skyr, kosten: A.kosten(A.parseZeile("Skyr"), skyr) };
  assert.equal(A.effektiv(A.parseZeile("Skyr"), t), 1.99 / 400 * 1000);
});

test("Stichpunkte: Kommas, Klammern, 10er, Überschriften, Kästchen", () => {
  const l = A.parseListe("Kühlregal:\n- [ ] Skyr, Magertopfen\n• Eier (10er)\n- Milch 1,5 l\n# Kommentar\n☐ ½ kg Hendlfilet\n- Joghurt (griechisch, 2 Stk)");
  assert.deepEqual(l.map((e) => e.begriff), ["skyr", "magertopfen", "eier", "milch", "hendlfilet", "joghurt"]);
  assert.equal(l[2].menge, 10); assert.equal(l[2].einheit, "stk");
  assert.equal(l[3].menge, 1500); assert.equal(l[3].einheit, "ml");
  assert.equal(l[4].menge, 500);
  assert.equal(l[5].anzahl, 2);
});

test("Eigenschaften sind optional, Modifikator-Komposita, Hüttenkäse = Cottage", () => {
  const ang = [
    { id: "1", kette: "spar", name: "Schärdinger Mozzarella Minis", preis: 1 },
    { id: "2", kette: "lidl", name: "Alpengut Speisetopfen", preis: 1 },
    { id: "3", kette: "penny", name: "Nöm Cottage Cheese", preis: 1 },
    { id: "4", kette: "billa", name: "11er Frischkäse Taschen", preis: 3 },
    { id: "5", kette: "billa", name: "Ölz Weißbrot", preis: 2 },
  ];
  const ids = (q) => A.finde(A.parseZeile(q), ang).map((t) => t.angebot.id);
  assert.deepEqual(ids("Mozzarella light"), ["1"]);
  assert.deepEqual(ids("Magertopfen"), ["2"]);
  assert.deepEqual(ids("Hüttenkäse"), ["3"]);
  assert.deepEqual(ids("Frischkäse"), []);
  assert.deepEqual(ids("Vollkornbrot"), []);
});

test("Milch findet Milch, nicht Käse mit Milch im Namen", () => {
  const ang = [
    { id: "1", kette: "penny", name: "Salzburg Milch Almkönig Scheiben", preis: 6.69, kategorie: "Kühlwaren > Käse, Aufstriche & Salate" },
    { id: "2", kette: "spar", name: "SalzburgMilch Premium Bergbauern H-Milch 3,5% Fett", preis: 0.89 },
    { id: "3", kette: "penny", name: "Österreichische Vollmilch aus Deiner Region", preis: 1.19 },
    { id: "4", kette: "billa", name: "BILLA Heumilch Gouda", preis: 1.99 },
    { id: "5", kette: "billa", name: "Schärdinger Topfen Creme", preis: 1.0 },
  ];
  const ids = (q) => A.finde(A.parseZeile(q), ang).map((t) => t.angebot.id).sort();
  assert.deepEqual(ids("Milch"), ["2", "3"]);
  assert.deepEqual(ids("Gouda"), ["4"]);
  assert.deepEqual(ids("Topfen Creme"), ["5"]);
});

test("Fest gewähltes Angebot (+ Liste) wird immer genommen", () => {
  const ang = [
    { id: "a", kette: "spar", name: "Vollmilch", preis: 0.99, menge: 1000, einheit: "ml" },
    { id: "b", kette: "lidl", name: "Vollmilch", preis: 1.49, menge: 1000, einheit: "ml" },
  ];
  const e = { ...A.parseZeile("Vollmilch"), fest: ang[1], anzahl: 2 };
  const r = A.auswerten([e], ang);
  assert.deepEqual(Object.keys(r.aufteilung), ["lidl"]);
  assert.equal(r.aufteilung.lidl[0].treffer.kosten.preis, 2.98);
});

test("Vollmilch, H-Milch, Bergbauernmilch und Milch gehören zusammen", () => {
  const ang = [
    { id: "1", kette: "spar", name: "SalzburgMilch Premium Bergbauern H-Milch 3,5% Fett", preis: 0.89 },
    { id: "2", kette: "penny", name: "Schärdinger Formil Haltbare Vollmilch", preis: 0.89 },
    { id: "3", kette: "penny", name: "Schärdinger Bergbauernmilch", preis: 1.29 },
    { id: "4", kette: "penny", name: "Salzburg Milch Premium Käse-Selektion", preis: 3 },
    { id: "5", kette: "penny", name: "Maresi Kaffeemilch", preis: 1.5 },
    { id: "6", kette: "lidl", name: "Kokosmilch", preis: 1.5 },
  ];
  const ids = (q) => A.finde(A.parseZeile(q), ang).map((t) => t.angebot.id).sort();
  assert.deepEqual(ids("Milch"), ["1", "2", "3"]);
  assert.deepEqual(ids("Vollmilch"), ["1", "2", "3"]);
  assert.deepEqual(ids("Frischmilch"), ["1", "2", "3"]);
});

test("Mengen in allen Schreibweisen", () => {
  const mengen = (s) => { const e = A.parseZeile(s); return [e.begriff, e.anzahl, e.menge, e.einheit]; };
  // Gewicht: Groß/Klein, mit/ohne Leerzeichen, ausgeschrieben, Punkt dahinter, österreichisch (dag)
  for (const s of ["1KG TOPFEN", "1kg Topfen", "1 Kg. Topfen", "1000g Topfen", "1000 Gramm Topfen", "1Kilogramm topfen",
    "1 KILOGRAMM Topfen", "1 kilo topfen", "1 kilogr Topfen", "1,0 kg Topfen", "Topfen 1kg", "Topfen (1kg)", "100 dag Topfen",
    "2 Pfund Topfen"]) {
    assert.deepEqual(mengen(s), ["topfen", 1, 1000, "g"], s);
  }
  assert.deepEqual(mengen("1.5kg Quark"), ["quark", 1, 1500, "g"]);   // "1." ist hier keine Aufzählung
  assert.deepEqual(mengen("1,5 Kilogramm Quark"), ["quark", 1, 1500, "g"]);
  assert.deepEqual(mengen("250 gr. Quark"), ["quark", 1, 250, "g"]);
  assert.deepEqual(mengen("½kg Topfen"), ["topfen", 1, 500, "g"]);
  assert.deepEqual(mengen("1. Topfen"), ["topfen", 1, null, null]);   // Aufzählung
  // Volumen
  for (const s of ["1 Liter Milch", "1L Milch", "1 ltr milch", "1 Litre Milch", "1000ML Milch", "10 dl Milch", "100cl Milch"]) {
    assert.deepEqual(mengen(s), ["milch", 1, 1000, "ml"], s);
  }
  // Gebinde zählen als Stück, das Wort gehört nicht zum Suchbegriff
  assert.deepEqual(mengen("2 Becher Topfen"), ["topfen", 2, null, null]);
  assert.deepEqual(mengen("2 Gläser Gurken"), ["gurken", 2, null, null]);
  assert.deepEqual(mengen("1 Sack Kartoffeln"), ["kartoffeln", 1, null, null]);
  assert.deepEqual(mengen("2 Kopf Salat"), ["salat", 2, null, null]);
  // ...aber nur als eigenes Wort
  assert.deepEqual(mengen("Kopfsalat"), ["kopfsalat", 1, null, null]);
  assert.deepEqual(mengen("2 Gurken"), ["gurken", 2, null, null]);

  // Topfen und Quark finden dasselbe, egal wie geschrieben
  const topfen = { id: "t", kette: "hofer", name: "Milsani Magertopfen", preis: 0.99, menge: 250, einheit: "g" };
  for (const s of ["1KG TOPFEN", "1 Kilogramm Quark", "1000g quark", "Magerquark 1kg", "1 kg Magertopfen"]) {
    const e = A.parseZeile(s);
    assert.ok(A.bewerte(e, topfen) >= A.SCHWELLE, s);
    assert.equal(A.kosten(e, topfen).stueck, 4, s);
  }
});

test("MPreis-Namen und -Kategorien: keine Fehltreffer, Gesuchtes wird gefunden", () => {
  // Echte Produkte aus den MPreis-Aktionen (24.11.2026)
  const mp = (name, kategorie) => ({ id: name, kette: "mpreis", name, preis: 1, kategorie });
  const P = [
    mp("Bebivita Beutel Dinkel Himbeer Apfel Banane", "Lebensmittel > Grundnahrung > Babynahrung"),
    mp("Danone Actimel Kids Erdbeere-Banane", "Lebensmittel > Milch & Eier > Milch > Milchgetränke"),
    mp("Ölz Milch Brötle Alpen-Frischmilch Schoko", "Lebensmittel > Brot & Gebäck > Zopf, Brioche & Strudel"),
    mp("Iglo Blattspinat mit Schafskäse", "Lebensmittel > Tiefkühl > Gemüse & Kräuter"),
    mp("Starbucks Frappuccino Coffee Eiskaffee", "Getränke > Kaffee, Tee & Kakao > Kaffee > Eiskaffee"),
    mp("Melitta Kaffee Auslese Klassisch", "Getränke > Kaffee, Tee & Kakao > Kaffee > Bohnenkaffee"),
    mp("Pan Südtiroler Topfenstrudel", "Lebensmittel > Tiefkühl > Mehlspeisen  & Teige"),
    mp("Jasmin Reis", "Lebensmittel > Grundnahrung > Reis"),
    mp("Eskimo Cremissimo Vanille Eis", "Lebensmittel > Tiefkühl > Eis > Bechereis"),
    mp("Dr. Oetker Pizza Ristorante Salame", "Lebensmittel > Tiefkühl > Pizza"),
    mp("Ferrero Kinder Riegel 18er-Packung", "Lebensmittel > Süßes & Salziges > Schokolade > Schokoriegel"),
    mp("Tirol Milch Heumilch Bergkäse 45%", "Lebensmittel > Milch & Eier > Käse"),
    mp("Schärdinger Formil haltbare Milch 3,5%", "Lebensmittel > Milch & Eier > Milch"),
    mp("Bananen", "Lebensmittel > Obst"),
    // aus dem Vorher-Nachher-Vergleich mit allen Ketten
    { id: "ps", kette: "penny", name: "Best Moments Pasta Sauce", preis: 1, kategorie: "Grundnahrungsmittel > Saucen & Dressings" },
    { id: "pf", kette: "billa", name: "Kotányi Pfeffer Mühle Weiß", preis: 1 },
    { id: "tr", kette: "billa", name: "Trauben weiß kernlos", preis: 1 },
    { id: "lk", kette: "penny", name: "Weiss Lebkuchen Hexenhaus", preis: 1 },
    { id: "we", kette: "mpreis", name: "Schöller Wassereis Peach", preis: 1, kategorie: "Lebensmittel > Tiefkühl > Eis > Stieleis" },
    { id: "nu", kette: "penny", name: "Barilla Spaghetti", preis: 1 },
  ];
  const namen = (s) => A.finde(A.parseZeile(s), P, null).map((t) => t.angebot.name);
  const hat = (s, teil) => namen(s).some((n) => n.includes(teil));
  // nicht finden
  assert.ok(!hat("Bananen", "Bebivita"), "Babybrei ist keine Banane");
  assert.ok(!hat("Bananen", "Actimel"), "Actimel ist keine Banane");
  assert.ok(!hat("Milch", "Brötle"), "Milch-Brötle ist keine Milch");
  assert.ok(!hat("Käse", "Blattspinat"), "Spinat mit Käse ist kein Käse");
  assert.ok(!hat("Kaffee", "Eiskaffee"), "Eiskaffee ist kein Kaffee");
  assert.ok(!hat("Eis", "Reis"), "Reis ist kein Eis");
  assert.ok(!hat("Proteinriegel", "Kinder Riegel"));
  assert.ok(!hat("Topfen", "Topfenstrudel"));
  // finden
  assert.ok(hat("Bananen", "Bananen"));
  assert.ok(hat("Milch", "Formil"));
  assert.ok(hat("Käse", "Bergkäse"));
  assert.ok(hat("Kaffee", "Melitta"));
  assert.ok(hat("Eiskaffee", "Starbucks"));
  assert.ok(hat("Spinat", "Blattspinat"));
  assert.ok(hat("Topfenstrudel", "Topfenstrudel"), "ausdrücklich gesucht -> trotz Mehlspeisen-Kategorie");
  assert.ok(hat("Reis", "Jasmin"));
  assert.ok(hat("Eis", "Cremissimo"));
  assert.ok(hat("Tiefkühlpizza", "Ristorante"));
  assert.ok(hat("Pizza", "Ristorante"));
  assert.ok(!hat("Nudeln", "Pasta Sauce"), "Sauce sind keine Nudeln");
  assert.ok(hat("Nudeln", "Spaghetti"));
  assert.ok(!hat("Eis", "Pfeffer") && !hat("Eis", "Trauben") && !hat("Eis", "Lebkuchen"), "weiß/Weiss ist kein Eis");
  assert.ok(hat("Eis", "Wassereis"), "Wassereis ist Eis");
  assert.ok(hat("Lebkuchen", "Weiss Lebkuchen"));
  // Ganzer Produktname: Abteilung (Käse) zählt nicht dagegen; ein einzelnes Wort aber schon
  const adler = { id: "ta", kette: "mpreis", name: "Tirol Milch Tiroler Adler 45%", preis: 1.79, menge: 100, einheit: "g",
    kategorie: "Lebensmittel > Milch & Eier > Käse > Schnittkäse" };
  assert.ok(A.finde(A.parseZeile("Tiroler Adler 300g"), [adler], null).length === 1, "Tiroler Adler");
  assert.equal(A.kosten(A.parseZeile("Tiroler Adler 300g"), adler).stueck, 3, "3 × 100 g");
  assert.ok(A.finde(A.parseZeile("Milch"), [adler], null).length === 0, "Milch findet keinen Käse");
});

// ---------- Österreichische und deutsche Schreibweisen ----------
const schreibweise = (suche, ...produkte) => {
  const e = A.parseListe(suche)[0];
  return produkte.map((name) => A.bewerte(e, { name }) >= A.SCHWELLE);
};

test("Wortgruppen: Rote Rüben = Rote Bete = Rote Beete = Rotebeete", () => {
  for (const s of ["Rote Rüben", "Rote Bete", "Rote Beete", "Rotebeete", "rote-rüben"]) {
    assert.deepEqual(schreibweise(s, "Machland Rote Rüben", "Rote Bete gekocht"), [true, true], s);
  }
  assert.deepEqual(schreibweise("Grüne Bohnen", "Clever Fisolen geschnitten"), [true]);
  assert.deepEqual(schreibweise("Gelbe Rüben", "Clever Karotten"), [true]);
  assert.deepEqual(schreibweise("Saure Sahne", "Schärdinger Sauerrahm"), [true]);
});

test("Schreibweisen: Hendel, Vogerlsalat, Germ, Staubzucker, Kukuruz …", () => {
  const faelle = [
    ["Hendelfilet", "Federike Hendl-Filet"], ["Putenbrust", "Truthahnbrust natur"], ["Feldsalat", "M Vogerlsalat"],
    ["Kopfsalat", "Häuptelsalat"], ["Porree", "Da komm ich her! Lauch"], ["Peperoni", "Clever Pfefferoni mild"],
    ["Blaubeeren", "Heidelbeeren 125 g"], ["Hefe", "Haas Germ"], ["Puderzucker", "Wiener Zucker Staubzucker"],
    ["Mais", "Kukuruz Kolben"], ["Kassler", "Geselchtes Karree"], ["Roastbeef", "Beiried geschnitten"],
    ["Berliner", "Marillenkrapfen"], ["Bonbons", "Zuckerl Mischung"], ["Pflaumenmus", "Darbo Powidl"],
    ["Fleischkäse", "Clever Leberkäse"], ["Würstchen", "Berner Würstel"], ["Konfitüre", "Marillen Marmelade"],
    ["Spätzle", "Omis Schmankerl Nockerl"], ["Rotkohl", "M Blaukraut"], ["Weißkohl", "M Weißkraut"],
    ["Hafermilch", "M-BIO Haferdrink ungesüßt"], ["Tomatenmark", "Paradeismark"], ["Holunder", "Holler Sirup"],
  ];
  for (const [suche, produkt] of faelle) assert.deepEqual(schreibweise(suche, produkt), [true], `${suche} -> ${produkt}`);
});

test("Falsche Wortenden: Topf, Knoblauch, Gehackte Tomaten", () => {
  assert.deepEqual(schreibweise("Topfen", "Petersilie im Topf", "BILLA Gurkentopf", "Clever Magertopfen"), [false, false, true]);
  assert.deepEqual(schreibweise("Lauch", "Clever Knoblauch", "Schnittlauch", "Lauch"), [false, false, true]);
  assert.deepEqual(schreibweise("Faschiertes", "Clever Gehackte Tomaten", "Frisches Faschiertes gemischt"), [false, true]);
  assert.deepEqual(schreibweise("Eier", "Pflügelmeier Russenkraut", "Matreier Henkele", "Clever Eier M"), [false, false, true]);
});

test("Energydrinks: Monster Energy findet Penny „Monster“, Marke findet Energy Drink", () => {
  const kat = "Getränke > Alkoholfreie Getränke";
  const passt = (suche, ...namen) => {
    const e = A.parseListe(suche)[0];
    return namen.map((name) => A.bewerte(e, { name, kategorie: kat }) >= A.SCHWELLE);
  };
  const e = A.parseListe("24x Monster Energy")[0];
  assert.equal(e.anzahl, 24);
  assert.deepEqual(passt("24x Monster Energy", "Monster", "Monster Energy Ultra White", "Hell Classic Energydrink"), [true, true, false]);
  assert.deepEqual(passt("Monster", "Monster", "Keli Limonade"), [true, false]);
  assert.deepEqual(passt("Monster Energy Drink", "Monster"), [true]);
  assert.deepEqual(passt("Red Bull", "Red Bull", "Red Bull* Energy Drink"), [true, true]);
  assert.deepEqual(passt("Energy Drink", "Hell Classic Energydrink", "Red Bull* Energy Drink", "LiveFresh Skyr Drink"), [true, true, false]);
  assert.deepEqual(passt("Proteindrink", "Hell Classic Energydrink", "Red Bull* Energy Drink"), [false, false]);
});

test("Synonyme: Kartoffeln = Erdäpfel, Melanzani = Aubergine, Egg = Eier", () => {
  assert.deepEqual(schreibweise("Kartoffeln", "ECHT BIO! Erdäpfel", "Clever Erdäpfel festkochend"), [true, true]);
  assert.deepEqual(schreibweise("Erdäpfel", "Bio Kartoffeln"), [true]);
  assert.deepEqual(schreibweise("Aubergine", "Melanzani"), [true]);
  assert.deepEqual(schreibweise("Melanzani", "Bio Auberginen"), [true]);
  assert.deepEqual(schreibweise("Eggs", "Clever Eier aus Bodenhaltung M", "Pflügelmeier Russenkraut"), [true, false]);
  assert.deepEqual(schreibweise("Egg", "Freilandeier"), [true]);
  assert.deepEqual(schreibweise("Eier", "Free Range Eggs", "Matreier Henkele"), [true, false]);
});
