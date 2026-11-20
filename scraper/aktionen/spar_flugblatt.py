"""Spar-Flugblätter automatisch finden und als PDF laden, ohne den Cloudflare-geschützten Shop.

- Viewer:  https://flugblatt.interspar.at/{gruppe}/{slug}/   (slug z. B. "niederoesterreich_kw47")
- PDF:     POST {viewer}GetPDF.ashx (pageNumbers="") -> 302 auf cdn.ipaper.io/.../Download.pdf?token=...
  Den Redirect NICHT automatisch per POST folgen lassen (CDN antwortet dann 405), sondern die Location per GET laden.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import httpx

from .stores.base import USER_AGENT
from .stores.ipaper import Flipbook, parse_viewer_html

BASIS = "https://flugblatt.interspar.at"

# Region -> (gruppe, slug-Präfix)
REGIONEN = {
    "burgenland_nord": ("burgenland", "burgenland_nord"),
    "burgenland_sued": ("burgenland", "burgenland_sued"),
    "kaernten": ("kaernten", "kaernten"),
    "niederoesterreich": ("niederoesterreich", "niederoesterreich"),
    "oberoesterreich": ("oberoesterreich", "oberoesterreich"),
    "osttirol": ("osttirol", "osttirol"),
    "salzburg": ("salzburg", "salzburg"),
    "steiermark": ("steiermark", "steiermark"),
    "tirol": ("tirol", "tirol"),
    "vorarlberg": ("vorarlberg", "vorarlberg"),
    "wien": ("wien", "wien"),
}


@dataclass
class SparFlugblatt:
    region: str
    kw: int
    viewer_url: str
    flipbook: Flipbook


def viewer_url(region: str, kw: int) -> str:
    gruppe, praefix = REGIONEN[region]
    return f"{BASIS}/{gruppe}/{praefix}_kw{kw}/"


def kandidaten_kw(heute: date, zurueck: int = 3) -> list[int]:
    """Aktuelle ISO-Kalenderwoche und die Wochen davor. Ein Flugblatt gilt meist 2 Wochen."""
    return [(heute - timedelta(weeks=i)).isocalendar().week for i in range(zurueck + 1)]


def _client() -> httpx.Client:
    return httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60)


def aktuelles_flugblatt(region: str, heute: date | None = None, client: httpx.Client | None = None) -> SparFlugblatt:
    """Neuestes Flugblatt der Region, das heute gilt (laut Titel 'Do., 19.11.26 - Mi., 02.12.26')."""
    heute = heute or date.today()
    client = client or _client()
    gefunden = []
    for kw in kandidaten_kw(heute):
        url = viewer_url(region, kw)
        r = client.get(url, follow_redirects=True)
        if r.status_code != 200 or "window.staticSettings" not in r.text:
            continue
        fb = parse_viewer_html(r.text)
        gefunden.append(SparFlugblatt(region, kw, url, fb))
        if fb.gueltig and fb.gueltig[0] <= heute <= fb.gueltig[1]:
            return gefunden[-1]
    if gefunden:
        return gefunden[0]  # z. B. Flugblatt ab morgen gültig
    raise LookupError(f"Kein Spar-Flugblatt für {region} gefunden (KW {kandidaten_kw(heute)})")


def pdf_url(viewer: str, client: httpx.Client | None = None) -> str:
    client = client or _client()
    r = client.post(viewer + "GetPDF.ashx", data={"pageNumbers": ""}, follow_redirects=False)
    if r.status_code not in (301, 302, 303) or "location" not in r.headers:
        raise RuntimeError(f"PDF-Link nicht erhalten (HTTP {r.status_code})")
    return r.headers["location"]


def pdf_herunterladen(fb: SparFlugblatt, ordner: Path, client: httpx.Client | None = None) -> Path:
    """Lädt das PDF (ca. 20 MB) in den Ordner. Ist es schon da, wird es nicht nochmal geladen."""
    ordner.mkdir(parents=True, exist_ok=True)
    ziel = ordner / f"spar_{fb.region}_kw{fb.kw}.pdf"
    if ziel.exists() and ziel.stat().st_size > 0:
        return ziel
    client = client or _client()
    with client.stream("GET", pdf_url(fb.viewer_url, client)) as r:
        r.raise_for_status()
        tmp = ziel.with_suffix(".part")
        with tmp.open("wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    tmp.replace(ziel)
    return ziel
