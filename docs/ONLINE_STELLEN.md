# Website online stellen (GitHub Pages + automatische Aktualisierung)

Vorbereitet ist alles im Repository: `.github/workflows/aktualisieren.yml` ruft **jeden Morgen** (04:17 UTC) die
Aktionen ab, speichert den Preisverlauf und veröffentlicht den Ordner `web/` auf GitHub Pages.

**Sparsamer Lauf** (`python -m aktionen.export --alt …`, ca. 30 s statt 20 min): Lidl, Hofer, Penny, Billa und MPreis
werden jedes Mal geholt (je wenige Sekunden). Spar nur, wenn es ein **neues Flugblatt** gibt (sonst kein 20-MB-PDF),
dm etwa **einmal pro Woche** (Dauerpreise, bremst bei vielen Anfragen). Fällt ein Geschäft aus oder liefert es
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

## Flugblatt-Ausschnitte (Bildrechte)

Standardmäßig veröffentlicht der Workflow **ohne** Spar-Flugblatt-Ausschnitte (`--ohne-bilder`), weil die Bildrechte
bei Spar liegen. Produktbilder der anderen Händler werden direkt von deren Servern geladen (nicht kopiert).
Wenn du die Ausschnitte trotzdem veröffentlichen willst (nur mit Erlaubnis!): *Settings* → *Secrets and variables* →
*Actions* → *Variables* → `FLUGBLATT_BILDER` = `ja`.

## Bekannte Grenzen

- **Hofer/dm aus der Cloud:** Manche Händler blockieren Anfragen von Rechenzentren (GitHub). Dann bleibt der letzte
  Stand dieser Kette stehen (Warnung im Lauf). Die Website zeigt unten, wann jedes Geschäft zuletzt neu geladen wurde.
- **Preisverlauf und letzter Stand** liegen im Branch `daten` (`preisverlauf.db`, `stand/`). Den Branch nicht löschen, sonst fängt der Verlauf
  von vorne an. Lokal kannst du ihn holen: `git fetch origin daten && git show FETCH_HEAD:preisverlauf.db > data/preisverlauf.db`.
- **Zeitplan ändern:** in `aktualisieren.yml` die Zeile `cron` (UTC). GitHub startet geplante Läufe manchmal mit
  Verspätung.

## Am Handy installieren

- **Android (Chrome):** Seite öffnen → Menü ⋮ → „App installieren“ bzw. „Zum Startbildschirm hinzufügen“.
- **iPhone (Safari):** Teilen-Symbol → „Zum Home-Bildschirm“.
Die Einkaufsliste, Merkliste und Häkchen sind pro Gerät gespeichert (nicht zwischen Handy und PC synchronisiert).
