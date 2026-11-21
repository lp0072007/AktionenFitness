# Website online stellen (GitHub Pages + automatische Aktualisierung)

Vorbereitet ist alles im Repository: `.github/workflows/aktualisieren.yml` ruft Montag und Donnerstag früh die
Aktionen ab, speichert den Preisverlauf und veröffentlicht den Ordner `web/` auf GitHub Pages. Die Website ist eine
installierbare App (PWA): am Handy „Zum Startbildschirm hinzufügen“, funktioniert danach auch ohne Netz.

## Was du einmalig tun musst

1. **Branch nach `main` bringen.** Zeitgesteuerte Workflows laufen nur im Standard-Branch. Also den Branch
   `claude/affectionate-euler-5s6yjv` per Pull Request in `main` mergen.
2. **Repository öffentlich oder GitHub Pro.** GitHub Pages für private Repositories gibt es nur mit einem bezahlten
   Plan. Für ein öffentliches Repository ist es kostenlos. Achtung: Dann ist auch der Code öffentlich.
3. **Pages einschalten:** Repository → *Settings* → *Pages* → *Source*: **GitHub Actions**.
4. **Ersten Lauf starten:** *Actions* → „Aktionen aktualisieren“ → *Run workflow*. Nach ca. 10–20 Minuten steht die
   Adresse (`https://<benutzer>.github.io/AktionenFitness/`) im Lauf unter „veroeffentlichen“.
5. **Impressum und Datenschutz ausfüllen** (`web/impressum.html`, `web/datenschutz.html`, Platzhalter in [ ]),
   im Datenschutz bei „Hosting“ GitHub Pages eintragen. **Vor** dem Veröffentlichen.

## Flugblatt-Ausschnitte (Bildrechte)

Standardmäßig veröffentlicht der Workflow **ohne** Spar-Flugblatt-Ausschnitte (`--ohne-bilder`), weil die Bildrechte
bei Spar liegen. Produktbilder der anderen Händler werden direkt von deren Servern geladen (nicht kopiert).
Wenn du die Ausschnitte trotzdem veröffentlichen willst (nur mit Erlaubnis!): *Settings* → *Secrets and variables* →
*Actions* → *Variables* → `FLUGBLATT_BILDER` = `ja`.

## Bekannte Grenzen

- **Hofer/dm aus der Cloud:** Manche Händler blockieren Anfragen von Rechenzentren (GitHub). Dann fehlt die Kette in
  diesem Lauf, der Rest wird trotzdem veröffentlicht. Im Protokoll des Laufs steht „übersprungen“.
- **Preisverlauf** liegt im Branch `daten` (`preisverlauf.db`). Den Branch nicht löschen, sonst fängt der Verlauf
  von vorne an. Lokal kannst du ihn holen: `git fetch origin daten && git show FETCH_HEAD:preisverlauf.db > data/preisverlauf.db`.
- **Zeitplan ändern:** in `aktualisieren.yml` die Zeile `cron` (UTC). GitHub startet geplante Läufe manchmal mit
  Verspätung.

## Am Handy installieren

- **Android (Chrome):** Seite öffnen → Menü ⋮ → „App installieren“ bzw. „Zum Startbildschirm hinzufügen“.
- **iPhone (Safari):** Teilen-Symbol → „Zum Home-Bildschirm“.
Die Einkaufsliste, Merkliste und Häkchen sind pro Gerät gespeichert (nicht zwischen Handy und PC synchronisiert).
