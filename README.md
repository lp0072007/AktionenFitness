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
pip install -e ".[dev]"
pytest
python -m aktionen spar --query skyr
```

## Status

Phase 1: Datenquellen anbinden, angefangen mit **Spar**. Siehe [docs/DATENQUELLEN.md](docs/DATENQUELLEN.md).
