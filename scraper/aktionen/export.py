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
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import httpx
from PIL import Image

from . import verlauf
from .ausschnitte import ausschnitte_speichern
from .fortschritt import Fortschritt, Gesamt
from .stores import billa, dm, hofer, lidl, penny

# Österreichweite Ketten mit strukturierten Daten: Name -> Modul mit aktuelle_angebote() und UA
KETTEN_NAMEN = {"lidl": "Lidl", "hofer": "Hofer", "penny": "Penny", "billa": "Billa", "dm": "dm"}
WEITERE_KETTEN = {"lidl": lidl, "hofer": hofer, "penny": penny, "billa": billa, "dm": dm}
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


def angebote_aus_pdf(pfad, fortschritt: Fortschritt | None = None) -> list[FlugblattAngebot]:
    import pdfplumber

    angebote = []
    with pdfplumber.open(pfad) as pdf:
        for n, seite in enumerate(pdf.pages, start=1):
            if fortschritt:
                fortschritt.setze(n, len(pdf.pages))
            woerter = seite.extract_words(use_text_flow=True, extra_attrs=["size", "fontname"])
            angebote += analysiere_seite(woerter, n)
    if fortschritt:
        fortschritt.fertig(f"{len(angebote)} Angebote")
    return angebote


def aktion_als_dict(a: FlugblattAngebot, kette: str, region: str, i: int, bild: str | None = None) -> dict:
    """Schlanke Form für den Einkaufslisten-Abgleich (alle Aktionen, nicht nur Fitness)."""
    d = {
        "id": f"{kette}-{a.produkt_id}" if a.produkt_id else f"{kette}-{region}-{a.seite}-{i}",
        "kette": kette,
        "name": a.name,
        "preis": a.preis,
        "normalpreis": a.normalpreis,
        "ab_menge": a.ab_menge,
        "zusatzpreis": a.zusatzpreis,
        "zusatz_text": a.zusatz_text,
        "menge": a.menge,
        "einheit": a.einheit,
        "pro_kg": a.pro_kg,
        "gueltig_von": a.gueltig_von.isoformat() if a.gueltig_von else None,
        "gueltig_bis": a.gueltig_bis.isoformat() if a.gueltig_bis else None,
        "aktion": a.aktion,
        "url": a.url,
        "bild": bild or a.bild_url,
        "seite": a.seite or None,
        "kategorie": a.kategorie_pfad,
    }
    return {k: v for k, v in d.items() if v not in (None, [], False)}  # kleinere Datei


def treffer_als_dict(t: FitnessTreffer, kette: str, region: str, i: int, bild: str | None = None) -> dict:
    a, k = t.angebot, t.kategorie
    zuordnung = {True: "geprueft", False: "unsicher", None: "unbekannt"}[a.grundpreis_ok]
    return {
        "id": f"{kette}-{a.produkt_id}" if kette in WEITERE_KETTEN and a.produkt_id else f"{kette}-{region}-{a.seite}-{i}",
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
        "zuordnung": "strukturiert" if kette in WEITERE_KETTEN else zuordnung,  # geprueft = Preis passt zum Grundpreis
        "bild": bild,             # Ausschnitt aus dem Flugblatt, relativ zu web/
    }


def _bild_speichern(client: httpx.Client, url: str, ziel: Path) -> None:
    r = client.get(url)
    r.raise_for_status()
    bild = Image.open(io.BytesIO(r.content))
    weiss = Image.new("RGB", bild.size, "white")  # PNG mit Transparenz auf Weiß
    weiss.paste(bild, mask=bild.convert("RGBA").split()[-1])
    weiss.thumbnail((480, 480))
    weiss.save(ziel, "JPEG", quality=82, optimize=True)


