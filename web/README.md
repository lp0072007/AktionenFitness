# Web

Statische Website ohne Build-Schritt: `index.html`, `style.css`, `app.js`.

## Ansehen

Zuerst einmal die Daten erzeugen (siehe unten, `python -m aktionen.export`). Die Daten und Bilder sind
nicht im Git, weil sie sich jede Woche ändern.


`index.html` einfach im Browser öffnen (Doppelklick). Oder mit lokalem Server:

```bash
cd web
python -m http.server 8000
```

Dann <http://localhost:8000> öffnen.

## Daten aktualisieren

```bash
cd scraper
python -m aktionen.export                    # Niederösterreich, Wien, Steiermark
python -m aktionen.export --alle             # alle 11 Spar-Regionen (dauert einige Minuten)
```

Das schreibt `web/data/angebote.json` und `web/data/angebote.js` (gleicher Inhalt; die `.js`-Variante
funktioniert auch beim Öffnen per Doppelklick, wo der Browser `fetch()` auf lokale Dateien blockiert).

## Flugblatt-Ausschnitte

Der Export schneidet für jedes Angebot den passenden Bereich aus dem Flugblatt aus (`web/data/bilder/`).
Diese Bilder sind **nicht im Git** (Bildrechte beim Händler). Nach dem Klonen einmal
`python -m aktionen.export` ausführen, sonst zeigt die Website die Karten ohne Bild.
Seit Neuem für **alle** Spar-Aktionen (nicht nur Fitness), damit „Alle Aktionen“ überall Bilder hat: ca. +10 s und
~10 MB pro Region. `--nur-fitness-bilder` schneidet nur die Fitness-Produkte aus, `--ohne-bilder` schaltet es ganz ab.
Der Ausschnitt richtet sich nach dem Produktnamen (Foto darüber oder daneben, fremde Namen bleiben draußen).
Qualität messen: `python -m aktionen.ausschnitte_pruefen ../data/spar_wien_kw47.pdf -v` (KW 47: 20 % → 7 % schlechte).

## Einkaufsliste abgleichen (`einkauf.html`)

Produkt eintippen + **Enter** → erscheint als eigener Punkt in „Deine Liste“ (mit Kreis zum Abhaken → durchgestrichen,
✕ zum Löschen; alles im Browser gespeichert). Mehrere Zeilen einfügen oder „Skyr, Topfen“ ergibt mehrere Punkte.
Mengen („2x“, „500g“, „1,5 kg“, „½ kg“, „10er“) werden erkannt, Klammern sind Notizen, Eigenschaften wie „light“ oder
„mager“ sind optional. Jeder Punkt wird mit **allen** aktuellen Aktionen abgeglichen (Spar-Region, Lidl, Hofer, Penny,
Billa, dm; Daten: `data/aktionen.js`) → Empfehlung, günstigste Aufteilung auf Geschäfte, falsche Treffer abwählbar.
Logik: `abgleich.js`, Tests: `node --test` im Ordner `web`.
**Testliste:** `tests/testliste/erwartet.mjs` (56 typische Einträge, was gefunden werden muss / nicht darf) gegen
eingefrorene echte Aktionen (`tests/testliste/angebote.json`). Bericht mit Trefferquote: `node tests/testliste.test.mjs --bericht`.
Fällt beim Einkaufen ein Fehltreffer auf, als neuen Fall eintragen.

## Funktionen

- **Startseite:** Aktionen durchstöbern, umschaltbar zwischen „💪 Fitness“ (Auswahl mit Nährwerten) und „🏷️ Alle Aktionen“.
  Suche, Filter nach Geschäft, Sortierung nach Kilopreis, Rabatt oder Preis. Beim Scrollen
  werden automatisch die nächsten 60 Karten nachgeladen; Bilder laden erst, wenn man hinscrollt.
- **Einkaufsliste als Seitenleiste** (🛒 oben rechts): fährt von rechts herein, Hintergrund wird dunkler, am Handy
  ganzer Bildschirm; schließen mit ✕, Esc oder Klick daneben. Produkte eintippen + Enter oder „+ Liste“ auf einer Karte.
  Jeder Punkt wird automatisch mit allen Aktionen abgeglichen; darunter steht, wo was in Aktion ist und was es zusammen kostet.
  Direktlink: `index.html#liste`. Die Liste ist dieselbe wie auf `einkauf.html` (gemeinsam: `liste.js`).
- **Preisverlauf:** Jeder Export speichert alle Preise mit Datum (`data/preisverlauf.db`, SQLite, nicht im Git).
  Die Karten zeigen dann eine Mini-Kurve und z. B. „🔥 Tiefster Preis seit 10.10.“ oder „📉 Am 24.10. schon 0,99 €“.
  Der Verlauf füllt sich mit jedem Export (am besten jede Woche). Abfragen: `python -m aktionen.verlauf skyr`.
- Bildausschnitt aus dem Flugblatt auf jeder Karte (antippen zum Vergrößern), Gültigkeit auf jeder Karte
- **Merkliste (⭐):** Produkte, die du regelmäßig kaufst – per ☆ auf einer Karte oder „Bearbeiten“. Oben auf der
  Startseite steht dann, was davon gerade wo in Aktion ist; antippen zeigt die passenden Angebote.
- **App fürs Handy (PWA):** über http(s) geöffnet lässt sich die Seite installieren und funktioniert offline
  (`manifest.webmanifest`, `sw.js`). Per Doppelklick (file://) gibt es keinen Offline-Modus.
- **Online stellen:** siehe `docs/ONLINE_STELLEN.md` (GitHub Pages + automatischer Abruf Mo/Do).
- Hell/Dunkel nach Systemeinstellung, für Handy optimiert

## Kopieren für die Notizen-App

In der Seitenleiste unter „📋 Liste für die Notizen-App“ Geschäft(e) wählen → nur deren Produkte (optional plus Produkte
ohne Aktion) werden als `* 12x Eier`-Liste kopiert. Bei mehreren Geschäften mit Überschrift pro Geschäft.

## Impressum, Datenschutz, Sicherheit

`impressum.html` und `datenschutz.html` sind Vorlagen: vor dem Veröffentlichen die [Platzhalter] ausfüllen.
Sicherheitsmaßnahmen: `docs/SICHERHEIT.md`.

## Hosting

Weil alles statisch ist, reicht GitHub Pages. Anleitung: `docs/ONLINE_STELLEN.md`.
