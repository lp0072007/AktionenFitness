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
Diese Bilder sind **nicht im Git** (Bildrechte beim Händler, ca. 1 MB pro Region). Nach dem Klonen einmal
`python -m aktionen.export` ausführen, sonst zeigt die Website die Karten ohne Bild.
Mit `--ohne-bilder` lässt sich das abschalten.

## Funktionen

- Bildausschnitt aus dem Flugblatt auf jeder Karte (antippen zum Vergrößern)
- Hinweis „✓ Preis passt zum Grundpreis“, wenn die Zuordnung per Grundpreis bestätigt ist
- Region wählen, Suche, Ziel (Protein/€, Diät, Aufbau), Filter nach Lebensmittelgruppe
- Einkaufsliste mit Mengen, Gesamtpreis und Makros. Mengenaktionen („ab 2 Stück“) werden richtig berechnet.
  Die Liste wird im Browser gespeichert (localStorage) und lässt sich als Text kopieren.
- Hell/Dunkel nach Systemeinstellung, für Handy optimiert

## Hosting (später)

Weil alles statisch ist, reicht z. B. GitHub Pages: Ordner `web/` veröffentlichen.
