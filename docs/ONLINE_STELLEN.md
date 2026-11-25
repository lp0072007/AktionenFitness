# Website online stellen (GitHub Pages + automatische Aktualisierung)

Vorbereitet ist alles im Repository: `.github/workflows/aktualisieren.yml` ruft **jeden Morgen** die
Aktionen ab, speichert den Preisverlauf und veröffentlicht den Ordner `web/` auf GitHub Pages.

**Sparsamer Lauf** (`python -m aktionen.export --alt …`, ca. 30 s statt 20 min): Lidl, Hofer, Penny, Billa und MPreis
werden jedes Mal geholt (je wenige Sekunden). **Spar ist standardmäßig aus**, weil die robots.txt von Spar den
PDF-Abruf ausschließt (Anfrage bei Spar läuft). Mit Erlaubnis: Variable `SPAR` = `ja` – dann nur bei **neuem Flugblatt**.
**dm wird nicht automatisch geladen:** die dm-Produktsuche verbietet automatische Zugriffe in ihrer robots.txt
(`Disallow: /`). Lokal zum Testen: `python -m aktionen.export --mit-dm`. Fällt ein Geschäft aus oder liefert es
0 Angebote, bleibt sein **letzter Stand** stehen und der Lauf zeigt eine **Warnung** (gelbes Dreieck im Actions-Tab).
Letzter Stand und Preisverlauf liegen im Branch `daten`. „Alles neu laden“: *Run workflow* → Häkchen „alles“. Die Website ist eine
installierbare App (PWA): am Handy „Zum Startbildschirm hinzufügen“, funktioniert danach auch ohne Netz.

## Was du einmalig tun musst

1. **Standard-Branch:** Zeitgesteuerte Workflows laufen nur im Standard-Branch. Das ist hier bereits
   `claude/affectionate-euler-5s6yjv` – nichts zu tun, solange das so bleibt.
2. **Repository öffentlich oder GitHub Pro.** GitHub Pages für private Repositories gibt es nur mit einem bezahlten
   Plan. Für ein öffentliches Repository ist es kostenlos. Achtung: Dann ist auch der Code öffentlich.
3. **Pages einschalten:** Repository → *Settings* → *Pages* → *Source*: **GitHub Actions**. Danach
   *Settings* → *Secrets and variables* → *Actions* → *Variables* → `VEROEFFENTLICHEN` = `ja`. Ohne diese Variable
   holt der Workflow nur die Daten und veröffentlicht nichts (kein Fehler).
4. **Ersten Lauf starten:** *Actions* → „Aktionen aktualisieren“ → *Run workflow*. Nach wenigen Minuten steht die
   Adresse (`https://<benutzer>.github.io/AktionenFitness/`) im Lauf unter „veroeffentlichen“.
5. **Impressum und Datenschutz ausfüllen** (`web/impressum.html`, `web/datenschutz.html`, Platzhalter in [ ]),
   im Datenschutz bei „Hosting“ GitHub Pages eintragen. **Vor** dem Veröffentlichen.

## Pünktlicher Start mit cron-job.org (eingerichtet 25.11.2026)

GitHub startet zeitgesteuerte Läufe oft Stunden zu spät oder gar nicht (Montag 23.11.: 04:17 geplant, 14:43 gelaufen;
25.11.: gar nicht). Deshalb stößt **cron-job.org** den Lauf täglich um **05:30 (Europe/Vienna)** an. Der eigene
`cron` im Workflow (10:17 UTC) bleibt als Reserve.

- **Aufruf:** `POST https://api.github.com/repos/lp0072007/AktionenFitness/actions/workflows/aktualisieren.yml/dispatches`
- **Header:** `Authorization: Bearer <Token>`, `Accept: application/vnd.github+json`, `X-GitHub-Api-Version: 2022-11-28`
- **Body:** `{"ref":"claude/affectionate-euler-5s6yjv"}` (der Standard-Branch – bei Umbenennung hier anpassen)
- **Erfolg:** HTTP 204, danach ein neuer Lauf im Actions-Tab
- **Token:** Fine-grained Personal Access Token, nur dieses Repo, Berechtigung nur *Actions: Read and write*.
  **Läuft am 24.11.2027 ab** → vorher neuen Token erzeugen und in cron-job.org eintragen.
- **API-Version:** GitHub meldet für `2022-11-28` „Deprecation 10.03.2026, Sunset 10.03.2028“ → vor März 2028 den
  Header auf die dann aktuelle Version umstellen.
- Fehler: 401 Token/„Bearer “ falsch · 403 Berechtigung fehlt · 404 Repo nicht freigegeben/URL · 422 Branch falsch.

## Flugblatt-Ausschnitte (Bildrechte)

Standardmäßig veröffentlicht der Workflow **ohne** Spar-Flugblatt-Ausschnitte (`--ohne-bilder`), weil die Bildrechte
bei Spar liegen. Produktbilder der anderen Händler werden direkt von deren Servern geladen (nicht kopiert).
Wenn du die Ausschnitte trotzdem veröffentlichen willst (nur mit Erlaubnis!): *Settings* → *Secrets and variables* →
*Actions* → *Variables* → `FLUGBLATT_BILDER` = `ja`.

## Bekannte Grenzen

- **Hofer aus der Cloud:** Manche Händler blockieren Anfragen von Rechenzentren (GitHub). Dann bleibt der letzte
  Stand dieser Kette stehen (Warnung im Lauf). Die Website zeigt unten, wann jedes Geschäft zuletzt neu geladen wurde.
- **Preisverlauf und letzter Stand** liegen im Branch `daten` (`preisverlauf.db`, `stand/`). Den Branch nicht löschen, sonst fängt der Verlauf
  von vorne an. Lokal kannst du ihn holen: `git fetch origin daten && git show FETCH_HEAD:preisverlauf.db > data/preisverlauf.db`.
- **Zeitplan ändern:** in `aktualisieren.yml` die Zeile `cron` (UTC). GitHub startet geplante Läufe manchmal mit
  Verspätung.

## Am Handy installieren

- **Android (Chrome):** Seite öffnen → Menü ⋮ → „App installieren“ bzw. „Zum Startbildschirm hinzufügen“.
- **iPhone (Safari):** Teilen-Symbol → „Zum Home-Bildschirm“.
Die Einkaufsliste, Merkliste und Häkchen sind pro Gerät gespeichert (nicht zwischen Handy und PC synchronisiert).
