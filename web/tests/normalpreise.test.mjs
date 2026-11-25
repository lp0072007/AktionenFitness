// Tests für die Normalpreise (Sortiment aus den Online-Shops). Ausführen im Ordner web:  node --test
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const A = createRequire(import.meta.url)("../abgleich.js");

// Aufbau wie data/sortiment.js (python -m aktionen.sortiment)
const SORTIMENT = {
  erstellt: "2026-11-25T18:00:00+01:00",
  ketten: {
    billa: {
      stand: "2026-11-25T18:00:00+01:00", link: "https://shop.billa.at/produkte/{}",
      kategorien: ["Kühlwaren > Milchprodukte", "Süßes & Salziges > Knabbereien", "Vorratsschrank > Konserven"],
      produkte: [
        ["clever-magertopfen", "Clever Magertopfen", 0.99, 250, "g", 0, null, 0],
        ["popcorn", "Clever Mikrowellen Popcorn Butter 3er", 1.49, 300, "g", 0, null, 1],
        ["teebutter", "Clever Teebutter", 1.59, 250, "g", 0, null, 0],
        ["gurkentopf", "BILLA Gurkentopf", 3.79, 1600, "g", 0, null, 2],
        ["thun-oel", "BILLA Thunfisch in Olivenöl 2er", 2.89, 160, "g", 0, null, 2],
        ["olivenoel", "Clever Olivenöl", 5.99, 1000, "ml", 0, null, 2],
      ],
    },
    mpreis: {
      stand: "2026-11-25T18:00:00+01:00", link: "https://www.mpreis.at/shop/p/{}", kategorien: ["Lebensmittel > Milch & Eier"],
      produkte: [
        ["1", "Jeden Tag Speisetopfen mager", 1.09, 250, "g", 0, 1.29, 0],
        ["2", "Jeden Tag Eier Bodenhaltung", 3.29, 10, "stk", 0, null, 0],
        ["3", "Jausen-/Ostereier Lose", 0.39, 70, "g", 0, null, 0],
      ],
    },
  },
};
const PRODUKTE = A.sortimentAuspacken(SORTIMENT);
const rechnen = (text, aktionen = []) => A.mitNormalpreisen(A.auswerten(A.parseListe(text), aktionen), PRODUKTE);
const name = (t) => t?.angebot.name;

test("Auspacken: Aufbau wie die Aktionen, mit Link und Kategorie", () => {
  const a = PRODUKTE.find((p) => p.id === "s:billa:clever-magertopfen");
  assert.equal(a.kette, "billa");
  assert.equal(a.url, "https://shop.billa.at/produkte/clever-magertopfen");
  assert.equal(a.kategorie, "Kühlwaren > Milchprodukte");
  assert.equal(a.dauerpreis, true);
  assert.equal(PRODUKTE.find((p) => p.id === "s:mpreis:1").normalpreis, 1.29);
  assert.deepEqual(A.sortimentAuspacken(undefined), []);
});

test("Topfen: kein Gurkentopf, Menge wird umgerechnet", () => {
  const n = rechnen("1kg Topfen");
  const e = n.proEintrag[0];
  assert.equal(name(e.bestProKette.billa), "Clever Magertopfen");
  assert.equal(e.bestProKette.billa.kosten.stueck, 4);
  assert.equal(name(e.bestProKette.mpreis), "Jeden Tag Speisetopfen mager");
});

test("Butter: kein Popcorn aus der Knabber-Abteilung", () => {
  assert.equal(name(rechnen("Butter").proEintrag[0].bestProKette.billa), "Clever Teebutter");
});

test("Olivenöl: nicht Thunfisch in Olivenöl – aber 'Thunfisch in Öl' findet ihn", () => {
  assert.equal(name(rechnen("Olivenöl").proEintrag[0].bestProKette.billa), "Clever Olivenöl");
  assert.equal(name(rechnen("Thunfisch in Öl").proEintrag[0].bestProKette.billa), "BILLA Thunfisch in Olivenöl 2er");
});

test("Eier: Packung statt einzelnem Osterei", () => {
  assert.equal(name(rechnen("Eier").proEintrag[0].bestProKette.mpreis), "Jeden Tag Eier Bodenhaltung");
});

test("Alles in einem Geschäft: Aktion zählt, wenn billiger als der Normalpreis", () => {
  const aktion = { id: "a1", kette: "billa", name: "NÖM Magertopfen", preis: 0.79, normalpreis: 1.19, menge: 250, einheit: "g" };
  const n = rechnen("Topfen\nButter\nEier", [aktion]);
  const billa = n.einGeschaeft.find((z) => z.kette === "billa");
  assert.equal(billa.aktion, 1);
  assert.equal(billa.normal, 1);
  assert.deepEqual(billa.fehlt.map((e) => e.text), ["Eier"]);
  assert.ok(Math.abs(billa.preis - (0.79 + 1.59)) < 1e-9);
  const mpreis = n.einGeschaeft.find((z) => z.kette === "mpreis");
  assert.deepEqual([mpreis.aktion, mpreis.normal, mpreis.fehlt.length], [0, 2, 1]); // Topfen, Eier; keine Butter
  // Sortierung: mehr gefunden zuerst (beide 2), dann billiger
  assert.deepEqual(n.einGeschaeft.map((z) => z.kette), ["billa", "mpreis"]);
});

test("Ohne Aktion: günstigster Normalpreis überhaupt", () => {
  const n = rechnen("Butter");
  assert.equal(n.ohneAktion.length, 1);
  assert.equal(name(n.ohneAktion[0].treffer), "Clever Teebutter");
});

test("Abgewählte Sortiments-Treffer zählen nicht", () => {
  const r = A.auswerten(A.parseListe("Butter"), []);
  const n = A.mitNormalpreisen(r, PRODUKTE, { ausgeschlossen: new Set(["s:billa:teebutter"]) });
  assert.equal(n.proEintrag[0].bestProKette.billa, undefined);
});

test("Vorfilter ändert keine Bewertung", () => {
  const begriffe = ["Topfen", "Magertopfen", "Butter", "Eier", "Olivenöl", "Öl", "Thunfisch in Öl", "Protein Bar", "Popcorn"];
  try {
    for (const b of begriffe) {
      const e = A.parseListe(b)[0];
      A.vorfilter = true;
      const mit = PRODUKTE.map((p) => A.bewerte(e, p));
      A.vorfilter = false;
      const ohne = PRODUKTE.map((p) => A.bewerte(e, p));
      assert.deepEqual(mit, ohne, b);
    }
  } finally {
    A.vorfilter = true;
  }
});
