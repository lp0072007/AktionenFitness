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

### Produktdetails ✅ (inkl. Nährwerte!)

`https://www.interspar.at/api/product/by-number/{productNumber}`, Beispiel:
`scraper/tests/fixtures/spar_detail_cottage_protein.json`

| Feld | Inhalt |
|---|---|
| `product.nutrition[key=INTERSPARPRODUCTNUTRITIONFACTSTABLE].value` | Nährwerttabelle pro 100 g als Text: `Eiweiß \| ca. 12g<br />…` |
| `product.infoSections[].items` | u. a. `Menge` (0,500) + `Einheit` (KG), `Preisgesenkt ab` |
| `product.promotions`, `promotionBadgeText`, `promotionCampaign`, `uvp` | **Aktionsfelder**, Struktur bei Aktion noch unbekannt |
| `breadcrumb` | Kategorie (z. B. Frischkäse) |
| `product.ingredients` | Zutaten, Allergene |

Beim NÖM Cottage Cheese natur (`2020001850105`, KW47 im Flugblatt mit Mengenvorteil) liefert auch die
Detail-API `currentPrice: 1.99` und leere `promotions`. **Flugblatt-Aktionen sind im Online-Shop nicht
enthalten**, wir brauchen dafür das Flugblatt selbst.

### Flugblatt (iPaper)

Seite: `https://www.interspar.at/aktionen/niederoesterreich/niederoesterreich_kw47`, also **pro Bundesland
und Kalenderwoche**.

| Endpunkt | Inhalt |
|---|---|
| `/api/ipaper/leaflets` ✅ | Alle aktuellen Flugblätter: `group`, `slug`, `region`, `validFrom`, `validTo` (UTC, Ende exklusiv), `weekLabel` |
| `/api/ipaper/leaflets/{group}/{slug}` ✅ | Dasselbe + `viewerUrl`, z. B. `https://flugblatt.interspar.at/niederoesterreich/niederoesterreich_kw47/` |
| `/api/ipaper/leaflets/{group}/{slug}/cover` | Titelbild |

Fixtures: `spar_flugblaetter.json`, `spar_flugblatt_noe.json`. Gruppen: 9 Bundesländer (Burgenland Nord/Süd
getrennt, Osttirol eigenes), Einzelmarkt-Folder (z. B. `wien_im20_kw47`), `sonderfolder`, `weinwelt`.

Der Viewer (`flugblatt.interspar.at`) ist ein **iPaper**-Flipbook (`cdn.ipaper.io/flipbooks/api/v3/latest.js`).

**Enrichments** (klickbare Bereiche), z. B. für NÖ KW47:
```
https://cdn.ipaper.io/iPaper/Papers/{paperId}/Enrichments/v1/{version}/{hash}/Page1-25.json
    ?token=HS256-…&token_ignore_params=true&token_path=/iPaper/Papers/{paperId}/Enrichments/&expires={unix}
```
- `paperId` = `fe9329db-0a2c-4b9d-8659-3b30f6e27bf7`, `version` = 1794554264 (13.11.2026, Veröffentlichung)
- Token läuft ca. 1 Tag nach Abruf ab (`expires`), muss also jedes Mal frisch geholt werden.
  **Offen:** Woher kommen paperId, hash und token? Vermutlich aus dem HTML von flugblatt.interspar.at.
- Typ 1 = Link. URL `https://www.interspar.at/p/{Artikelnummer}` → **Artikelnummer im Flugblatt** ✅
- Typ 6 = Menü „Passenden Artikel finden“, Einträge mit `parentid` + `menuitemName`
- Typ 3 = Deko-GIF, Typ 9 = Popup
- Parser: `aktionen/stores/ipaper.py`, Fixture: `spar_ipaper_enrichments.json`

