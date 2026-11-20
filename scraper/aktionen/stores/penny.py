"""Penny Österreich: Aktionsangebote über die Produkt-Schnittstelle von penny.at.

    GET https://www.penny.at/api/product-discovery/categories/alle-angebote-99000000/products?page=0&pageSize=100

Antwort: {"total": 591, "count": …, "offset": …, "results": [Produkt, …]}. Produktformat: siehe rewe.py.
Penny liefert pro Angebot validityStart/validityEnd. Angebote gelten österreichweit.
Von Cloud- und Heim-IP aus erreichbar (getestet 20.11.2026).
"""

from __future__ import annotations

import time
from datetime import date

import httpx

from ..flugblatt_pdf import FlugblattAngebot
from . import rewe
from .base import USER_AGENT, get_mit_wiederholung

BASIS = "https://www.penny.at"
KATEGORIE = "alle-angebote-99000000"
UA = USER_AGENT
SEITENGROESSE = 100


def parse_produkt(p: dict) -> FlugblattAngebot | None:
    return rewe.parse_produkt(p, f"{BASIS}/produkte")


def aktuelle_angebote(heute: date | None = None, tage_voraus: int = 10, client: httpx.Client | None = None,
                      pause: float = 1.0) -> list[FlugblattAngebot]:
    """Alle Lebensmittel-Aktionen, die heute gelten oder in den nächsten `tage_voraus` Tagen starten."""
    heute = heute or date.today()
    client = client or httpx.Client(headers={"User-Agent": UA, "Accept": "application/json"}, timeout=60)
    gesehen: dict[str, FlugblattAngebot] = {}
    sorten: set[tuple] = set()
    seite = 0
    while True:
        url = f"{BASIS}/api/product-discovery/categories/{KATEGORIE}/products?page={seite}&pageSize={SEITENGROESSE}"
        r = get_mit_wiederholung(client, url)
        r.raise_for_status()
        daten = r.json()
        rewe.sammeln(daten.get("results") or [], heute, tage_voraus, gesehen, sorten, f"{BASIS}/produkte")
        seite += 1
        if not daten.get("results") or seite * SEITENGROESSE >= (daten.get("total") or 0):
            break
        time.sleep(pause)
    return list(gesehen.values())
