"""Bildausschnitte der Angebote aus dem Flugblatt-PDF, genau so, wie sie im Flugblatt aussehen.

Für jedes Angebot gibt es einen Textbereich (bbox: Name, Beschreibung, Preis, Aktion). Dazu kommt das Produktfoto:
die Bilder der Seite, die über dem Namen in derselben Spalte liegen. Seitenfüllende Hintergründe werden ignoriert.
Die Seite wird gerendert und dieser Bereich als JPEG gespeichert.

Hinweis: Die Bilder gehören dem Händler. Für den privaten Gebrauch ok, für eine öffentliche Seite Rechte klären.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .flugblatt_pdf import FlugblattAngebot

AUFLOESUNG = 144          # dpi beim Rendern (PDF-Punkte * 2)
MAX_FOTO_HOEHE = 230      # so weit über dem Namen wird nach dem Produktfoto gesucht (PDF-Punkte)
MAX_BILD_ANTEIL = 0.30    # Bilder größer als 30 % der Seite gelten als Hintergrund
RAND = 6


@dataclass
class Rechteck:
    x0: float
    top: float
    x1: float
    bottom: float

    @property
    def flaeche(self) -> float:
        return max(0.0, self.x1 - self.x0) * max(0.0, self.bottom - self.top)

    def vereinigen(self, o: "Rechteck") -> "Rechteck":
        return Rechteck(min(self.x0, o.x0), min(self.top, o.top), max(self.x1, o.x1), max(self.bottom, o.bottom))

    def schnitt(self, o: "Rechteck") -> float:
        return Rechteck(max(self.x0, o.x0), max(self.top, o.top), min(self.x1, o.x1), min(self.bottom, o.bottom)).flaeche \
            if self.x0 < o.x1 and o.x0 < self.x1 and self.top < o.bottom and o.top < self.bottom else 0.0


def _ueberlappung_x(a: Rechteck, b: Rechteck) -> float:
    return max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0))


def ausschnitt_bereich(
    a: FlugblattAngebot, bilder: list[Rechteck], seite_breite: float, seite_hoehe: float,
    andere: list[FlugblattAngebot] = (),
) -> Rechteck | None:
    """Bereich = Textbereich des Angebots + Produktfoto direkt darüber, begrenzt durch die Angebote darüber."""
    if a.bbox is None:
        return None
    text = Rechteck(*a.bbox)
    breite = text.x1 - text.x0

    # Obergrenze: Unterkante des nächsten Angebots darüber in derselben Spalte
    oben = max(0.0, text.top - MAX_FOTO_HOEHE)
    for o in andere:
        if o is a or not o.bbox:
            continue
        r = Rechteck(*o.bbox)
        if r.bottom <= text.top + 5 and _ueberlappung_x(r, text) > 0.3 * min(breite, r.x1 - r.x0):
            oben = max(oben, r.bottom + 2)

    bereich = text
    for b in bilder:
        b_breite = b.x1 - b.x0
        if b.flaeche > MAX_BILD_ANTEIL * seite_breite * seite_hoehe or b.flaeche < 400:
            continue                                   # Hintergrund oder Mini-Deko
        if _ueberlappung_x(b, text) < 0.75 * min(b_breite, breite):
            continue                                   # liegt nicht (überwiegend) in dieser Spalte
        if b_breite > 1.6 * breite:
            continue                                   # breiter als die Kachel: gehört zum Layout
        if b.bottom < text.top - 40 or b.top > text.top - 10:
            continue                                   # Foto muss über dem Text beginnen und daran anschließen
        bereich = bereich.vereinigen(Rechteck(b.x0, max(b.top, oben), b.x1, b.bottom))
    return Rechteck(
        max(0, bereich.x0 - RAND), max(0, max(bereich.top, oben) - RAND),
        min(seite_breite, bereich.x1 + RAND), min(seite_hoehe, bereich.bottom + RAND),
    )


def ausschnitte_speichern(pdf_pfad, angebote: list[FlugblattAngebot], ordner: Path, praefix: str,
                          nur: set[int] | None = None, max_breite: int = 640) -> dict[int, Path]:
    """Speichert die Ausschnitte als JPEG. Rückgabe: Index in `angebote` -> Datei.

    nur: Indizes der Angebote, für die Bilder erzeugt werden sollen (z. B. nur die fitnessrelevanten).
    """
    import pdfplumber

    ordner.mkdir(parents=True, exist_ok=True)
    ergebnis: dict[int, Path] = {}
    nach_seite: dict[int, list[int]] = {}
    for i, a in enumerate(angebote):
        if nur is None or i in nur:
            nach_seite.setdefault(a.seite, []).append(i)

    with pdfplumber.open(pdf_pfad) as pdf:
        for nr, indizes in nach_seite.items():
            page = pdf.pages[nr - 1]
            bilder = [Rechteck(b["x0"], b["top"], b["x1"], b["bottom"]) for b in page.images]
            gleiche_seite = [a for a in angebote if a.seite == nr]
            bild = page.to_image(resolution=AUFLOESUNG).original.convert("RGB")
            faktor = bild.width / float(page.width)
            for i in indizes:
                r = ausschnitt_bereich(angebote[i], bilder, float(page.width), float(page.height), gleiche_seite)
                if r is None:
                    continue
                teil = bild.crop((int(r.x0 * faktor), int(r.top * faktor), int(r.x1 * faktor), int(r.bottom * faktor)))
                if teil.width > max_breite:
                    teil = teil.resize((max_breite, round(teil.height * max_breite / teil.width)))
                ziel = ordner / f"{praefix}-s{nr}-{i}.jpg"
                teil.save(ziel, "JPEG", quality=82, optimize=True)
                ergebnis[i] = ziel
    return ergebnis
