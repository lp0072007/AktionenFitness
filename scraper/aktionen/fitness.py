"""Fitness-Auswertung: Welche Angebote lohnen sich für Sportler?

1. Angebot einer Kategorie zuordnen (Stichwörter im Namen). Hat es keine Kategorie, ist es nicht fitnessrelevant.
2. Nährwerte aus der Kategorie (typische Werte pro 100 g, gerundet; echte Produkte weichen ab)
3. Kennzahlen: g Protein pro €, kcal pro €, g Protein pro 100 kcal (Eiweißdichte)

Die Werte sind Richtwerte für den Vergleich und keine Etikettenangaben.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .flugblatt_pdf import FlugblattAngebot
from .models import Naehrwerte


@dataclass(frozen=True)
class Kategorie:
    name: str
    gruppe: str                  # "Protein", "Kohlenhydrate", "Fette"
    stichwoerter: tuple[str, ...]  # Regex, auf den kleingeschriebenen Produktnamen
    kcal: float
    protein: float
    kohlenhydrate: float
    fett: float
    gramm_pro_stueck: float | None = None  # für Stückware (Eier)
    ausschluss: tuple[str, ...] = ()
    mit_beschreibung: bool = False  # Stichwörter auch in der Beschreibung suchen (z. B. "in Sonnenblumenöl")

    @property
    def naehrwerte(self) -> Naehrwerte:
        return Naehrwerte(kcal=self.kcal, protein=self.protein, kohlenhydrate=self.kohlenhydrate, fett=self.fett)


# Reihenfolge wichtig: spezifische Kategorien zuerst. Werte pro 100 g (roh bzw. wie verkauft).
KATEGORIEN: tuple[Kategorie, ...] = (
    Kategorie("Proteinpulver", "Protein", (r"\bwhey\b", r"proteinpulver", r"eiweißpulver"), 380, 75, 8, 6),
    Kategorie("Magertopfen", "Protein", (r"magertopfen", r"topfen.*mager"), 67, 12, 4, 0.2),
    Kategorie("Skyr", "Protein", (r"\bskyr\b",), 63, 11, 4, 0.2, ausschluss=(r"drink", r"alternative")),
    Kategorie("Cottage Cheese", "Protein", (r"cottage",), 95, 10.5, 3, 4.5),
    Kategorie("Hühnerbrust", "Protein", (r"hendl-?filet", r"hühner-?brust", r"hähnchen-?brust", r"hühner-?(innen)?filet",
                                          r"maishendl-?filet", r"hendl-?brust", r"hendl-?innenfilet"), 110, 23, 0, 1.5,
              ausschluss=(r"faschiert", r"nugget", r"paniert", r"cordon", r"knusper")),
    Kategorie("Putenbrust", "Protein", (r"putenbrust", r"putenschnitz", r"puteninnenfilet", r"putenfilet",
                                        r"putengeschnetzelt"), 105, 24, 0, 1,
              ausschluss=(r"faschiert", r"wurst", r"schinken", r"aufschnitt")),
    Kategorie("Geflügel-Faschiertes", "Protein", (r"(puten|hendl|geflügel)-?faschiert",), 150, 19, 0, 8),
    Kategorie("Rind mager", "Protein", (r"rindsschnitzel", r"rinderhüfte", r"rindsfilet", r"rinderfilet",
                                        r"tafelspitz", r"beiried"), 120, 22, 0, 3.5),
    Kategorie("Rinder-Faschiertes", "Protein", (r"rind(er|s)?-?faschiert",), 220, 20, 0, 15),
    Kategorie("Thunfisch in Öl", "Protein", (r"thunfisch.*\bin\b[^.·]*öl",), 200, 24, 0, 11,
              ausschluss=(r"salat", r"pizza", r"creme", r"aufstrich"), mit_beschreibung=True),
    Kategorie("Thunfisch", "Protein", (r"thunfisch",), 110, 24, 0, 1,
              ausschluss=(r"salat", r"pizza", r"creme", r"aufstrich")),
    Kategorie("Garnelen", "Protein", (r"garnele", r"shrimp", r"crevette"), 80, 18, 0, 1),
    Kategorie("Lachs", "Protein", (r"lachs(?!forelle)", r"lachsforelle"), 200, 20, 0, 13,
              ausschluss=(r"geräuchert", r"räucher", r"weißburgunder", r"lammlachs")),
    Kategorie("Magerer Fisch", "Protein", (r"dorsch", r"kabeljau", r"seelachs", r"pangasius", r"zander",
                                           r"goldbrasse", r"forelle", r"saibling"), 95, 19, 0, 2,
              ausschluss=(r"stäbchen", r"paniert", r"backfisch", r"knusper")),
    Kategorie("Eier", "Protein", (r"\beier\b",), 140, 12.5, 0.7, 9.5, gramm_pro_stueck=60,
              ausschluss=(r"likör", r"nudel", r"teigwaren", r"eiergold", r"schoko")),
    Kategorie("Eiweißbrot", "Protein", (r"eiweißbrot", r"proteinbrot", r"eiweiß-?brot"), 260, 21, 9, 13),
    Kategorie("Tofu", "Protein", (r"\btofu\b",), 130, 13, 2, 7.5),
    Kategorie("Linsen & Bohnen", "Protein", (r"linsen", r"kichererbsen", r"kidneybohnen", r"weiße bohnen"),
              330, 23, 50, 1.5, ausschluss=(r"chips", r"suppe")),
    Kategorie("Haferflocken", "Kohlenhydrate", (r"haferflocken", r"porridge"), 370, 13.5, 59, 7,
              ausschluss=(r"riegel", r"keks", r"cookie")),
    Kategorie("Reis", "Kohlenhydrate", (r"\breis\b", r"basmati", r"jasmin(reis)?\b", r"-reis\b"), 350, 7.5, 78, 0.6,
              ausschluss=(r"reiswaffel", r"milchreis", r"reisdrink", r"pfanne", r"express", r"mikrowelle")),
    Kategorie("Nudeln", "Kohlenhydrate", (r"\bpasta\b", r"teigwaren", r"spaghetti", r"penne", r"fusilli",
                                          r"nudeln"), 355, 12.5, 71, 1.5,
              ausschluss=(r"noodles", r"fertig", r"suppe", r"instant", r"croissant", r"crepe", r"bolognese",
                          r"carbonara", r"sauce", r"soße", r"pesto", r"salat")),
    Kategorie("Erdäpfel", "Kohlenhydrate", (r"erdäpfel", r"kartoffel"), 75, 2, 16, 0.1,
              ausschluss=(r"chips", r"püree", r"rösti", r"pommes", r"salat", r"knödel")),
    Kategorie("Bananen", "Kohlenhydrate", (r"banane",), 90, 1.1, 20, 0.3, ausschluss=(r"chips", r"nikolo", r"schoko")),
    Kategorie("Milch", "Protein", (r"\bh?-?milch\b", r"vollmilch", r"magermilch", r"\bh-milch"), 50, 3.4, 4.8, 1.5,
              ausschluss=(r"schoko", r"kakao", r"cacao", r"reis", r"hafer", r"pudding", r"milchreis", r"käse",
                          r"scheiben", r"selektion", r"butter", r"joghurt", r"topfen", r"rahm", r"schlag")),
    Kategorie("Nüsse", "Fette", (r"nusskern", r"mandeln", r"walnüsse", r"cashew", r"haselnüsse"), 620, 18, 12, 54,
              ausschluss=(r"schoko", r"nougat", r"krokant")),
    Kategorie("Erdnussbutter", "Fette", (r"erdnussbutter", r"erdnussmus", r"peanut butter"), 600, 25, 14, 50),
    Kategorie("Olivenöl", "Fette", (r"olivenöl",), 820, 0, 0, 91),
)

# Was nie fitnessrelevant ist, auch wenn ein Stichwort passt
_GLOBAL_AUSSCHLUSS = re.compile(
    r"\b(wein|bier|likör|sekt|prosecco|wodka|whisky|schokolade|pralinen|keks|playmobil|lego|spielset)\b"
)


def kategorie_fuer(name: str, beschreibung: str = "") -> Kategorie | None:
    n = name.lower()
    if _GLOBAL_AUSSCHLUSS.search(n):
        return None
    for k in KATEGORIEN:
        text = f"{n} {beschreibung.lower()}" if k.mit_beschreibung else n
        if any(re.search(s, text) for s in k.stichwoerter) and not any(re.search(a, n) for a in k.ausschluss):
            return k
    return None


@dataclass
class FitnessTreffer:
    angebot: FlugblattAngebot
    kategorie: Kategorie
    gramm: float | None          # Menge in g/ml für den Preis (bei Stückware über gramm_pro_stueck)

    @property
    def preis(self) -> float:
        return self.angebot.preis

    def _pro_euro(self, wert_pro_100: float, preis: float | None = None) -> float | None:
        preis = preis if preis is not None else self.preis
        if not self.gramm or not preis:
            return None
        return round(wert_pro_100 * self.gramm / 100 / preis, 1)

    @property
    def protein_pro_euro(self) -> float | None:
        return self._pro_euro(self.kategorie.protein)

    @property
    def protein_pro_euro_zusatz(self) -> float | None:
        """Mit Zusatzpreis (z. B. Fr/Sa -25%), falls vorhanden."""
        z = self.angebot.zusatzpreis
        return self._pro_euro(self.kategorie.protein, z) if z else None

    @property
    def kcal_pro_euro(self) -> float | None:
        return self._pro_euro(self.kategorie.kcal)

    @property
    def protein_pro_100kcal(self) -> float:
        """Eiweißdichte: hoch = gut für die Diät."""
        return round(self.kategorie.protein / self.kategorie.kcal * 100, 1) if self.kategorie.kcal else 0.0


def _gramm(a: FlugblattAngebot, k: Kategorie) -> float | None:
    if a.menge and a.einheit in ("g", "ml"):
        return a.menge
    if a.menge and a.einheit == "stk" and k.gramm_pro_stueck:
        return a.menge * k.gramm_pro_stueck
    if a.pro_kg:
        return 1000.0
    return None


def fitness_angebote(angebote: list[FlugblattAngebot]) -> list[FitnessTreffer]:
    treffer = []
    for a in angebote:
        k = kategorie_fuer(a.name, a.beschreibung)
        if k:
            treffer.append(FitnessTreffer(a, k, _gramm(a, k)))
    return treffer


ZIELE = {
    # Sortierung: Protein pro Euro (Standard)
    "protein": lambda t: -(t.protein_pro_euro or 0),
    # Diät: nur eiweißreiche Lebensmittel (>= 8 g Protein pro 100 kcal), dann Protein pro Euro
    "diaet": lambda t: (t.protein_pro_100kcal < 8, -(t.protein_pro_euro or 0)),
    # Aufbau: möglichst viele Kalorien pro Euro
    "aufbau": lambda t: -(t.kcal_pro_euro or 0),
}


def rangliste(treffer: list[FitnessTreffer], ziel: str = "protein") -> list[FitnessTreffer]:
    return sorted(treffer, key=ZIELE[ziel])


# --- Befehlszeile --------------------------------------------------------------

DATEN_ORDNER = __import__("pathlib").Path(__file__).resolve().parents[2] / "data"


def _zeile(i: int, t: FitnessTreffer) -> str:
    a = t.angebot
    menge = f"{t.gramm:g} g" if t.gramm else "?"
    if a.pro_kg and t.gramm == 1000:
        menge = "per kg"
    bedingung = []
    if a.ab_menge:
        bedingung.append(f"ab {a.ab_menge} Stk")
    if t.protein_pro_euro_zusatz:
        bedingung.append(f"Zusatzpreis {a.zusatzpreis:.2f} € = {t.protein_pro_euro_zusatz:g} g/€")
    bedingung += a.aktion
    p = f"{t.protein_pro_euro:5.1f}" if t.protein_pro_euro is not None else "    ?"
    k = f"{t.kcal_pro_euro:5.0f}" if t.kcal_pro_euro is not None else "    ?"
    return (f"{i:3d}. {a.name[:44]:44s} {a.preis:6.2f} € {menge:>8s}  {p} g/€  {k} kcal/€  "
            f"{t.protein_pro_100kcal:4.1f}  S.{a.seite:<3d} {' | '.join(bedingung)}")


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    import pdfplumber

    from .flugblatt_pdf import analysiere_seite
    from .spar_flugblatt import REGIONEN, aktuelles_flugblatt, pdf_herunterladen

    p = argparse.ArgumentParser(prog="python -m aktionen.fitness", description="Fitness-Angebote der Woche bei Spar")
    p.add_argument("--region", default="niederoesterreich", choices=sorted(REGIONEN))
    p.add_argument("--pdf", help="Bereits heruntergeladenes Flugblatt-PDF verwenden")
    p.add_argument("--ziel", default="protein", choices=sorted(ZIELE),
                   help="protein = Protein pro €, diaet = eiweißreich zuerst, aufbau = kcal pro €")
    p.add_argument("--gruppe", choices=["Protein", "Kohlenhydrate", "Fette"], help="Nur eine Lebensmittelgruppe")
    args = p.parse_args(argv)

    if args.pdf:
        pfad = args.pdf
    else:
        try:
            fb = aktuelles_flugblatt(args.region)
            print(f"Flugblatt: {fb.flipbook.name} ({fb.flipbook.titel})", file=sys.stderr)
            pfad = pdf_herunterladen(fb, DATEN_ORDNER)
        except Exception as e:  # noqa: BLE001
            print(f"Fehler beim Laden des Flugblatts: {e}", file=sys.stderr)
            return 1

    angebote = []
    with pdfplumber.open(pfad) as pdf:
        for n, seite in enumerate(pdf.pages, start=1):
            woerter = seite.extract_words(use_text_flow=True, extra_attrs=["size", "fontname"])
            angebote += analysiere_seite(woerter, n)

    treffer = fitness_angebote(angebote)
    if args.gruppe:
        treffer = [t for t in treffer if t.kategorie.gruppe == args.gruppe]
    print(f"{len(angebote)} Angebote, davon {len(treffer)} fitnessrelevant\n")
    print(f"{'':5s}{'Produkt':44s} {'Preis':>8s} {'Menge':>8s}  {'Protein':>8s}  {'Energie':>11s}  "
          f"{'P/100kcal':9s} Seite  Aktion")
    for i, t in enumerate(rangliste(treffer, args.ziel), start=1):
        print(_zeile(i, t))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
