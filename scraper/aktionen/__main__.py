"""CLI: python -m aktionen spar --query skyr [--json]"""

from __future__ import annotations

import argparse
import json
import sys

from .stores import STORES


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="aktionen")
    p.add_argument("kette", choices=sorted(STORES))
    p.add_argument("--query", default="*", help="Suchbegriff, z. B. skyr")
    p.add_argument("--raw", action="store_true", help="Rohdaten der Kette ausgeben (zum Felder-Erkunden)")
    p.add_argument("--json", action="store_true", help="Ausgabe als JSON")
    args = p.parse_args(argv)

    store = STORES[args.kette]()
    try:
        if args.raw:
            print(json.dumps(store.fetch_raw(args.query), indent=2, ensure_ascii=False))
            return 0
        angebote = store.angebote(args.query)
    except Exception as e:  # noqa: BLE001
        print(f"Fehler: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps([a.to_dict() for a in angebote], indent=2, ensure_ascii=False))
    else:
        for a in angebote:
            aktion = f"  AKTION -{a.rabatt_prozent}%" if a.ist_aktion else ""
            menge = f"{a.menge:g} {a.einheit}" if a.menge else ""
            print(f"{a.preis:6.2f} €  {a.marke or '':<15} {a.name:<40} {menge}{aktion}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
