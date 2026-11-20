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
  const skyr = ANGEBOTE.find((a) => a.name.startsWith("Alpro"));
  const zwei = A.kosten(A.parseZeile("2x Skyr"), skyr);
  assert.equal(zwei.aktionGilt, false);
  assert.equal(zwei.preis, 2 * 1.99);
  const drei = A.kosten(A.parseZeile("3x Skyr"), skyr);
  assert.ok(Math.abs(drei.preis - 3 * 1.32) < 1e-9 && Math.abs(drei.ersparnis - 3 * 0.67) < 1e-9);
  const hendl = ANGEBOTE.find((a) => a.name.startsWith("S-BUDGET Hendl"));
  assert.equal(A.kosten(A.parseZeile("1kg Hendlfilet"), hendl).stueck, 2);  // 700-g-Packungen
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
