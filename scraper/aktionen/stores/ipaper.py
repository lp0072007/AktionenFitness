"""Auswertung von iPaper-Flipbooks (Online-Flugblätter, u. a. von Spar).

Ein iPaper-Flugblatt besteht aus Seitenbildern (Normal.jpg / Zoom.jpg) und "Enrichments": klickbare
Bereiche pro Seite, abrufbar als PageX-Y.json. Links vom Typ 1 zeigen teils auf Produktseiten
(z. B. https://www.interspar.at/p/2020004779311). Daraus lassen sich die Artikelnummern im Flugblatt lesen.

Achtung: Verlinkt sind fast nur Produkte, die es im Online-Shop gibt (v. a. Non-Food). Lebensmittel, die
nur im Markt verkauft werden, haben meist keinen Link.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_PRODUKT_URL_RE = re.compile(r"/p/(\d+)(?:[/?#]|$)")

TYP_LINK = 1
TYP_BILD = 3
TYP_SHOP_AUSWAHL = 6  # "Passenden Artikel finden": Menü, Einträge haben parentid
TYP_POPUP = 9


@dataclass
class FlugblattLink:
    seite: int                  # 1-basiert
    produkt_nr: str
    name: str | None = None     # nur bei Menü-Einträgen bekannt
    position: tuple[float, float, float, float] | None = None  # x, y, Breite, Höhe (0..1), für Bildausschnitt


def produkt_links(data: dict) -> list[FlugblattLink]:
    """Alle Produkt-Links (Artikelnummern) aus einer PageX-Y.json, ohne Duplikate."""
    links: dict[str, FlugblattLink] = {}
    for e in data.get("enrichments") or []:
        if e.get("type") != TYP_LINK or not e.get("url"):
            continue
        m = _PRODUKT_URL_RE.search(e["url"])
        if not m:
            continue
        nr = m.group(1)
        pos = None
        if all(k in e for k in ("x", "y", "width", "height")):
            pos = (e["x"], e["y"], e["width"], e["height"])
        if nr not in links:
            links[nr] = FlugblattLink(seite=e["pageIndex"] + 1, produkt_nr=nr, name=e.get("menuitemName"), position=pos)
    return list(links.values())
