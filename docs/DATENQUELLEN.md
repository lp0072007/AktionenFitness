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

## Hofer ✅

`www.hofer.at` sperrt Anfragen mit **vorgetäuschter Browser-Kennung** (Akamai „Access Denied“, 403). Mit der ehrlichen
Programm-Kennung (`AktionenFitness/0.1`) geht es von Heim- und Cloud-IP aus (getestet 20.11.2026).

- Übersicht `https://www.hofer.at/angebote` verlinkt pro Starttag eine Seite `/angebote/2026-11-19`
  (Abschnitte „ANGEBOTE AB MONTAG, 16.11.“ usw.).
- Serverseitig gerendertes HTML, Kachel `<div id="product-tile-000000000000744520">` mit
  `product-tile__brandname`, `product-tile__name`, `product-tile__unit-of-measurement` („400 ml per Stück“,
  „0,2 KG/ATG per Stück“), `product-tile__comparison-price` („(€ 3,98/1 l)“), `base-price__regular` /
  `base-price__discounted`, Badges (`base-label`: „Tiefpreisaktion“, „Verfügbar seit 16.11.2026“).
- Parser: `aktionen/stores/hofer.py`, Fixture `hofer_kacheln.html`
- Noch nicht geprüft: Struktur der Tagesseiten (vermutlich gleiche Kacheln) und ob dort alle Produkte stehen
  oder per „Mehr anzeigen“ nachgeladen werden (`asl.api.hofer.at` = Hofers API, im HTML als `API_AZURE_BASE_URL`).
- Flugblatt: `katalog.hofer.at` (Publitas). Von überall erreichbar, Hotspots enthalten aber nur Links, keine Produkte.
  PDF unter `config.downloadPdfUrl` (view.publitas.com), das wäre ein möglicher Plan B wie bei Spar.

## Penny ✅

Rewe-Plattform (wie Billa), von Heim- und Cloud-IP erreichbar (20.11.2026).

    GET https://www.penny.at/api/product-discovery/categories/alle-angebote-99000000/products?page=0&pageSize=100

`{"total": 591, "results": [...]}`: `name`, `brand.name`, `amount` + `volumeLabelShort` (g/kg/ml/liter/stk),
`weightArticle` (Kilo-Ware), `price.regular.value` (Cent), `price.regular.promotionText`/`promotionQuantity`
(„ab 2 Becher“), `price.crossed` (Streichpreis), `price.discountPercentage`, `price.validityStart/End`, `images[]`,
`slug` (→ /produkte/{slug}), `parentCategories` (Kühlwaren, Haushalt, Non-Food …).
Die Seite /angebote enthält dieselben Daten zusätzlich als `__NUXT_DATA__` (nur die ersten 30).
Parser: `aktionen/stores/penny.py`. KW 47: 440 Lebensmittel-Aktionen (ohne Haushalt/Non-Food/Pflege/Haustier), 30 fitnessrelevant.

## Billa ✅

Gleiche Rewe-Plattform wie Penny, aber über den Online-Shop (`shop.billa.at`). Von Heim- und Cloud-IP erreichbar.

    GET https://shop.billa.at/api/product-discovery/categories/kuehlwaren-15416/products?inPromotion=true&sortBy=relevance&page=0&pageSize=100

- Kategorien stehen auf `https://shop.billa.at/aktionen` als `product-group-<slug>-{"inPromotion":"true",…}`
  (Fallback-Liste in `aktionen/stores/billa.py`).
- Preis: `regular.value` = Aktionspreis, `standard.value` = Normalpreis, `crossed`, `promotionText` („Bei 3 Becher je“).
- **Keine Gültigkeitsdaten** (aktuelle Shop-Aktionen). Die Website zeigt „aktuell im BILLA-Shop (Stand …)“.
- KW 47: 1409 Lebensmittel-Aktionen, 83 fitnessrelevant.
- Billa und Penny liefern einen Kategoriepfad („Tiefkühl > Tiefkühlgerichte > Reis & Pasta“). Damit werden
  Fertiggerichte, Pizza, Eis, Snacks usw. aus der Fitness-Auswertung ausgeschlossen (`fitness._PFAD_AUSSCHLUSS`).
