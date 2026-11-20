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

from .fitness import DATEN_ORDNER, FitnessTreffer, fitness_angebote
from .flugblatt_pdf import FlugblattAngebot, analysiere_seite
from .spar_flugblatt import REGIONEN, aktuelles_flugblatt, pdf_herunterladen

WEB_DATEN = Path(__file__).resolve().parents[2] / "web" / "data" / "angebote.json"
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


def treffer_als_dict(t: FitnessTreffer, kette: str, region: str, i: int) -> dict:
    a, k = t.angebot, t.kategorie
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
    }


def region_exportieren(region: str, pdf: str | None = None) -> dict:
    fb = None
    if pdf is None:
        fb = aktuelles_flugblatt(region)
        print(f"  {region}: {fb.flipbook.name} ({fb.flipbook.titel})", file=sys.stderr)
        pdf = pdf_herunterladen(fb, DATEN_ORDNER)
    angebote = angebote_aus_pdf(pdf)
    treffer = fitness_angebote(angebote)
    gueltig = fb.flipbook.gueltig if fb else None
    return {
        "region": region,
        "name": REGION_NAMEN.get(region, region),
        "flugblatt": fb.flipbook.name if fb else Path(pdf).name,
        "flugblatt_url": fb.viewer_url if fb else None,
        "gueltig_von": gueltig[0].isoformat() if gueltig else None,
        "gueltig_bis": gueltig[1].isoformat() if gueltig else None,
        "anzahl_angebote": len(angebote),
        "angebote": [treffer_als_dict(t, "spar", region, i) for i, t in enumerate(treffer)],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m aktionen.export")
    p.add_argument("--region", action="append", choices=sorted(REGIONEN))
    p.add_argument("--alle", action="store_true")
    p.add_argument("--pdf", help="nur mit genau einer --region")
    p.add_argument("--ziel", type=Path, default=WEB_DATEN)
    args = p.parse_args(argv)

    regionen = sorted(REGIONEN) if args.alle else (args.region or STANDARD_REGIONEN)
    if args.pdf and len(regionen) != 1:
        p.error("--pdf geht nur mit genau einer --region")

    daten = {"erstellt": datetime.now().isoformat(timespec="minutes"), "regionen": []}
    for r in regionen:
        try:
            daten["regionen"].append(region_exportieren(r, args.pdf))
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