**Viewer-HTML** ✅ (`https://flugblatt.interspar.at/{region}/{slug}/` = `viewerUrl`): enthält
`window.staticSettings` mit
- `pageTexts`: **Volltext jeder Seite** (Index 0 = Seite 1), u. a. „NÖM PRO Cottage Cheese … MENGEN VORTEIL 40%
  billiger! 1 Becher 1,99 ab 2 Becher je 1 19“. Preise sind zerlegt („1 19“ = 1,19 €), die Reihenfolge ist durch
  das Layout teils durcheinander, deshalb ist eine Auswertung per Text-KI nötig, Regex reicht nicht.
- `pageTitle`: echte Gültigkeit „Do., 19.11.26 - Mi., 02.12.26“ (die API sagt 17.11.)
- `enrichments.chunkUrls`: fertige URLs inkl. Token für die PageX-Y.json
- `aws.url` + `aws.policy`: Basis-URL und Token für Seitenbilder (`Pages/{n}/Normal.jpg` bzw. `Zoom.jpg`, ungeprüft)
- `modules.hasDownloadPdf: true`: PDF-Download vorhanden (Alternative)
- Parser: `ipaper.parse_viewer_html()`, Fixture: `spar_ipaper_viewer.html`

**PDF-Download** ✅: `https://cdn.ipaper.io/iPaper/Papers/{paperGuid}/Download.pdf?…&token=…&expires=…`
(NÖ KW47: 25 Seiten, 21 MB). Mit `pdfplumber` bekommt man jedes Wort mit Position, Schriftgröße und Schriftart:
- Produktname: Schriftgröße ~11, Beschreibung ~8
- Preis: Euro groß (~39), Cent daneben kleiner (~23), z. B. `1` + `19`
- Aktionstext: „MENGEN VORTEIL“ (16), „40% billiger!“, „1 Becher 1,99 / ab 2 Becher je“ (8)
- Achtung: Die Seitennummerierung im PDF ist gegenüber `pageTexts` um 1 verschoben (Cottage Cheese: pageTexts[12], PDF-Seite 14)

**Auswertung ohne KI: `scraper/aktionen/flugblatt_pdf.py`** (`python -m aktionen.flugblatt_pdf datei.pdf [seiten]`)
1. Rollen über die **Schriftart** (Spar): `MuseoSansCond-900` = Produktname, `-500` = Beschreibung,
   `MuseoSansRounded-900` / `TrueNorth3DBlack` = Preis + Badges, `MuseoSansRounded-700` = Bedingung
2. Preise = große Euro-Ziffern + kleinere Cent rechts daneben (einzeln gesetzte Ziffern werden verbunden)
3. „Zusätzlich -25%“, „Mit %-Aktion“, „SPAR-App-Gutschein“ über einem Preis → Zusatzpreis
4. Hauptpreis → Produktname: globale Zuordnung nach Abstand, Strafe wenn der Preis links vom Namen steht,
   **Grundpreis-Kontrolle**: „400-g-Becher (= per kg 1,98)“ ergibt 0,79 €. Passt der Preis, gibt es einen Bonus,
   sonst eine Strafe. Das löst die meisten Verwechslungen bei dicht stehenden Produkten.
5. Bedingungen („statt 2,89“, „1 Becher 1,99 ab 2 Becher je“) und Badges („2+1 GRATIS“, „-40%“) → nächster Preis

Stand 20.11.2026, NÖ KW47: 193 Angebote auf 22 Seiten. Die Seiten 7, 9, 11, 12, 14, 15 sind händisch geprüft und
**alle richtig** (Tests in `tests/test_flugblatt_pdf.py`). Stichproben auf anderen Seiten zeigen noch Fehler, z. B.
S. 8 (Bio-Eier: der Fr/Sa-Preis landet bei Bio-Orange) und S. 17 (Titel in gesperrter Schrift wie „R a d i e r e“).
Geschätzte Gesamtgenauigkeit: 85–90 %. Für die Fitness-Auswahl reicht das als Start, weil die Nährwerte-Abfrage
falsche Zuordnungen zusätzlich auffallen lässt.