- Gemeinsamer Parser für Penny und Billa: `aktionen/stores/rewe.py`.

## dm ✅ (Dauerpreise)

dm macht kaum Aktionen (1 von 200 Proteinprodukten mit Streichpreis). Eingebunden als **Dauerpreis-Vergleich**.

    GET https://product-search.services.dmtech.com/at/search/crawl?query=tofu&pageSize=100&currentPage=0

`brandName`, `title` („Direktsaft Rote Bete, 1 l“), `dan`, `tileData.price.price.current.value` („2,00 €“),
`…previous.value` (selten), `tileData.price.tileInfos` („1 l (2,00 € je 1 l)“), `tileData.self`, `tileData.images`,
`tileData.trackingData.categories` („Gemüsesäfte & Ingwershots“, „Duschgel“ …, damit werden Drogerieartikel ausgeschlossen).
**Rate-Limit:** Bei schnellen Anfragen kommt 429. Deshalb 3 s Pause und nur 100 Treffer pro Suchbegriff
(Liste in `aktionen/stores/dm.py`). Bei 429 wird automatisch gewartet (`Retry-After`). KW 47: 683 Produkte, ~150 fitnessrelevant.

## MPreis ✅ (eingebunden 24.11.2026, `aktionen/stores/mpreis.py`)

Die Website (Vue-App) ist von Algolia auf **Typesense** umgestiegen (Komponenten heißen noch „algoliaProductGrid“).
Abfrage über einen Proxy von MPreis, **ohne API-Schlüssel**, per POST mit JSON:

    POST https://data-hub.mpreis.at/typesense-proxy/multi_search
    {"searches":[{"collection":"products","q":"*",
      "filter_by":"available:true && priceMissing:false && $product_store_data(storeId:=8450 && sitePrice.isInFlyer:true)",
      "include_fields":"id,name,image,categories,mixins.productCustomAttributes.packagingUnit,
                        mixins.markantAttributes.data.description.brandName,
                        $product_store_data(productId,storeId,sitePrice,strategy:nest_array)",
      "per_page":250,"page":1}]}

- **Sammlungen:** `products` (Stammdaten) und `product_store_data` (Preis/Verfügbarkeit **pro Markt**), verknüpft per Join
  `$product_store_data(…)`. Ohne Join fehlt der Preis; `product_store_data` allein lehnt der Proxy ab (HTTP 400).
- **Markt:** `storeId`, Standardmarkt der Website **8450** (daher der alte Index-Name). Preise gelten pro Markt –
  ob sie sich zwischen Märkten unterscheiden, ist noch nicht geprüft.
- **Preisfelder** (`sitePrice`): `effective` (aktuell), `original` (Normalpreis), `base` (Grundpreis/kg bzw. l),
  `promotionType`, `wholesale.minQuantity` (= ab Menge), `isInFlyer` (im Flugblatt).
- **Produktfelder:** `name`, Marke `mixins.markantAttributes.data.description.brandName`,
  Packung `mixins.productCustomAttributes.packagingUnit` („250g“, „500ml“), `weightDependent` (Kilo-Ware),
  `categories` (z. B. „Topfen > Milch & Eier > Lebensmittel“), `image` (Cloudinary).
- **Umfang (Markt 8450):** 13.013 Produkte **mit Normalpreis** (ganzes Sortiment → auch für Gesamtpreis-Vergleich),
  davon Aktionstypen: Preisgesenkt 623, Immer günstig 490, In der Menge billiger 464, 1+1 gratis 255,
  Dauertiefpreis 98. Im Flugblatt: 307, davon Lebensmittel 211.
