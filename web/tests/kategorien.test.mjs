// Tests für die einheitlichen Produkt-Kategorien. Ausführen im Ordner web:  node --test
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const K = createRequire(import.meta.url)("../kategorien.js");
const von = (name, kategorie) => K.von({ name, kategorie });

test("Produktname entscheidet, wenn der Markt keine Kategorie liefert (Spar, Lidl, Hofer)", () => {
  const faelle = {
    "Schärdinger Bergbauern Joghurt": "milch", "NÖM PRO Cottage Cheese": "milch", "Große Bio-Eier": "milch", "1 kg Topfen": "milch",
    "S-BUDGET Hendlfilet aus Österreich": "fleisch", "Thunfisch in Öl": "fleisch", "Iglo Fischstäbchen mit Käse": "tk",
    "Bananen": "obst", "Mild-nussiger Bio-Butternuss Kürbis": "obst", "Honigmelone": "obst",
    "Rummo Pasta": "vorrat", "Bio-Basmati-Reis": "vorrat", "Mani natives Olivenöl extra": "vorrat", "Erdnussbutter": "vorrat",
    "Römerquelle Mineralwasser": "getraenke", "SPAR Eistee": "getraenke", "Pepsi Zero": "getraenke",
    "Bellarom Espresso Cremoso": "kaffee", "Dallmayr Prodomo": "kaffee", "Früchtetee": "kaffee",
    "TAIGA Wodka": "alkohol", "Wieselburger Gold": "alkohol", "Grüner Veltliner": "alkohol",
    "Milka Nikolo": "suess", "Küfferle Katzenzungen Adventkalender": "suess", "Speiseeis Vanille": "suess",
    "Premium Bio-Handsemmel": "brot", "Chef Select Lasagne Bolognese": "fertig",
    "Gourmet Gold Katzennahrung": "drogerie", "Tetesept Badesalz": "drogerie",
    "SHARP 55 Zoll Smart TV": "sonstiges",
  };
  for (const [name, erwartet] of Object.entries(faelle)) assert.equal(von(name), erwartet, name);
});

test("Markt-Kategorie: der genaueste Teil zählt", () => {
  assert.equal(von("Irgendwas", "Lebensmittel > Konserven, Fertiggerichte & Suppen > Saucen > Sugo & Pesto"), "vorrat");
  assert.equal(von("Irgendwas", "Lebensmittel > Konserven, Fertiggerichte & Suppen > Fertiggerichte > Dosengerichte"), "fertig");
  assert.equal(von("Irgendwas", "Kühlwaren > Getränke > Milch- & Joghurtgetränke"), "milch");
  assert.equal(von("Irgendwas", "Getränke > Alkoholfreie Getränke > Eistee"), "getraenke");
  assert.equal(von("Irgendwas", "Rein Pflanzlich > Rein Pflanzliche Vorräte > Süßes & Salziges"), "suess");
  assert.equal(von("Irgendwas", "Getränke > Wein & Schaumwein > Wein > Rotwein"), "alkohol");
});

test("Tiefkühl-Abteilung schlägt alles (kein 'Reis' in 'Bechereis')", () => {
  assert.equal(von("Magnum", "Lebensmittel > Tiefkühl > Eis > Bechereis"), "tk");
  assert.equal(von("Erbsen", "Tiefkühl > Obst, Gemüse & Kräuter > Gemüse"), "tk");
});

test("Allgemeine Markt-Kategorie ohne Aussage: Name entscheidet", () => {
  assert.equal(von("Pepsi Cola", "Neu im Online Shop"), "getraenke");
});

test("Fitness-Gruppen landen in der passenden Kategorie", () => {
  const faelle = { "Joghurt": "milch", "Skyr": "milch", "Kefir": "milch", "Eier": "milch", "Cottage Cheese": "milch",
    "Hühnerbrust": "fleisch", "Putenbrust": "fleisch", "Rind mager": "fleisch", "Lachs": "fleisch", "Garnelen": "fleisch", "Magerer Fisch": "fleisch",
    "Nudeln": "vorrat", "Reis": "vorrat", "Nüsse": "vorrat", "Olivenöl": "vorrat", "Linsen & Bohnen": "vorrat", "Erdnussbutter": "vorrat",
    "Gemüse": "obst", "Obst": "obst", "Erdäpfel": "obst", "Bananen": "obst",
    "Energy Drink": "getraenke", "Zero-Getränk": "getraenke", "Zero-Sirup": "getraenke", "Eiweißbrot": "brot" };
  for (const [kat, erwartet] of Object.entries(faelle)) assert.equal(K.von({ name: "X", kategorie: kat }), erwartet, kat);
});

test("Jede Kategorie hat einen Namen", () => {
  for (const k of K.LISTE) assert.equal(K.NAME[k.id], k.name);
});

test("Tiefgefroren: Iglo/Frosta und Lidl-Hinweis 'In der Tiefkühltruhe' auch ohne Tiefkühl-Abteilung", () => {
  assert.equal(K.NAME.tk, "Tiefgefroren");
  assert.equal(von("Iglo Broccoli", "Gemüse"), "tk"); // Fitness-Gruppe statt Markt-Abteilung
  assert.equal(von("Iglo Königsgarnelen ASC", "Garnelen"), "tk");
  assert.equal(von("FRoSTA Paella"), "tk");
  assert.equal(K.von({ name: "Deluxe Zanderfilet Portionen", kategorie: "Magerer Fisch",
    beschreibung: "Je 450 g · 1 kg = 17.76 · In der Tiefkühltruhe" }), "tk");
  assert.equal(von("Igloo Kühlbox"), "sonstiges"); // nur die Marke, kein Wortteil
  assert.equal(von("Broccoli", "Gemüse"), "obst");
});
