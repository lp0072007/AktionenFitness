"""CLI.

    python -m aktionen spar --query skyr            live abfragen
    python -m aktionen spar --datei antwort.json    gespeicherte JSON-Antwort aus dem Browser einlesen
    python -m aktionen spar --query skyr --raw      Rohdaten anzeigen (Felder erkunden)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .stores import STORES
from .stores.spar import produkte_aus_antwort


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="aktionen")
    p.add_argument("kette", choices=sorted(STORES))
    p.add_argument("--query", default="*", help="Suchbegriff, z. B. skyr")
    p.add_argument("--datei", type=Path, help="Gespeicherte JSON-Antwort statt Live-Abfrage")
    p.add_argument("--raw", action="store_true", help="Rohdaten der Kette ausgeben (zum Felder-Erkunden)")
    p.add_argument("--json", action="store_true", help="Ausgabe als JSON")
    args = p.parse_args(argv)

    store = STORES[args.kette]()
    try:
        if args.datei:
            raw = produkte_aus_antwort(json.loads(args.datei.read_text(encoding="utf-8")))
        else:
            raw = store.fetch_raw(args.query)
    except Exception as e:  # noqa: BLE001
        print(f"Fehler: {e}", file=sys.stderr)
        return 1

    if args.raw:
        print(json.dumps(raw, indent=2, ensure_ascii=False))
        return 0

    angebote = [a for r in raw if (a := store.parse(r)) is not None]
    if args.json:
        print(json.dumps([a.to_dict() for a in angebote], indent=2, ensure_ascii=False))
    else:
        for a in angebote:
            aktion = f"  AKTION -{a.rabatt_prozent}%" if a.ist_aktion else ""
            menge = f"{a.menge:g} {a.einheit}" if a.menge else "?"
            kg = f"{a.preis_pro_kg:6.2f} €/kg" if a.preis_pro_kg else " " * 11
            print(f"{a.preis:6.2f} €  {kg}  {menge:>8}  {a.name}{aktion}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
