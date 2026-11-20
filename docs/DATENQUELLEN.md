# Datenquellen

Recherche-Stand: 20.11.2026. Grundlage sind die Scraper des Open-Source-Projekts
[heissepreise](https://github.com/badlogic/heissepreise) (Ordner `stores/`), die zeigen, welche JSON-Schnittstellen
die Webshops intern verwenden. Offizielle, dokumentierte APIs bietet keine Kette an.

## Spar (erste Kette)

### Aktueller Endpunkt (gefunden 20.11.2026 über DevTools) ✅

| Endpunkt | Zweck |
|---|---|
| `https://www.interspar.at/api/search/flyout?q=skyr&scope=all` | Suchvorschläge, max. 5 Produkte, `total` = Gesamtzahl |
| `https://www.interspar.at/api/search/results?q=skyr&scope=all&productLimit=…` | Suchergebnisseite (Format noch prüfen) |

Beispielantwort: `scraper/tests/fixtures/spar_flyout_skyr.json`. Wichtige Felder pro Produkt:

| Feld | Beispiel | Bedeutung |
|---|---|---|
| `productNumber` | `2020004900746` | Spar-Artikelnummer (keine EAN) |
| `name` | `S-BUDGET Skyr 1 KG` | Name inkl. Menge am Ende |
| `brand` | `S-BUDGET` | Marke |
| `price.currentPrice` | `2.99` | aktueller Preis |
| `price.referencePrice.price` | `2.99` | Grundpreis pro kg / l |
| `unit.shortCode` | `kg` / `l` | Einheit des Grundpreises |
| `badges.image[].key` | `vegan`, `lactose-free` | Eigenschaften |
| `image.url` | … | Produktbild |
| `availabilityCase` | `fos-market-search` / `online-only` | im Markt / nur online |

**Test mit Flugblatt-Aktion (20.11.2026):** NÖM Cottage Cheese natur 200 G (`2020001850105`) ist im Flugblatt
als Mengenvorteil (1 Stk. 1,99 €, ab 2 Stk. je 1,19 €). Die Such-API zeigt nur `currentPrice: 1.99` und **keine**
Aktionsinfo. Die Suche liefert also nur Regalpreise, keine Flugblatt-Aktionen.

Weitere Endpunkte auf der Produktseite (noch nicht ausgewertet):
- `/api/product/by-number/{productNumber}`: Produktdetails (evtl. Aktionen, Nährwerte)
- `/api/data/p/{productNumber}`
- `/api/markets/locations`: Märkte (Preise/Aktionen evtl. marktabhängig)

**Offen:**
- **Aktionsfelder** (Streichpreis, Aktionstext, gültig bis): In der Beispielantwort war kein Produkt in Aktion.
  → Ein Produkt suchen, das gerade im Angebot ist, und dessen JSON ansehen.
- **Aktionsseite**: Gibt es einen Endpunkt, der *alle* aktuellen Angebote liefert (statt Suche nach Begriff)?
  → Auf interspar.at/spar.at die Angebote-Seite öffnen und im Network-Tab nach `/api/` suchen.
- **Cloudflare**: Von Cloud-IPs kommt eine „Just a moment…“-Seite statt JSON. Von einer Heim-IP aus testen.
  Wenn das auch blockiert wird, Alternative überlegen (z. B. Billa zuerst).

### Alter Endpunkt (tot)

`search-spar.spar-ics.com/fact-finder/rest/v4/search/products_lmos_at` (von heissepreise genutzt) antwortet
seit 11/2026 mit `"Channel 'products_lmos_at' does not exist."`.

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
