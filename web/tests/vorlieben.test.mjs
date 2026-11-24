// Tests für Einstellungen (Kundenkarten, vegan/vegetarisch, Bio, Eigenmarken). Ausführen im Ordner web:  node --test
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const V = createRequire(import.meta.url)("../vorlieben.js");
const m = (name, extra = {}) => V.merkmale({ name, kette: extra.kette || "spar", ...extra });
const ALLES = V.STANDARD;

test("Fleisch und Fisch: nicht vegetarisch", () => {
  for (const n of ["Hühnerbrust Filet", "Thunfisch in Öl", "Putenschnitzel", "Wiener Würstel", "Lachsfilet", "Rindsschnitzel aus Österreich",
    "Feine Gabelbissen", "Chicken Nuggets", "Faschierte Laibchen"]) {
    assert.deepEqual([m(n).vegetarisch, m(n).vegan], [false, false], n);
  }
});

test("Kein falscher Alarm bei ähnlichen Wörtern", () => {
  for (const n of ["Studentenfutter", "Fleischtomaten", "Wild Berries Smoothie", "Wiener Kipferl", "Haferflocken Zart", "Rote Linsen"]) {
    assert.notEqual(m(n).vegetarisch, false, n);
  }
});

test("Milch, Ei, Honig: vegetarisch möglich, aber nicht vegan – Pflanzendrinks schon", () => {
  for (const n of ["NÖM Skyr Natur", "Butterkeks", "Freilandeier 10 Stk", "Schärdinger Bergbauern Joghurt", "Mozzarella Minis", "Blütenhonig"]) {
    assert.equal(m(n).vegan, false, n);
    assert.notEqual(m(n).vegetarisch, false, n);
  }
  for (const n of ["Alpro Haferdrink", "Kokosmilch", "Erdnussbutter Crunchy", "Mandelmilch ungesüßt", "Sojajoghurt Natur"]) {
    assert.notEqual(m(n).vegan, false, n);
  }
});

test("Ausdrücklich vegan/vegetarisch schlägt Fleischwörter", () => {
  assert.deepEqual([m("Vegane Bratwurst").vegetarisch, m("Vegane Bratwurst").vegan], [true, true]);
  assert.equal(m("Veggie Burger").vegetarisch, true);
  assert.deepEqual([m("Veggie Burger mit Käse").vegetarisch, m("Veggie Burger mit Käse").vegan], [true, false]);
});

test("Kennzeichnung des Händlers (Billa-Badges) gilt vor dem Namen", () => {
  const alpro = m("Alpro Skyr Natur Ungesüßt", { kette: "billa", merkmale: ["vegan", "vegetarisch"] });
  assert.deepEqual([alpro.vegetarisch, alpro.vegan], [true, true]); // "Skyr" im Namen, trotzdem vegan
  const drink = m("nöm PRO Vanille Proteindrink", { kette: "billa", merkmale: ["vegetarisch"] });
  assert.deepEqual([drink.vegetarisch, drink.vegan], [true, false]);
  assert.equal(m("Irgendwas", { kette: "billa", merkmale: ["bio"] }).bio, true);
  // Kategorie des Händlers
  assert.equal(m("Extra", { kette: "billa", kategorie: "Fleisch, Wurst & Fisch > Wurst" }).vegetarisch, false);
  assert.notEqual(m("Veggie Extra", { kette: "billa", kategorie: "Rein pflanzlich > Fleischalternativen" }).vegetarisch, false);
});

test("Bio und Eigenmarken", () => {
  for (const n of ["Bio-Joghurt", "Ja! Natürlich Vollmilch", "Zurück zum Ursprung Bergbauern Milch", "SPAR Natur*pur Topfen"]) {
    assert.equal(m(n).bio, true, n);
  }
  assert.equal(m("Biskotten").bio, false); // "Bis…" ist kein Bio
  assert.equal(m("S-BUDGET Topfen").eigenmarke, true);
  assert.equal(m("Clever Haferflocken", { kette: "billa" }).eigenmarke, true);
  assert.equal(m("Milsani Skyr", { kette: "hofer" }).eigenmarke, true);
  assert.equal(m("Milbona Skyr", { kette: "lidl" }).eigenmarke, true);
  assert.equal(m("NÖM Skyr", { kette: "billa" }).eigenmarke, false);
  assert.equal(m("Clever Haferflocken", { kette: "spar" }).eigenmarke, false); // Clever gibt es nur bei Billa
});

