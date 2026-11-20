"""Daten für die Website exportieren: web/data/angebote.json

    python -m aktionen.export                                  # Standard-Regionen
    python -m aktionen.export --region wien --region tirol
    python -m aktionen.export --alle                           # alle 11 Spar-Regionen (dauert, je ~20 MB PDF)
    python -m aktionen.export --region niederoesterreich --pdf flugblatt.pdf
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from .ausschnitte import ausschnitte_speichern
from .fitness import DATEN_ORDNER, FitnessTreffer, fitness_angebote
from .flugblatt_pdf import FlugblattAngebot, analysiere_seite
from .spar_flugblatt import REGIONEN, aktuelles_flugblatt, pdf_herunterladen

WEB_DATEN = Path(__file__).resolve().parents[2] / "web" / "data" / "angebote.json"
BILDER_UNTERORDNER = "bilder"   # relativ zu web/data, Bilder sind nicht im Git (Rechte beim Händler)
STANDARD_REGIONEN = ["niederoesterreich", "wien", "steiermark"]

REGION_NAMEN = {
    "burgenland_nord": "Burgenland Nord", "burgenland_sued": "Burgenland Süd", "kaernten": "Kärnten",
    "niederoesterreich": "Niederösterreich", "oberoesterreich": "Oberösterreich", "osttirol": "Osttirol",
    "salzburg": "Salzburg", "steiermark": "Steiermark", "tirol": "Tirol", "vorarlberg": "Vorarlberg", "wien": "Wien",
}


def angebote_aus_pdf(pfad) -> list[FlugblattAngebot]:
    import pdfplumber

    angebote = []
    with pdfplumber.open(pfad) as pdf:
        for n, seite in enumerate(pdf.pages, start=1):
            woerter = seite.extract_words(use_text_flow=True, extra_attrs=["size", "fontname"])
            angebote += analysiere_seite(woerter, n)
    return angebote


def treffer_als_dict(t: FitnessTreffer, kette: str, region: str, i: int, bild: str | None = None) -> dict:
    a, k = t.angebot, t.kategorie
    zuordnung = {True: "geprueft", False: "unsicher", None: "unbekannt"}[a.grundpreis_ok]
    return {
        "id": f"{kette}-{region}-{a.seite}-{i}",
        "kette": kette,
        "name": a.name,
        "beschreibung": a.beschreibung,
        "seite": a.seite,
        "preis": a.preis,
        "normalpreis": a.normalpreis,
        "ab_menge": a.ab_menge,
        "zusatzpreis": a.zusatzpreis,
        "aktion": a.aktion,
        "menge": a.menge,
        "einheit": a.einheit,
        "pro_kg": a.pro_kg,
        "gramm": t.gramm,
        "kategorie": k.name,
        "gruppe": k.gruppe,
        "naehrwerte": {"kcal": k.kcal, "protein": k.protein, "kohlenhydrate": k.kohlenhydrate, "fett": k.fett},
        "protein_pro_euro": t.protein_pro_euro,
        "protein_pro_euro_zusatz": t.protein_pro_euro_zusatz,
        "kcal_pro_euro": t.kcal_pro_euro,
        "protein_pro_100kcal": t.protein_pro_100kcal,
        "zuordnung": zuordnung,   # geprueft = Preis passt zum Grundpreis im Flugblatt
        "bild": bild,             # Ausschnitt aus dem Flugblatt, relativ zu web/
    }


def region_exportieren(region: str, pdf: str | None = None, bilder_ordner: Path | None = None) -> dict:
    fb = None
    if pdf is None:
        fb = aktuelles_flugblatt(region)
        print(f"  {region}: {fb.flipbook.name} ({fb.flipbook.titel})", file=sys.stderr)
        pdf = pdf_herunterladen(fb, DATEN_ORDNER)
    angebote = angebote_aus_pdf(pdf)
    treffer = fitness_angebote(angebote)
    bilder: dict[int, str] = {}
    if bilder_ordner is not None:
        index = {id(a): i for i, a in enumerate(angebote)}
        nur = {index[id(t.angebot)] for t in treffer}
        dateien = ausschnitte_speichern(pdf, angebote, bilder_ordner / region, f"spar-{region}", nur)
        web = bilder_ordner.parent.parent  # .../web
        bilder = {i: d.relative_to(web).as_posix() for i, d in dateien.items()}
        index_treffer = {id(t): index[id(t.angebot)] for t in treffer}
    gueltig = fb.flipbook.gueltig if fb else None
    return {
        "region": region,
        "name": REGION_NAMEN.get(region, region),
        "flugblatt": fb.flipbook.name if fb else Path(pdf).name,
        "flugblatt_url": fb.viewer_url if fb else None,
        "gueltig_von": gueltig[0].isoformat() if gueltig else None,
        "gueltig_bis": gueltig[1].isoformat() if gueltig else None,
        "anzahl_angebote": len(angebote),
        "angebote": [
            treffer_als_dict(t, "spar", region, i, bilder.get(index_treffer[id(t)]) if bilder else None)
            for i, t in enumerate(treffer)
        ],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m aktionen.export")
    p.add_argument("--region", action="append", choices=sorted(REGIONEN))
    p.add_argument("--alle", action="store_true")
    p.add_argument("--pdf", help="nur mit genau einer --region")
    p.add_argument("--ziel", type=Path, default=WEB_DATEN)
    p.add_argument("--ohne-bilder", action="store_true", help="keine Flugblatt-Ausschnitte erzeugen")
    args = p.parse_args(argv)

    regionen = sorted(REGIONEN) if args.alle else (args.region or STANDARD_REGIONEN)
    if args.pdf and len(regionen) != 1:
        p.error("--pdf geht nur mit genau einer --region")

    daten = {"erstellt": datetime.now().isoformat(timespec="minutes"), "regionen": []}
    for r in regionen:
        try:
            bilder = None if args.ohne_bilder else args.ziel.parent / BILDER_UNTERORDNER
            daten["regionen"].append(region_exportieren(r, args.pdf, bilder))
        except Exception as e:  # noqa: BLE001
            print(f"  {r}: übersprungen ({e})", file=sys.stderr)

    args.ziel.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(daten, ensure_ascii=False, indent=1)
    args.ziel.write_text(text, encoding="utf-8")
    # Zusätzlich als JS, damit index.html auch per Doppelklick (file://) funktioniert, wo fetch() blockiert ist
    args.ziel.with_suffix(".js").write_text(f"window.ANGEBOTE = {text};\n", encoding="utf-8")
    n = sum(len(r["angebote"]) for r in daten["regionen"])
    print(f"{args.ziel}: {len(daten['regionen'])} Regionen, {n} Fitness-Angebote", file=sys.stderr)
    return 0 if daten["regionen"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
