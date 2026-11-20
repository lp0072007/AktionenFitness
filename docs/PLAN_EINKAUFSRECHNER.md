# Plan: Einkaufsrechner

Ziel: Einkaufsliste eingeben → Abgleich mit Aktionen (und später Normalpreisen) → Empfehlung, wo man am günstigsten
einkauft, inklusive Gesamtpreis pro Geschäft und sinnvoller Kombination aus 2–3 Geschäften.

Entscheidungen (20.11.2026):
- Spar ist beim Gesamtpreis vorerst nicht dabei (Onlineshop hinter Cloudflare). Spar-Aktionen aus dem Flugblatt zählen.
- Reihenfolge: zuerst Schritt A (Liste ↔ Aktionen), danach Phase 0 (Machbarkeit Sortimente).

Legende: ☐ offen · ◐ in Arbeit · ☑ erledigt

---

## Schritt A: Einkaufsliste mit Aktionen abgleichen

| # | Aufgabe | Status |
|---|---|---|
| A.1 | Export: **alle** Lebensmittel-Aktionen aller Ketten (nicht nur Fitness) als `web/data/aktionen.js` | ☑ |
| A.2 | Eingabe als Stichpunkte („- 2x Milch“, „• Haferflocken 1kg“, „500g Hendlfilet“) → Begriff + Menge | ☑ |
| A.3 | Namensabgleich: Normalisierung (Umlaute, Bindestriche), Synonyme (Topfen/Quark, Erdäpfel/Kartoffeln, Hendl/Huhn …), deutsche Komposita („Milch“ passt zu „Vollmilch“, nicht zu „Milchschnitte“) | ☑ |
| A.4 | Gültigkeit am gewählten Einkaufstag berücksichtigen, Spar nach Region | ☑ |
| A.5 | Empfehlung: pro Geschäft „x von n Produkten in Aktion, Ersparnis ≥ y €“ und günstigste Aufteilung pro Produkt | ☑ |
| A.6 | Seite `web/einkauf.html`: Eingabe, Ergebnis, Treffer an-/abwählen, Neuberechnung | ☑ |
| A.7 | Tests für Parser und Abgleich (`node --test`) mit typischen Einträgen | ☑ |

Grenzen von Schritt A: Ohne Normalpreise kann der **Gesamtpreis** eines Einkaufs nicht berechnet werden. Es lässt sich nur
sagen, was in Aktion ist und wie viel man dabei spart (sofern der Händler den Normalpreis angibt).

---

## Phase 0: Machbarkeit Sortimente

| # | Aufgabe | Status |
|---|---|---|
| 0.1 | Billa-Gesamtsortiment abrufen: Anzahl, Dauer, Datenmenge | ☐ |
| 0.2 | Penny-Gesamtsortiment, gleiche Prüfung | ☐ |
| 0.3 | Hofer-Dauersortiment auf hofer.at untersuchen | ☐ |
| 0.4 | Lidl: welcher Teil des Sortiments ist online? | ☐ |
| 0.5 | Spar-Alternative (später): heisse-preise.io-Rohdaten (Aktualität, Lizenz, Abdeckung) | ☐ |
| 0.6 | Architektur-Entscheidung: alles im Browser oder Backend (Python-API + SQLite) | ☐ |

## Phase 1: Produktkatalog

| # | Aufgabe | Status |
|---|---|---|
| 1.1 | Modell `Produkt`: Kette, ID, Name, Marke, Menge, Einheit, Normalpreis, Aktionspreis, Bedingung, Gültigkeit, Kategoriepfad, EAN, Stand | ☐ |
| 1.2 | SQLite-Datenbank `data/preise.db` statt JSON, mit Preisverlauf | ☐ |
| 1.3 | Katalog-Scraper pro Kette (Billa, Penny, dm, Hofer, Lidl) | ☐ |
| 1.4 | Aktionen mit Katalog verknüpfen (Produkt-ID; Spar über Namensabgleich) | ☐ |
| 1.5 | Zeitplan: Katalog wöchentlich, Aktionen Mo + Do | ☐ |

## Phase 2: Einkaufsliste verstehen (Ausbau von Schritt A)

| # | Aufgabe | Status |
|---|---|---|
| 2.1 | Mengen umrechnen: 1 kg gebraucht, 500-g-Packung → 2 Stück; Mengenaktionen einrechnen | ☐ |
| 2.2 | Vorlieben: Bio, Marke fix/egal, Eigenmarke ok | ☐ |
| 2.3 | Testset ~50 Einträge mit erwarteten Treffern, Trefferquote messen | ☐ |

## Phase 3: Optimierung „Wo einkaufen?“

| # | Aufgabe | Status |
|---|---|---|
| 3.1 | Gesamtpreis pro Geschäft (inkl. „nicht verfügbar“) | ☐ |
| 3.2 | Beste Kombination aus 2–3 Geschäften mit Mindestersparnis pro zusätzlichem Weg | ☐ |
| 3.3 | Theoretisches Minimum (jedes Produkt im billigsten Geschäft) | ☐ |
| 3.4 | Kundenkarten (Lidl Plus, jö) als Schalter | ☐ |

## Phase 4: Oberfläche

| # | Aufgabe | Status |
|---|---|---|
| 4.1 | Ergebnisseite mit Empfehlung, Liste pro Geschäft, Ersparnis | ☐ |
| 4.2 | Falsche Treffer korrigieren, Alternative wählen | ☐ |
| 4.3 | Listen speichern, teilen, Fitness-Liste übernehmen | ☐ |

## Phase 5: Betrieb

| # | Aufgabe | Status |
|---|---|---|
| 5.1 | Automatischer Datenabruf (GitHub Actions oder Windows-Aufgabenplanung) | ☐ |
| 5.2 | Überwachung: Warnung, wenn eine Kette plötzlich 0 Produkte liefert | ☐ |
| 5.3 | Hosting (statisch oder mit Backend) | ☐ |