**Einschränkung:** In NÖ KW47, Seiten 1–25, sind nur rund 40 Produkte verlinkt, fast nur **Non-Food**
(Glühwein, Bettwäsche, Haushaltsgeräte). Lebensmittel, die nur im Markt verkauft werden, z. B. NÖM Cottage
Cheese, haben **keinen** Link. Für Lebensmittel-Aktionen müssen wir also die **Seitenbilder** auswerten
(KI/Bilderkennung) und die Produkte per Such-API mit Spar-Artikeln abgleichen.

Sonstige Endpunkte:
- `/api/data/p/{productNumber}` liefert nur CMS-Inhalt (`{"story":null}`) und ist irrelevant
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

### Ergebnis: So läuft Spar jetzt (ohne Shop und ohne KI)

Getestet 20.11.2026 von einer Heim-IP: `www.interspar.at/api/*` ist **gesperrt** (Cloudflare 403), auch für die
Flugblatt-Liste. `flugblatt.interspar.at` und `cdn.ipaper.io` sind **offen**.

1. Viewer-URL aus Region + ISO-KW bauen: `https://flugblatt.interspar.at/{gruppe}/{region}_kw{KW}/`
   (`aktionen/spar_flugblatt.py`). Gruppe ist meist gleich der Region, Burgenland hat Nord/Süd.
   Die aktuelle KW und bis zu 3 Wochen zurück probieren, Gültigkeit aus `pageTitle` prüfen.
2. PDF: `POST {viewer}GetPDF.ashx` mit `pageNumbers=` → 302 → Location per **GET** laden (POST-Redirect ergibt 405)
3. Angebote: `aktionen/flugblatt_pdf.py`
4. Fitness: `aktionen/fitness.py`. Kategorie über Stichwörter, Nährwerte aus einer Tabelle typischer Werte.
   Open Food Facts liefert für Flugblatt-Produkte keine EAN, und die Suche war beim Test überlastet (503),
   deshalb wird es für den Normalbetrieb nicht verwendet.

## Lidl ✅

Getestet 20.11.2026, von Cloud- und Heim-IP aus ohne Sperre erreichbar.

**Quelle: Angebotsseiten auf lidl.at.** Auf der Startseite stehen Links wie `/c/store/aktion/a10107111` oder
`/c/store/frische-angebote/a10107118`. Die Nummern ändern sich wöchentlich, deshalb werden sie jedes Mal von der Startseite gelesen.
Jedes Produkt steckt als JSON im HTML-Attribut `data-grid-data`:

| Feld | Beispiel |
|---|---|
| `fullTitle` | „Nixe Thunfischfilets“ |
| `category` | `Food`, `F+V` (Obst & Gemüse), `NonFood` |
| `price.price` / `price.oldPrice` | 1.11 / 1.69 |
| `price.packaging.text` | „Je 4x 185 g“, „Je kg“, „Bei 2 Stk. je 400 g (Einzeln = 8.99)“ |
| `price.basePrice.text` | „1 kg = 6.47“ |
| `price.discount.discountText` | „-34%“ |
| `lidlPlus[].price.price` | Lidl-Plus-Preis |
| `storeStartDate` / `storeEndDate` | Unix-Zeit (Gültigkeit, oft nur Mo–Mi oder Do–Sa) |
| `image`, `canonicalUrl` | Produktbild, Produktseite |
| `regions` | `[1, 2, 3]` = ganz Österreich |

Ergebnis KW 47: 140 Lebensmittel-Aktionen, davon 10 fitnessrelevant.

**Flugblatt-Schnittstelle** (`endpoints.leaflets.schwarz/v4/flyer?flyer_identifier=…&region_id=0&region_code=0`,
Übersicht `v4/overview?client_locale=lidl%2Fde-AT&region_id=0&store_id=0`) liefert Seiten mit Bildern, PDF-Link
und Hotspots. Strukturierte `products` gibt es dort aber **nur für Non-Food** (113 von 119), deshalb wird sie nicht genutzt.

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