def kette_exportieren(kette: str, bilder_ordner: Path | None = None) -> dict:
    """Österreichweite Kette (Lidl, Hofer, Penny, Billa). Produktbilder werden parallel geladen und verkleinert."""
    modul = WEITERE_KETTEN[kette]
    f = Fortschritt("Angebote")
    angebote = modul.aktuelle_angebote(fortschritt=f)
    treffer = fitness_angebote(angebote)
    art = "Produkte (Dauerpreise)" if kette == "dm" else "Aktionen"
    f.fertig(f"{len(angebote)} {art}, {len(treffer)} fitnessrelevant")
    bilder: dict[int, str] = {}
    if bilder_ordner is not None:
        ordner = bilder_ordner / kette
        ordner.mkdir(parents=True, exist_ok=True)
        web = bilder_ordner.parent.parent
        aufgaben = {}
        for t in treffer:
            if t.angebot.bild_url:
                ziel = ordner / f"{t.angebot.produkt_id}.jpg"
                aufgaben[id(t)] = (t.angebot.bild_url, ziel)
        neu = {k: v for k, v in aufgaben.items() if not v[1].exists()}  # schon vorhandene nicht nochmal laden
        fb = Fortschritt("Bilder", len(neu))
        with httpx.Client(headers={"User-Agent": modul.UA}, timeout=60, follow_redirects=True) as c, \
                ThreadPoolExecutor(max_workers=8) as pool:
            laeufe = {pool.submit(_bild_speichern, c, url, ziel): (k, ziel) for k, (url, ziel) in neu.items()}
            fehler = 0
            for lauf in as_completed(laeufe):
                fb.weiter()
                if lauf.exception():
                    fehler += 1
            fb.fertig(f"{fehler} nicht ladbar" if fehler else ("alle schon vorhanden" if not neu else ""))
        for k, (_, ziel) in aufgaben.items():
            if ziel.exists():
                bilder[k] = ziel.relative_to(web).as_posix()
    bild_von = {id(t.angebot): bilder.get(id(t)) for t in treffer}
    return {
        "anzahl_angebote": len(angebote),
        "angebote": [treffer_als_dict(t, kette, "at", i, bilder.get(id(t))) for i, t in enumerate(treffer)],
        # dm hat keine Aktionen (Dauerpreise) und kommt deshalb nicht in den Aktions-Abgleich
        "alle": [] if kette == "dm" else
                [aktion_als_dict(a, kette, "at", i, bild_von.get(id(a))) for i, a in enumerate(angebote)],
    }