test("Filter: vegan, vegetarisch, nur Bio, ohne Eigenmarken – unbekannte bleiben drin", () => {
  const angebote = [
    { id: 1, kette: "spar", name: "Hühnerbrust" }, { id: 2, kette: "spar", name: "NÖM Skyr" },
    { id: 3, kette: "spar", name: "Haferflocken" }, { id: 4, kette: "spar", name: "Bio-Haferflocken" },
    { id: 5, kette: "spar", name: "S-BUDGET Reis" },
  ];
  const ids = (v) => V.anwenden(angebote, { ...ALLES, ...v }).map((a) => a.id);
  assert.deepEqual(ids({}), [1, 2, 3, 4, 5]);
  assert.deepEqual(ids({ ernaehrung: "vegetarisch" }), [2, 3, 4, 5]);
  assert.deepEqual(ids({ ernaehrung: "vegan" }), [3, 4, 5]);
  assert.deepEqual(ids({ nurBio: true }), [4]);
  assert.deepEqual(ids({ ohneEigenmarken: true }), [1, 2, 3, 4]);
});

test("Kundenkarten: Kartenpreis wird zum Preis, nur mit der passenden Karte", () => {
  const lidl = { id: "l", kette: "lidl", name: "Skyr", preis: 1.29, zusatzpreis: 0.99, zusatz_text: "Lidl Plus" };
  const penny = { id: "p", kette: "penny", name: "Feine Gabelbissen", preis: 1.99, zusatzpreis: 1.59, zusatz_text: "jö" };
  const spar = { id: "s", kette: "spar", name: "Premium-Baguette Korn", preis: 2.29, zusatzpreis: 1.99, zusatz_text: "SPAR-App" };
  const tag = { id: "t", kette: "spar", name: "Rindsschnitzel", preis: 19.99, zusatzpreis: 14.99 }; // Aktionstag, keine Karte
  assert.deepEqual([lidl, penny, spar, tag].map(V.karteFuer), ["lidlplus", "joe", "sparapp", null]);

  const ohne = V.anwenden([lidl, penny], { ...ALLES });
  assert.deepEqual(ohne.map((a) => a.preis), [1.29, 1.99]);

  const mit = V.anwenden([lidl, penny, spar, tag], { ...ALLES, karten: ["joe"] });
  assert.deepEqual(mit.map((a) => a.preis), [1.29, 1.59, 2.29, 19.99]);
  const p = mit[1];
  assert.deepEqual([p.karte, p.ohne_karte, p.normalpreis, p.zusatzpreis], ["jö Bonus Club", 1.99, 1.99, undefined]);
  assert.equal(p.roh, penny);                          // Original für "+ Liste"
  assert.equal(JSON.stringify(p).includes("roh"), false); // wird nicht mitgespeichert
  // Bestehender Streichpreis bleibt
  const mitStreich = V.mitKarte({ ...lidl, normalpreis: 1.79 }, { ...ALLES, karten: ["lidlplus"] });
  assert.deepEqual([mitStreich.preis, mitStreich.normalpreis], [0.99, 1.79]);
});

test("Beschriftung des Zusatzpreises", () => {
  assert.equal(V.zusatzName({ kette: "penny", zusatzpreis: 1, zusatz_text: "jö" }), "💳 mit jö");
  assert.equal(V.zusatzName({ kette: "lidl", zusatzpreis: 1, zusatz_text: "Lidl Plus" }), "💳 mit Lidl Plus");
  assert.equal(V.zusatzName({ kette: "spar", zusatzpreis: 1 }), "Aktionstag");
});

test("Gespeicherte Einstellungen werden bereinigt", () => {
  assert.deepEqual(V.lesen(), ALLES); // in Node ohne localStorage: Standard
  assert.equal(V.zusammenfassung({ ...ALLES, ernaehrung: "vegan", karten: ["lidlplus"] }), "🌱 vegan · 💳 Lidl Plus");
  assert.equal(V.filtertAktiv({ ...ALLES, karten: ["joe"] }), false); // Karten filtern nichts weg
});