- **Keine Gültigkeitsdaten** in den Preisen (wie Billa: aktueller Stand).
- Filter-Tipp: `promotionType:!=""` greift nicht, stattdessen `sitePrice.promotionType:=[…]` oder `isInFlyer:true`.
- „Immer günstig“ und „Dauertiefpreis“ sind Dauerpreise, keine Aktionen.
- **Umsetzung:** Lebensmittel + Getränke mit Preisgesenkt / In der Menge billiger / 1+1 gratis oder im Flugblatt
  (~1.200 Aktionen, 5 Anfragen, ~3 s). „Preisgesenkt“ ohne niedrigeren Preis und nicht im Flugblatt wird weggelassen
  (dauerhaft gesenkt). „1+1 gratis“-Label aus `discounts` (forQuantity 3 = 2+1). Eigenschaften `VGN`/`BIO` → Merkmale.
  Produktlink `https://www.mpreis.at/shop/p/{id}` (leitet weiter). Eigenmarken: M, M-BIO, Jeden Tag, Therese Mölk.
- **Noch ungenutzt:** echte Nährwerte (`mixins.markantAttributes.data.nutrient`: kcal, Eiweiß … pro 100 g) und Zutaten.
- Produktdetails zusätzlich über `POST https://www.mpreis.at/api/products` mit `{productIds, marketId}`.
- Nutzungsbedingungen vor einem öffentlichen Start prüfen (interne Schnittstelle der Website, keine offizielle API).

## ADEG ⚠️ (noch nicht eingebunden)

Das Flugblatt gibt es pro Markt (selbstständige Kaufleute). `adeg.at/flugblatt-aktionen/adeg-flugblatt` lädt es erst nach
der Marktauswahl per JavaScript. Für die Einbindung braucht es eine DevTools-Erkundung (welche Anfrage liefert das Flugblatt?).

## BIPA ➖ (nicht geplant)

Drogerie, kaum Lebensmittel, deshalb für Fitness-Angebote nicht relevant.

## Weitere Ketten (für später, laut heissepreise)

| Kette | Endpunkt (intern, ungeprüft) |
|---|---|
| Billa | `https://shop.billa.at/api/product-discovery/categories/{id}/products?pageSize=500&page={n}` |
| Penny | `https://www.penny.at/api/products?page={n}&pageSize={n}` |
| Lidl | `https://www.lidl.at/p/api/gridboxes/AT/de/?max={n}` |
| Hofer | über roksh.at (`https://www.roksh.at/hofer/angebot/`) |
| MPreis | ~~Algolia-Suchindex (`prod_mpreis_8450`)~~ veraltet → Typesense, siehe Abschnitt MPreis |
| ADEG | kein Shop → Flugblatt-PDF + KI-Auswertung |

Alternative Rohdaten: heisse-preise.io stellt `data/latest-canonical.json` bereit (alle Ketten, aber keine
Aktionszeiträume und kein offizielles API).

## Nährwerte (eingebaut 25.11.2026, `aktionen/naehrwerte.py`)

Nur für fitnessrelevante Angebote, jedes Produkt einmal (Zwischenspeicher `data/naehrwerte.json`, im Branch `daten`).
Nur Werte **wie verkauft** (unzubereitet) – gekochter Reis (155 statt 355 kcal) würde Protein/€ verfälschen.
Plausibilitätsprüfung: Werte im möglichen Bereich, kcal ≈ 4·Eiweiß + 4·KH + 9·Fett (±40 %).

| Kette | Quelle | Abdeckung Fitness-Angebote (25.11.2026) |
|---|---|---|
| Billa | `GET shop.billa.at/api/product-discovery/products/<sku>` → `additionalInformation[].foodInformation.nutritionInfos` | 56/57 |
| MPreis | in der Suche: `mixins.markantAttributes.data.nutrient` (+ `gtin` → Open Food Facts) | 128/145 |
| Lidl | keine Werte; EAN im JSON-LD der Produktseite (`gtin13`) → Open Food Facts | 14/29 |
| Penny | weder Werte noch EAN (Schnittstelle und Produktseite geprüft) | Richtwerte |
| Hofer | Seite zeigt Nährwerte nur aus eingebetteten Daten (`multiInformations`), bei 0/24 Stichproben befüllt; keine EAN | Richtwerte |

Open Food Facts: `GET world.openfoodfacts.org/api/v2/product/<ean>.json?fields=nutriments`, eigene Kennung im
User-Agent, Lizenz ODbL → Hinweis auf der Website.

