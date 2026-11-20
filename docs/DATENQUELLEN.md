# Datenquellen

Recherche-Stand: 20.11.2026. Grundlage sind die Scraper des Open-Source-Projekts
[heissepreise](https://github.com/badlogic/heissepreise) (Ordner `stores/`), die zeigen, welche JSON-Schnittstellen
die Webshops intern verwenden. Offizielle, dokumentierte APIs bietet keine Kette an.

## Spar (erste Kette)

| Was | Stand |
|---|---|
| Bisheriger Endpunkt | `https://search-spar.spar-ics.com/fact-finder/rest/v4/search/products_lmos_at?query=*&q=*&page=1&hitsPerPage=…` |
| Live-Test 20.11.2026 | ❌ Server antwortet, aber `"Channel 'products_lmos_at' does not exist."`, der Kanalname hat sich geändert |
| Technik | FACT-Finder (Suchdienst), liefert JSON mit `hits[].masterValues` |
| www.spar.at | Cloudflare-Schutz („Just a moment…“) bei einfachen Requests |

**Bekannte Felder in `masterValues`** (aus heissepreise, Stand der alten API):
`product-number`, `title` (Marke), `name`, `short-description`, `short-description-2/3` (Menge, z. B. „450 g“),
`price`, `price-per-unit` (z. B. „€8,87/kg“), `item-type` (`WeightProduct` bei Gewichtsware), `biolevel`, `marketing-text`.
Welche Felder Aktionen markieren (Streichpreis, Aktionstext, gültig bis) ist noch **unbekannt**.

### Nächster Schritt: aktuellen Endpunkt im Browser finden

1. Auf https://www.spar.at (oder interspar.at) im Online-Shop nach „Skyr“ suchen
2. DevTools öffnen (F12) → Tab **Network** → Filter **Fetch/XHR**
3. Seite neu laden / Suche wiederholen und nach Requests suchen, die JSON mit Produkten liefern
   (Stichworte: `fact-finder`, `search`, `products`, `spar-ics`)
4. Rechtsklick auf den Request → „Copy as cURL“ und in `docs/spar-request.txt` speichern
   (Cookies/Tokens vorher entfernen)
5. Die Antwort (Response) als `scraper/tests/fixtures/spar_echt.json` speichern, damit wir Parser und Tests
   auf echten Daten aufbauen und die Aktionsfelder finden

Zusätzlich die **Aktionsseite** (spar.at → Angebote / Flugblatt) ansehen: Kommen die Angebote dort ebenfalls als JSON?

## Weitere Ketten (für später, laut heissepreise)

| Kette | Endpunkt (intern, ungeprüft) |
|---|---|
| Billa | `https://shop.billa.at/api/product-discovery/categories/{id}/products?pageSize=500&page={n}` |
| Penny | `https://www.penny.at/api/products?page={n}&pageSize={n}` |
| Lidl | `https://www.lidl.at/p/api/gridboxes/AT/de/?max={n}` |
| Hofer | über roksh.at (`https://www.roksh.at/hofer/angebot/`) |
| MPreis | Algolia-Suchindex (`prod_mpreis_8450`) |
| ADEG | kein Shop → Flugblatt-PDF + KI-Auswertung |

Alternative Rohdaten: heisse-preise.io stellt `data/latest-canonical.json` bereit (alle Ketten, aber keine
Aktionszeiträume und kein offizielles API).

## Nährwerte

- [Open Food Facts](https://world.openfoodfacts.org/data): kostenlos, Abfrage per EAN:
  `https://world.openfoodfacts.org/api/v2/product/{ean}.json`
- Manuelle Basisliste für Generika (Magertopfen, Hühnerbrust, Haferflocken, …)