def region_exportieren(region: str, pdf: str | None = None, bilder_ordner: Path | None = None,
                       alle_bilder: bool = True) -> dict:
    """Spar-Region aus dem Flugblatt. alle_bilder: Ausschnitt für jede Aktion (sonst nur für Fitness-Produkte)."""
    fb = None
    if pdf is None:
        fb = aktuelles_flugblatt(region)
        print(f"    {fb.flipbook.name} ({fb.flipbook.titel})", file=sys.stderr)
        pdf = pdf_herunterladen(fb, DATEN_ORDNER, fortschritt=Fortschritt("PDF laden", einheit="MB"))
    angebote = angebote_aus_pdf(pdf, Fortschritt("Seiten lesen"))
    treffer = fitness_angebote(angebote)
    bilder: dict[int, str] = {}
    if bilder_ordner is not None:
        index = {id(a): i for i, a in enumerate(angebote)}
        nur = None if alle_bilder else {index[id(t.angebot)] for t in treffer}
        dateien = ausschnitte_speichern(pdf, angebote, bilder_ordner / region, f"spar-{region}", nur,
                                        fortschritt=Fortschritt("Ausschnitte"))
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
        "alle": [
            {**aktion_als_dict(a, "spar", region, i, bilder.get(i) if bilder else None),
             "gueltig_von": gueltig[0].isoformat() if gueltig else None,
             "gueltig_bis": gueltig[1].isoformat() if gueltig else None}
            for i, a in enumerate(angebote)
        ],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m aktionen.export")
    p.add_argument("--region", action="append", choices=sorted(REGIONEN))
    p.add_argument("--alle", action="store_true")
    p.add_argument("--pdf", help="nur mit genau einer --region")
    p.add_argument("--ziel", type=Path, default=WEB_DATEN)
    p.add_argument("--ohne-bilder", action="store_true", help="keine Flugblatt-Ausschnitte erzeugen")
    p.add_argument("--nur-fitness-bilder", action="store_true",
                   help="Spar: Ausschnitte nur für Fitness-Produkte (schneller, weniger Speicher)")
    p.add_argument("--ohne-lidl", action="store_true")
    p.add_argument("--ohne-hofer", action="store_true")
    p.add_argument("--ohne-penny", action="store_true")
    p.add_argument("--ohne-billa", action="store_true")
    p.add_argument("--ohne-dm", action="store_true")
    p.add_argument("--ohne-verlauf", action="store_true", help="Preise nicht im Preisverlauf speichern")
    args = p.parse_args(argv)

    regionen = sorted(REGIONEN) if args.alle else (args.region or STANDARD_REGIONEN)
    if args.pdf and len(regionen) != 1:
        p.error("--pdf geht nur mit genau einer --region")

    # Struktur: regionen[] = Spar pro Bundesland; lidl, hofer = österreichweit (gelten für alle Regionen)
    daten = {"erstellt": datetime.now().isoformat(timespec="minutes"), "regionen": [], "lidl": None, "hofer": None, "penny": None, "billa": None, "dm": None}
    bilder = None if args.ohne_bilder else args.ziel.parent / BILDER_UNTERORDNER
    ketten = [k for k in WEITERE_KETTEN if not getattr(args, f"ohne_{k}")]
    # Aufwand grob: Spar-Region (PDF + Auswertung) ≈ 2,5 × Kette, Billa ≈ 1,5 × (viele Angebote), dm ≈ 4 ×
    spar = 2.5 if args.nur_fitness_bilder or args.ohne_bilder else 3.0  # alle Ausschnitte: ca. +10 s je Region
    gesamt = Gesamt([spar] * len(regionen) + [{"billa": 1.5, "dm": 4.0}.get(k, 1.0) for k in ketten])  # dm: 3 s Pausen
    for r in regionen:
        gesamt.schritt(f"Spar {REGION_NAMEN.get(r, r)}")
        try:
            daten["regionen"].append(region_exportieren(r, args.pdf, bilder, alle_bilder=not args.nur_fitness_bilder))
        except Exception as e:  # noqa: BLE001
            print(f"\n    übersprungen ({e})", file=sys.stderr)
    for kette in ketten:
        gesamt.schritt(KETTEN_NAMEN.get(kette, kette))
        try:
            daten[kette] = kette_exportieren(kette, bilder)
        except Exception as e:  # noqa: BLE001
            print(f"\n    übersprungen ({e})", file=sys.stderr)
    gesamt.ende()

    args.ziel.parent.mkdir(parents=True, exist_ok=True)
    # Alle Aktionen (für den Einkaufslisten-Abgleich) in eine eigene Datei, damit die Startseite schlank bleibt
    aktionen = {
        "erstellt": daten["erstellt"],
        "regionen": {r["region"]: {"name": r["name"], "angebote": r.pop("alle", [])} for r in daten["regionen"]},
        "ketten": {k: daten[k].pop("alle", []) for k in WEITERE_KETTEN if daten[k]},
    }
    # Preisverlauf: alle Aktionen (und dm-Dauerpreise) mit Datum speichern, Spar bekommt einen stabilen Schlüssel
    alle_dicts = [d for r in aktionen["regionen"].values() for d in r["angebote"]] + \
        [d for l in aktionen["ketten"].values() for d in l] + (daten["dm"]["angebote"] if daten.get("dm") else [])
    fitness_dicts = [d for r in daten["regionen"] for d in r["angebote"]] + \
        [d for k in WEITERE_KETTEN if daten[k] for d in daten[k]["angebote"]]
    for d in alle_dicts + fitness_dicts:
        if d["kette"] == "spar":
            d["vk"] = verlauf.schluessel(d)
    if not args.ohne_verlauf:
        heute = daten["erstellt"][:10]
        conn = verlauf.oeffnen()
        n = verlauf.speichern(conn, alle_dicts, heute)
        web_verlauf = verlauf.fuer_website(conn, [verlauf.schluessel(d) for d in alle_dicts + fitness_dicts], heute)
        conn.close()
        (args.ziel.parent / "verlauf.js").write_text(
            "window.VERLAUF = " + json.dumps(web_verlauf, ensure_ascii=False, separators=(",", ":")) + ";\n",
            encoding="utf-8")
        print(f"    Preisverlauf: {n} Preise gespeichert, {len(web_verlauf['preise'])} Produkte mit Verlauf",
              file=sys.stderr)
    (args.ziel.parent / "aktionen.js").write_text(
        "window.AKTIONEN = " + json.dumps(aktionen, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    text = json.dumps(daten, ensure_ascii=False, indent=1)
    args.ziel.write_text(text, encoding="utf-8")
    # Zusätzlich als JS, damit index.html auch per Doppelklick (file://) funktioniert, wo fetch() blockiert ist
    args.ziel.with_suffix(".js").write_text(f"window.ANGEBOTE = {text};\n", encoding="utf-8")
    n = sum(len(r["angebote"]) for r in daten["regionen"])
    weitere = ", ".join(f"{KETTEN_NAMEN.get(k, k)} {len(daten[k]['angebote']) if daten[k] else 'übersprungen'}"
                        for k in WEITERE_KETTEN)
    print(f"{args.ziel}: Spar {len(daten['regionen'])} Regionen / {n} Fitness-Angebote, {weitere}", file=sys.stderr)
    return 0 if daten["regionen"] or any(daten[k] for k in WEITERE_KETTEN) else 1


if __name__ == "__main__":
    raise SystemExit(main())
