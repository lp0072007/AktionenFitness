"""Auswertung von iPaper-Flipbooks (Online-Flugblätter, u. a. von Spar).

Ein iPaper-Flugblatt besteht aus Seitenbildern (Normal.jpg / Zoom.jpg) und "Enrichments": klickbare
Bereiche pro Seite, abrufbar als PageX-Y.json. Links vom Typ 1 zeigen teils auf Produktseiten
(z. B. https://www.interspar.at/p/2020004779311). Daraus lassen sich die Artikelnummern im Flugblatt lesen.

Achtung: Verlinkt sind fast nur Produkte, die es im Online-Shop gibt (v. a. Non-Food). Lebensmittel, die
nur im Markt verkauft werden, haben meist keinen Link.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date

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


# --- Viewer-Seite (HTML) -----------------------------------------------------

_SETTINGS_MARKER = "window.staticSettings ="
_TITEL_DATUM_RE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})")


@dataclass
class Flipbook:
    """Daten aus window.staticSettings der Viewer-Seite (z. B. flugblatt.interspar.at/...)."""

    name: str
    titel: str                                      # z. B. "Do., 19.11.26 - Mi., 02.12.26"
    seitentexte: list[str] = field(default_factory=list)  # Index 0 = Seite 1
    enrichment_urls: list[str] = field(default_factory=list)
    bilder_basis_url: str | None = None             # aws.url
    bilder_token: str | None = None                 # aws.policy, läuft nach ca. 1 Tag ab

    @property
    def gueltig(self) -> tuple[date, date] | None:
        """Gültigkeit aus dem Titel, z. B. 'Do., 19.11.26 - Mi., 02.12.26'."""
        daten = []
        for t, m, j in _TITEL_DATUM_RE.findall(self.titel):
            jahr = int(j) + 2000 if len(j) == 2 else int(j)
            daten.append(date(jahr, int(m), int(t)))
        return (daten[0], daten[1]) if len(daten) >= 2 else None

    def seitenbild_url(self, seite: int, zoom: bool = False) -> str | None:
        """URL des Seitenbilds (1-basiert). Pfadschema laut token_path '/Pages/', noch ungeprüft."""
        if not self.bilder_basis_url or not self.bilder_token:
            return None
        datei = "Zoom.jpg" if zoom else "Normal.jpg"
        return f"{self.bilder_basis_url}Pages/{seite}/{datei}?{self.bilder_token}"


def static_settings(html: str) -> dict:
    """Liest das JSON-Objekt window.staticSettings aus dem HTML der Viewer-Seite."""
    start = html.find(_SETTINGS_MARKER)
    if start < 0:
        raise ValueError("window.staticSettings nicht gefunden: ist das eine iPaper-Viewer-Seite?")
    start = html.index("{", start)
    obj, _ = json.JSONDecoder().raw_decode(html, start)
    return obj


def parse_viewer_html(html: str) -> Flipbook:
    s = static_settings(html)
    aws = s.get("aws") or {}
    return Flipbook(
        name=s.get("name") or "",
        titel=s.get("pageTitle") or "",
        seitentexte=list(s.get("pageTexts") or []),
        enrichment_urls=list(((s.get("enrichments") or {}).get("chunkUrls") or {}).values()),
        bilder_basis_url=aws.get("url"),
        bilder_token=aws.get("policy"),
    )
