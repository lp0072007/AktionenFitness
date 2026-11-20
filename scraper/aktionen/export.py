"""Daten für die Website exportieren: web/data/angebote.json

    python -m aktionen.export                                  # Standard-Regionen
    python -m aktionen.export --region wien --region tirol
    python -m aktionen.export --alle                           # alle 11 Spar-Regionen (dauert, je ~20 MB PDF)
    python -m aktionen.export --region niederoesterreich --pdf flugblatt.pdf
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import datetime
from pathlib import Path

import httpx
from PIL import Image

from .ausschnitte import ausschnitte_speichern
from .stores import lidl
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
        "id": f"lidl-{a.produkt_id}" if kette == "lidl" and a.produkt_id else f"{kette}-{region}-{a.seite}-{i}",
        "kette": kette,
        "name": a.name,
        "beschreibung": a.beschreibung,
        "seite": a.seite,
        "preis": a.preis,
        "normalpreis": a.normalpreis,
        "ab_menge": a.ab_menge,
        "zusatzpreis": a.zusatzpreis,
        "zusatz_text": a.zusatz_text,     # z. B. "Lidl Plus"; bei Spar: Aktionstag / App-Gutschein
        "gueltig_von": a.gueltig_von.isoformat() if a.gueltig_von else None,
        "gueltig_bis": a.gueltig_bis.isoformat() if a.gueltig_bis else None,
        "url": a.url,
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
        "zuordnung": "strukturiert" if kette == "lidl" else zuordnung,  # geprueft = Preis passt zum Grundpreis
        "bild": bild,             # Ausschnitt aus dem Flugblatt, relativ zu web/
    }


def lidl_exportieren(bilder_ordner: Path | None = None) -> dict:
    """Lidl-Angebote (österreichweit). Produktbilder werden lokal verkleinert gespeichert."""
    angebote = lidl.aktuelle_angebote()
    treffer = fitness_angebote(angebote)
    bilder: dict[int, str] = {}
    if bilder_ordner is not None:
        ordner = bilder_ordner / "lidl"
        ordner.mkdir(parents=True, exist_ok=True)
        web = bilder_ordner.parent.parent
        with httpx.Client(headers={"User-Agent": lidl.UA}, timeout=60, follow_redirects=True) as c:
            for t in treffer:
                a = t.angebot
                if not a.bild_url:
                    continue
                ziel = ordner / f"{a.produkt_id}.jpg"
                if not ziel.exists():
                    try:
                        r = c.get(a.bild_url)
                        r.raise_for_status()
                        bild = Image.open(io.BytesIO(r.content))
                        weiss = Image.new("RGB", bild.size, "white")  # PNG mit Transparenz auf Weiß
                        weiss.paste(bild, mask=bild.convert("RGBA").split()[-1])
                        weiss.thumbnail((480, 480))
                        weiss.save(ziel, "JPEG", quality=82, optimize=True)
                    except Exception as e:  # noqa: BLE001
                        print(f"  Lidl-Bild {a.produkt_id}: {e}", file=sys.stderr)
                        continue
                bilder[id(t)] = ziel.relative_to(web).as_posix()
    print(f"  lidl: {len(angebote)} Lebensmittel-Aktionen, {len(treffer)} fitnessrelevant", file=sys.stderr)
    return {
        "anzahl_angebote": len(angebote),
        "angebote": [treffer_als_dict(t, "lidl", "at", i, bilder.get(id(t))) for i, t in enumerate(treffer)],
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
    p.add_argument("--ohne-lidl", action="store_true", help="nur Spar")
    args = p.parse_args(argv)

    regionen = sorted(REGIONEN) if args.alle else (args.region or STANDARD_REGIONEN)
    if args.pdf and len(regionen) != 1:
        p.error("--pdf geht nur mit genau einer --region")

    # Struktur: regionen[] = Spar pro Bundesland, lidl = österreichweit (gilt für alle Regionen)
    daten = {"erstellt": datetime.now().isoformat(timespec="minutes"), "regionen": [], "lidl": None}
    bilder = None if args.ohne_bilder else args.ziel.parent / BILDER_UNTERORDNER
    for r in regionen:
        try:
            daten["regionen"].append(region_exportieren(r, args.pdf, bilder))
        except Exception as e:  # noqa: BLE001
            print(f"  {r}: übersprungen ({e})", file=sys.stderr)
    if not args.ohne_lidl:
        try:
            daten["lidl"] = lidl_exportieren(bilder)
        except Exception as e:  # noqa: BLE001
            print(f"  lidl: übersprungen ({e})", file=sys.stderr)

    args.ziel.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(daten, ensure_ascii=False, indent=1)
    args.ziel.write_text(text, encoding="utf-8")
    # Zusätzlich als JS, damit index.html auch per Doppelklick (file://) funktioniert, wo fetch() blockiert ist
    args.ziel.with_suffix(".js").write_text(f"window.ANGEBOTE = {text};\n", encoding="utf-8")
    n = sum(len(r["angebote"]) for r in daten["regionen"])
    n_lidl = len(daten["lidl"]["angebote"]) if daten["lidl"] else 0
    print(f"{args.ziel}: Spar {len(daten['regionen'])} Regionen / {n} Fitness-Angebote, Lidl {n_lidl}", file=sys.stderr)
    return 0 if daten["regionen"] or daten["lidl"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
