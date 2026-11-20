"""Einheitliches Datenmodell für alle Ketten."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date


@dataclass
class Naehrwerte:
    """Nährwerte pro 100 g bzw. 100 ml."""

    kcal: float | None = None
    protein: float | None = None
    kohlenhydrate: float | None = None
    zucker: float | None = None
    fett: float | None = None
    gesaettigte_fettsaeuren: float | None = None
    ballaststoffe: float | None = None
    salz: float | None = None


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
    tags: list[str] = field(default_factory=list)  # z. B. "vegan", "lactose-free", "preisgesenkt"
    kategorie: str | None = None
    naehrwerte: Naehrwerte | None = None

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

    def _pro_euro(self, wert_pro_100: float | None) -> float | None:
        if wert_pro_100 is None or not self.menge or self.einheit not in ("g", "ml") or not self.preis:
            return None
        return round(wert_pro_100 * self.menge / 100 / self.preis, 1)

    @property
    def protein_pro_euro(self) -> float | None:
        """Gramm Protein, die man für 1 € bekommt."""
        return self._pro_euro(self.naehrwerte.protein if self.naehrwerte else None)

    @property
    def kcal_pro_euro(self) -> float | None:
        return self._pro_euro(self.naehrwerte.kcal if self.naehrwerte else None)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["gueltig_bis"] = self.gueltig_bis.isoformat() if self.gueltig_bis else None
        d["ist_aktion"] = self.ist_aktion
        d["rabatt_prozent"] = self.rabatt_prozent
        d["preis_pro_kg"] = self.preis_pro_kg
        d["protein_pro_euro"] = self.protein_pro_euro
        d["kcal_pro_euro"] = self.kcal_pro_euro
        return d