## Nährwerte (frühere Notizen)

- [Open Food Facts](https://world.openfoodfacts.org/data): kostenlos, Abfrage per EAN:
  `https://world.openfoodfacts.org/api/v2/product/{ean}.json`
- Manuelle Basisliste für Generika (Magertopfen, Hühnerbrust, Haferflocken, …)

## robots.txt (geprüft 24.11.2026)

| Host | Was wir abrufen | robots.txt | |
|---|---|---|---|
| shop.billa.at, www.penny.at | `/api/product-discovery/…` | nur Sitemap, keine Sperren | ✅ |
| www.lidl.at | `/c/store/…` | gesperrt: `/q/search`, `/1*`–`/9*`, `/cc.js` | ✅ |
| www.hofer.at | `/angebote`, `/angebote/<datum>` | gesperrt: `/tools`, `/*?q=` (Datei nur im Browser abrufbar) | ✅ |
| data-hub.mpreis.at | `/typesense-proxy/multi_search` | keine robots.txt (404); www.mpreis.at sperrt nur `/search/`, Filter | ✅ |
| flugblatt.interspar.at | Flugblattseite ✅, PDF über `GetPDF.ashx` | `Disallow: /*.ashx` | ❌ PDF-Download ausgeschlossen – Anfrage bei Spar läuft |
| product-search.services.dmtech.com | `/at/search/crawl` | `Disallow: /` | ❌ → dm nicht mehr automatisch (`--mit-dm`) |
| www.interspar.at | `/api/listing/<abteilung>?p=<seite>` (Sortiment) | nur `/-global/` gesperrt | ⏳ nur lokal, bis Spar zustimmt; Cloudflare sperrt Python-Abrufe (403), `curl` kommt durch – nicht umgehen |
| www.gurkerl.at | – | nur `/regal/*` gesperrt | ❌ AGB 1.1 (d): Inhalte „durch automatisierte Mittel“ zu erlangen oder zu kopieren nur mit schriftlicher Zustimmung |

## Sortiment / Normalpreise (eingebaut 25.11.2026, `aktionen/sortiment.py`)

`python -m aktionen.sortiment` lädt das ganze Lebensmittel-Sortiment mit aktuellen Regalpreisen nach
`web/data/sortiment.js` (nicht im Git). Nur die Vergleichsseite (`einkauf.html`) lädt die Datei: „Alles in einem
Geschäft“ und Normalpreise für Produkte ohne Aktion (`Abgleich.mitNormalpreisen`).

| Markt | Quelle | Umfang (25.11.2026) | Dauer |
|---|---|---|---|
| Billa | wie `billa.py`, Kategorien ohne `inPromotion` | 9 546 | ca. 2 min |
| MPreis | wie `mpreis.py`, Filter ohne Aktionsarten | 9 922 | ca. 1 min |
| Spar | `www.interspar.at/api/listing/<abteilung>?p=<seite>`, 32 je Seite, 7 Abteilungen | ca. 9 000 | ca. 5 min |

Spar: Packungsgröße aus Preis ÷ Grundpreis (`referencePrice`), Aktionspreis = `currentPrice` mit `originalPrice`.
Auf GitHub läuft das Sortiment ohne Spar (`--ohne-spar`, bis die Variable `SPAR = "ja"` gesetzt ist).

Geprüft und **nicht** möglich:
- **Lidl, Penny**: kein Sortiment mit Normalpreisen online. Penny-Kategorien (`/api/product-discovery/categories/…`)
  enthalten nur Produkte mit Gültigkeitsdatum, also nur Aktionen (12 Kategorien stichprobenartig geprüft).
- **Hofer**: sperrte am 25.11.2026 diese Verbindung komplett (Akamai 403, auch `robots.txt`). Nicht umgehen.
- **Gurkerl**: AGB verbieten es (siehe Tabelle oben). Nur mit schriftlicher Erlaubnis (office@gurkerl.at).
- **dm**: robots.txt verbietet die Produktsuche.
