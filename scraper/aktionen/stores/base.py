"""Gemeinsame Basis für alle Ketten-Scraper."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from ..models import Angebot

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
