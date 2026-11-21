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
| A.8 | Eingabe ausgebaut: Kommas, Klammern als Notiz, „10er“, „½ kg“, Überschriften, Kästchen; optionale Eigenschaften (light, mager …); Vorschau „So verstanden“ | ☑ |

Grenzen von Schritt A: Ohne Normalpreise kann der **Gesamtpreis** eines Einkaufs nicht berechnet werden. Es lässt sich nur
sagen, was in Aktion ist und wie viel man dabei spart (sofern der Händler den Normalpreis angibt).

---

## Phase 0: Machbarkeit Sortimente

| # | Aufgabe | Status |
|---|---|---|
| 0.1 | Billa-Gesamtsortiment abrufen: Anzahl, Dauer, Datenmenge | ☑ |
| 0.2 | Penny-Gesamtsortiment, gleiche Prüfung | ☑ |
| 0.3 | Hofer-Dauersortiment auf hofer.at untersuchen | ☑ |
| 0.4 | Lidl: welcher Teil des Sortiments ist online? | ☑ |
| 0.5 | Spar-Alternative (später): heisse-preise.io-Rohdaten (Aktualität, Lizenz, Abdeckung) | ☐ |
| 0.6 | Architektur-Entscheidung: alles im Browser oder Backend (Python-API + SQLite) | ☑ |

### Ergebnisse (20.11.2026)

| Kette | Gesamtsortiment online? | Befund |
|---|---|---|
| **Billa** | ✅ ja | Gleiche API wie bei den Aktionen, nur ohne `inPromotion=true`. Lebensmittel-Kategorien: Obst & Gemüse 315, Brot & Gebäck 565, Kühlwaren 1.273, Fleisch/Wurst/Fisch 748, Tiefkühl 780, Vorratsschrank 2.574, Schnelle Küche 590, Getränke 2.317, Rein pflanzlich 2.202 (überschneidet sich). **≈ 9.000–11.000 Produkte**, ca. 0,2 s pro Seite → ein paar Minuten pro Abruf. Normalpreis in `price.regular.value`, Grundpreis in `perStandardizedQuantity`. |
| **dm** | ✅ ja (Drogerie-Lebensmittel) | Such-API liefert das ganze Sortiment, aber Rate-Limit (429) → langsam, nur gezielte Suchbegriffe sinnvoll. |
| **Hofer** | ◐ teilweise | `/produkte` hat 23 Kategorien (Milchprodukte, Brot, Fleisch mit Unterkategorien, Fisch, Saison …), 60 Produkte pro Seite (`?page=N`), der vorhandene Parser funktioniert. Milchprodukte + Brot = 194 Produkte. **Fehlt:** Getränke, Vorrat (Nudeln, Reis, Haferflocken …). „Dauerhaft günstiger“ hat nur 38 Produkte. |
| **Penny** | ❌ nein | Online nur die aktuellen Angebote (~590 in 12 Kategorien, alle mit Gültigkeit). |
| **Lidl** | ❌ nein | Website zeigt nur Aktionen und Saisonware (Suche „Haferflocken“ → 0 Treffer, Kategorie „Lebensmittel“ = Aktionsartikel mit Gültigkeit). |
| **Spar** | ❌ (vorerst) | Onlineshop hinter Cloudflare. Später evtl. über heisse-preise.io (0.5). |

**Folgerung:** Ein echter Gesamtpreis ist nur bei **Billa** (und dm) machbar, bei Hofer für einen Teil der Liste.
Für Lidl, Penny und Spar zählen weiterhin nur Aktionen. Die Ergebnisseite muss deshalb pro Geschäft anzeigen,
wie viele Produkte der Liste überhaupt bepreist werden konnten („Billa: 12/12, Hofer: 7/12“).

**0.6 Architektur:** Python-Abruf + **SQLite** (`data/preise.db`, mit Preisverlauf) als Quelle. Für die Website wird daraus
weiterhin eine statische Datei erzeugt (kompakter Katalog, ~1–2 MB gzip), damit GitHub Pages reicht. Ein eigener Server
ist erst nötig, wenn der Katalog zu groß für den Browser wird.

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
| 2.3 | Testset ~50 Einträge mit erwarteten Treffern, Trefferquote messen (`web/tests/testliste.test.mjs`, 56 Einträge; vorher 75 % gefunden / 83 % Fehltreffer vermieden, jetzt 100 % / 100 %) | ☑ |

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
