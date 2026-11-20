"""Gemeinsame Basis für alle Ketten-Scraper."""

from __future__ import annotations

import html
import re
from abc import ABC, abstractmethod

from ..models import Angebot, Naehrwerte

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AktionenFitness/0.1 (privates Projekt)"

_MENGE_RE = re.compile(
    r"(?:(\d+)\s*[x×]\s*)?(\d+(?:[.,]\d+)?)\s*(kg|g|l|ml|cl|stk\.?|stück)\b",
    re.IGNORECASE,
)


def parse_menge(text: str | None) -> tuple[float | None, str | None]:
    """'450 g' -> (450, 'g'), '1,5 l' -> (1500, 'ml'), '4 x 125 g' -> (500, 'g')."""
    if not text:
        return None, None
    m = _MENGE_RE.search(text)
    if not m:
        return None, None
    anzahl = int(m.group(1)) if m.group(1) else 1
    wert = float(m.group(2).replace(",", ".")) * anzahl
    einheit = m.group(3).lower().rstrip(".")
    if einheit == "kg":
        return wert * 1000, "g"
    if einheit == "l":
        return wert * 1000, "ml"
    if einheit == "cl":
        return wert * 10, "ml"
    if einheit in ("stk", "stück"):
        return wert, "stk"
    return wert, einheit


def parse_preis(wert) -> float | None:
    """Akzeptiert 1.99, '1,99', '€1,99', '€8,87/kg'."""
    if wert is None:
        return None
    if isinstance(wert, (int, float)):
        return float(wert)
    s = str(wert).split("/")[0].replace("€", "").replace(",", ".").strip()
    try:
        return float(s)
    except ValueError:
        return None


_ZAHL_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(kcal|kj|g|mg)?", re.IGNORECASE)

# Reihenfolge wichtig: spezifischere Begriffe zuerst ("davon Zucker" vor "Kohlenhydrate")
_NAEHRWERT_FELDER = [
    ("gesättigte", "gesaettigte_fettsaeuren"),
    ("zucker", "zucker"),
    ("ballaststoff", "ballaststoffe"),
    ("kohlenhydrat", "kohlenhydrate"),
    ("eiweiß", "protein"),
    ("eiweiss", "protein"),
    ("protein", "protein"),
    ("fett", "fett"),
    ("salz", "salz"),
]


def parse_naehrwert_tabelle(text: str | None) -> Naehrwerte | None:
    """Parst Tabellen im Format 'Energie | ca. 296kJ | ca. 70kcal<br />Eiweiß | ca. 12g<br />…'.

    Werte wie '< 0,5g' werden als 0,5 übernommen (Obergrenze).
    """
    if not text:
        return None
    text = html.unescape(text)
    nw = Naehrwerte()
    gefunden = False
    for zeile in re.split(r"<br\s*/?>|\n", text):
        teile = [t.strip() for t in zeile.split("|")]
        if len(teile) < 2:
            continue
        label = teile[0].lower()
        if label.startswith("energie") or "brennwert" in label:
            for wert in teile[1:]:
                m = _ZAHL_RE.search(wert)
                if m and (m.group(2) or "").lower() == "kcal":
                    nw.kcal = float(m.group(1).replace(",", "."))
                    gefunden = True
            continue
        for stichwort, feld in _NAEHRWERT_FELDER:
            if stichwort in label:
                m = _ZAHL_RE.search(teile[1])
                if m:
                    wert = float(m.group(1).replace(",", "."))
                    if (m.group(2) or "").lower() == "mg":
                        wert /= 1000
                    setattr(nw, feld, wert)
                    gefunden = True
                break
    return nw if gefunden else None


class Store(ABC):
    name: str

    @abstractmethod
    def fetch_raw(self, query: str) -> list[dict]:
        """Rohdaten von der Kette holen."""

    @abstractmethod
    def parse(self, raw: dict) -> Angebot | None:
        """Einen Roh-Eintrag ins einheitliche Modell übersetzen."""

    def angebote(self, query: str) -> list[Angebot]:
        return [a for r in self.fetch_raw(query) if (a := self.parse(r)) is not None]


def get_mit_wiederholung(client, url: str, versuche: int = 4, warte: float = 3.0, max_warte: float = 60.0):
    """GET mit Wiederholung bei Verbindungsabbrüchen, 5xx-Fehlern und 429 (zu viele Anfragen).

    Bei 429 wird so lange gewartet, wie der Server per Retry-After verlangt (höchstens max_warte Sekunden).
    """
    import time

    import httpx

    for i in range(versuche):
        pause = warte * (i + 1)
        try:
            r = client.get(url)
            if r.status_code == 429:
                try:
                    pause = min(max_warte, float(r.headers.get("retry-after", pause * 3)))
                except ValueError:
                    pause = min(max_warte, pause * 3)
            elif r.status_code < 500:
                return r
            if i == versuche - 1:
                return r
        except httpx.TransportError:
            if i == versuche - 1:
                raise
        time.sleep(pause)
