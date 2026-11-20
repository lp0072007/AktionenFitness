"""CLI.

    python -m aktionen spar --query skyr            Suche live abfragen
    python -m aktionen spar --nr 2020005744769      Produktdetails inkl. Nährwerten live abfragen
    python -m aktionen spar --datei antwort.json    gespeicherte JSON-Antwort (Suche oder Detail) einlesen
    python -m aktionen spar --query skyr --raw      Rohdaten anzeigen (Felder erkunden)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .models import Angebot
from .stores import STORES
from .stores.spar import produkte_aus_antwort


def zeile(a: Angebot) -> str:
    aktion = f"  AKTION -{a.rabatt_prozent}%" if a.ist_aktion else ""
    menge = f"{a.menge:g} {a.einheit}" if a.menge else "?"
    kg = f"{a.preis_pro_kg:6.2f} €/kg" if a.preis_pro_kg else " " * 11
    prot = f"{a.protein_pro_euro:5.1f} g Protein/€" if a.protein_pro_euro else ""
    return f"{a.preis:6.2f} €  {kg}  {menge:>8}  {a.name}{aktion}  {prot}".rstrip()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="aktionen")
    p.add_argument("kette", choices=sorted(STORES))
    quelle = p.add_mutually_exclusive_group()
    quelle.add_argument("--query", default="*", help="Suchbegriff, z. B. skyr")
    quelle.add_argument("--nr", help="Produktnummer für Detailabfrage (inkl. Nährwerte)")
    quelle.add_argument("--datei", type=Path, help="Gespeicherte JSON-Antwort statt Live-Abfrage")
    p.add_argument("--raw", action="store_true", help="Rohdaten der Kette ausgeben (zum Felder-Erkunden)")
    p.add_argument("--json", action="store_true", help="Ausgabe als JSON")
    args = p.parse_args(argv)

    store = STORES[args.kette]()
    try:
        if args.datei:
            data = json.loads(args.datei.read_text(encoding="utf-8"))
        elif args.nr:
            data = store.fetch_detail(args.nr)
        else:
            data = store.fetch_json(args.query)
    except Exception as e:  # noqa: BLE001
        print(f"Fehler: {e}", file=sys.stderr)
        return 1

    if args.raw:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    if "product" in data:  # Detail-Antwort
        angebote = [a] if (a := store.parse_detail(data)) else []
    else:
        angebote = [a for r in produkte_aus_antwort(data) if (a := store.parse(r)) is not None]

    if args.json:
        print(json.dumps([a.to_dict() for a in angebote], indent=2, ensure_ascii=False))
    else:
        for a in angebote:
            print(zeile(a))
            if a.naehrwerte:
                n = a.naehrwerte
                print(f"          pro 100 g: {n.kcal} kcal, {n.protein} g Protein, "
                      f"{n.kohlenhydrate} g KH, {n.fett} g Fett")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
