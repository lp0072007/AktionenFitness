// Testliste: ~55 typische Einträge gegen eingefrorene echte Aktionen. Ausführen im Ordner web:  node --test
// Ausführlicher Bericht (Trefferquote, alle Fehler):  node tests/testliste.test.mjs --bericht
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { FAELLE } from "./testliste/erwartet.mjs";

const A = createRequire(import.meta.url)("../abgleich.js");
const ANGEBOTE = JSON.parse(readFileSync(new URL("./testliste/angebote.json", import.meta.url), "utf8"));
const NAME = Object.fromEntries(ANGEBOTE.map((a) => [a.id, a.name]));

function pruefen(fall) {
  const treffer = new Set(A.finde(A.parseZeile(fall.eingabe), ANGEBOTE).map((t) => t.angebot.id));
  return {
    fehlt: (fall.muss ?? []).filter((id) => !treffer.has(id)),
    falsch: (fall.nicht ?? []).filter((id) => treffer.has(id)),
  };
}

test("Testliste: Daten und Erwartungen passen zusammen", () => {
  for (const f of FAELLE) for (const id of [...(f.muss ?? []), ...(f.nicht ?? [])]) {
    assert.ok(NAME[id], `${f.eingabe}: Angebot ${id} fehlt in angebote.json`);
  }
  assert.ok(FAELLE.length >= 50, "mindestens 50 Fälle");
});

for (const fall of FAELLE) {
  test(`Testliste: ${fall.eingabe}`, () => {
    const { fehlt, falsch } = pruefen(fall);
    assert.deepEqual(
      { fehlt: fehlt.map((id) => NAME[id]), falsch: falsch.map((id) => NAME[id]) },
      { fehlt: [], falsch: [] },
    );
  });
}

// Bericht: node tests/testliste.test.mjs --bericht
if (process.argv.includes("--bericht")) {
  let muss = 0, mussOk = 0, nicht = 0, nichtOk = 0;
  for (const f of FAELLE) {
    const { fehlt, falsch } = pruefen(f);
    muss += f.muss?.length ?? 0; mussOk += (f.muss?.length ?? 0) - fehlt.length;
    nicht += f.nicht?.length ?? 0; nichtOk += (f.nicht?.length ?? 0) - falsch.length;
    if (fehlt.length || falsch.length) {
      console.log(`✗ ${f.eingabe}`);
      for (const id of fehlt) console.log(`    fehlt:  ${NAME[id]}`);
      for (const id of falsch) console.log(`    falsch: ${NAME[id]}`);
    }
  }
  console.log(`\n${FAELLE.length} Einträge · gefunden ${mussOk}/${muss} (${Math.round((100 * mussOk) / muss)} %) · ` +
    `Fehltreffer vermieden ${nichtOk}/${nicht} (${Math.round((100 * nichtOk) / nicht)} %)`);
}
