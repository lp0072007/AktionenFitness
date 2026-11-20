# AktionenFitness

Liest die Aktionen der österreichischen Supermärkte (Spar, Billa, Lidl, Hofer, …) automatisch ein,
filtert die Produkte heraus, die für Fitness-Leute interessant sind (Protein, Haferflocken, Reis, …),
und berechnet Kennzahlen wie **Gramm Protein pro Euro**. Aus den Angeboten kann man Einkaufslisten erstellen.

## Projektstruktur

```
AktionenFitness/
├── docs/
│   ├── KONZEPT.md        Idee, Features, Roadmap
│   └── DATENQUELLEN.md   Recherche: woher kommen die Daten pro Kette
├── scraper/              Python: Daten holen, vereinheitlichen, speichern
│   ├── aktionen/
│   │   ├── models.py     Einheitliches Datenmodell (Produkt / Angebot)
│   │   ├── stores/       Ein Modul pro Kette (spar.py, billa.py, …)
│   │   └── __main__.py   CLI: python -m aktionen spar
│   └── tests/            pytest + Beispiel-JSON (fixtures)
├── web/                  Website (kommt in Phase 3)
└── data/                 Lokale Rohdaten & Exporte (nicht im Git)
```

## Schnellstart (Scraper)

```bash
cd scraper
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev,pdf]"
pytest
python -m aktionen.fitness --region niederoesterreich              # Fitness-Rangliste der Woche
python -m aktionen.fitness --region wien --ziel diaet               # eiweißreich zuerst
python -m aktionen.fitness --pdf flugblatt.pdf --gruppe Kohlenhydrate
python -m aktionen.flugblatt_pdf flugblatt.pdf 14                   # alle Angebote einer Seite
```

`aktionen.fitness` sucht das aktuelle Spar-Flugblatt der Region auf flugblatt.interspar.at, lädt das PDF nach `data/`
(ca. 20 MB, wird zwischengespeichert), liest die Angebote aus und bewertet die fitnessrelevanten Produkte
(Protein pro €, kcal pro €, Protein pro 100 kcal). Der Spar-Onlineshop wird **nicht** verwendet (Cloudflare-Sperre).

## Status

**Spar, Lidl, Hofer und Penny funktionieren durchgehend.** Lidl: strukturierte Angebote von den Angebotsseiten auf lidl.at (`aktionen/stores/lidl.py`), österreichweit gültig. Spar: Flugblatt finden → PDF laden → Angebote auslesen (ohne KI) → Fitness-Rangliste. Nährwerte kommen aus einer eigenen Tabelle typischer Werte (`aktionen/fitness.py`). Siehe [docs/DATENQUELLEN.md](docs/DATENQUELLEN.md).
