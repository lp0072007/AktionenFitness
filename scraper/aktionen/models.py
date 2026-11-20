"""Einheitliches Datenmodell für alle Ketten."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date


@dataclass
class Angebot:
    kette: str                       # "spar", "billa", ...
    produkt_id: str                  # Produktnummer der Kette
    name: str
    preis: float                     # aktueller Preis in EUR
    marke: str | None = None
    menge: float | None = None       # z. B. 450
    einheit: str | None = None       # "g", "ml", "stk"
    normalpreis: float | None = None # Streichpreis, falls Aktion
    aktion_text: str | None = None   # z. B. "-25%", "1+1 gratis"
    gueltig_bis: date | None = None
    ean: str | None = None
    bio: bool = False
    bild_url: str | None = None
    tags: list[str] = field(default_factory=list)  # z. B. "vegan", "lactose-free"

    @property
    def ist_aktion(self) -> bool:
        return self.normalpreis is not None and self.normalpreis > self.preis

    @property
    def rabatt_prozent(self) -> float | None:
        if not self.ist_aktion:
            return None
        return round((1 - self.preis / self.normalpreis) * 100, 1)

    @property
    def preis_pro_kg(self) -> float | None:
        """Preis pro kg bzw. Liter (nur für g/ml)."""
        if not self.menge or self.einheit not in ("g", "ml"):
            return None
        return round(self.preis / self.menge * 1000, 2)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["gueltig_bis"] = self.gueltig_bis.isoformat() if self.gueltig_bis else None
        d["ist_aktion"] = self.ist_aktion
        d["rabatt_prozent"] = self.rabatt_prozent
        return d
