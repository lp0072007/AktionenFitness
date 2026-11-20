"""Billa: Aktionsangebote aus dem BILLA Online-Shop (shop.billa.at), gleiche Rewe-Plattform wie Penny.

Pro Kategorie mit Filter auf Aktionen:
    GET https://shop.billa.at/api/product-discovery/categories/kuehlwaren-15416/products
        ?inPromotion=true&sortBy=relevance&page=0&pageSize=100

Die Kategorien stehen auf https://shop.billa.at/aktionen (als product-group-<slug>-{"inPromotion":"true",…}).
Produktformat: siehe rewe.py. Unterschied zu Penny: price.standard.value = Normalpreis, und es gibt
KEINE Gültigkeitsdaten (es sind die aktuellen Shop-Aktionen). Österreichweit.
"""

from __future__ import annotations

import re
import time
from datetime import date

import httpx

from ..flugblatt_pdf import FlugblattAngebot
from . import rewe
from .base import USER_AGENT, get_mit_wiederholung

BASIS = "https://shop.billa.at"
UA = USER_AGENT
SEITENGROESSE = 100
# Lebensmittel-Kategorien (Stand 11/2026). Werden zusätzlich von /aktionen gelesen, falls sich Nummern ändern.
STANDARD_KATEGORIEN = [
    "obst-und-gemuese-13751", "brot-und-gebaeck-15520", "kuehlwaren-15416", "fleisch-wurst-und-fisch-15388",
    "tiefkuehl-15415", "vorratsschrank-15012", "schnelle-kueche-15389", "getraenke-13784", "rein-pflanzlich-15207",
]
_NICHT_LEBENSMITTEL = ("drogerie", "haustier", "haushalt", "baby")
_KATEGORIE_RE = re.compile(r'product-group-([a-z0-9-]+-\d{4,6})-\{\\?"inPromotion')


def kategorien_aus_html(aktionen_html: str) -> list[str]:
    gefunden = []
    for k in _KATEGORIE_RE.findall(aktionen_html):
        if k not in gefunden and not any(n in k for n in _NICHT_LEBENSMITTEL):
            gefunden.append(k)
    return gefunden


def parse_produkt(p: dict) -> FlugblattAngebot | None:
    return rewe.parse_produkt(p, f"{BASIS}/produkte")


def aktuelle_angebote(heute: date | None = None, tage_voraus: int = 10, client: httpx.Client | None = None,
                      pause: float = 1.0) -> list[FlugblattAngebot]:
    heute = heute or date.today()
    client = client or httpx.Client(headers={"User-Agent": UA}, timeout=60, follow_redirects=True)
    try:
        kategorien = kategorien_aus_html(get_mit_wiederholung(client, f"{BASIS}/aktionen").text) or STANDARD_KATEGORIEN
    except httpx.HTTPError:
        kategorien = STANDARD_KATEGORIEN
    gesehen: dict[str, FlugblattAngebot] = {}
    sorten: set[tuple] = set()
    for kat in kategorien:
        seite = 0
        while True:
            url = (f"{BASIS}/api/product-discovery/categories/{kat}/products"
                   f"?inPromotion=true&sortBy=relevance&page={seite}&pageSize={SEITENGROESSE}")
            r = get_mit_wiederholung(client, url)
            if r.status_code == 404:
                break  # Kategorie gibt es nicht mehr
            r.raise_for_status()
            daten = r.json()
            rewe.sammeln(daten.get("results") or [], heute, tage_voraus, gesehen, sorten, f"{BASIS}/produkte")
            seite += 1
            time.sleep(pause)
            if not daten.get("results") or seite * SEITENGROESSE >= (daten.get("total") or 0):
                break
    return list(gesehen.values())
