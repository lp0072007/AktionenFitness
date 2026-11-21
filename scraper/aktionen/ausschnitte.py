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


def _mitte(r: Rechteck) -> tuple[float, float]:
    return (r.x0 + r.x1) / 2, (r.top + r.bottom) / 2


def _abstand(a: Rechteck, b: Rechteck) -> float:
    dx = max(0.0, max(a.x0, b.x0) - min(a.x1, b.x1))
    dy = max(0.0, max(a.top, b.top) - min(a.bottom, b.bottom))
    return (dx * dx + dy * dy) ** 0.5


def ausschnitt_bereich(
    a: FlugblattAngebot, bilder: list[Rechteck], seite_breite: float, seite_hoehe: float,
    andere: list[FlugblattAngebot] = (),
) -> Rechteck | None:
    """Bereich = Name + Preis (+ Beschreibung) des Angebots und das Produktfoto darüber.

    Anker ist der Produktname: Texte, die weit weg liegen (falsch zugeordnete Beschreibungen), zählen nicht.
    Fremde Produktnamen werden aus dem Ausschnitt herausgehalten.
    """
    if a.name_bbox is None:
        return _ausschnitt_alt(a, bilder, seite_breite, seite_hoehe, andere)
    name = Rechteck(*a.name_bbox)
    kern = name
    if a.preis_bbox and _abstand(Rechteck(*a.preis_bbox), name) < 140:
        kern = kern.vereinigen(Rechteck(*a.preis_bbox))
    if a.bbox:  # Beschreibung: nur was direkt beim Namen liegt
        g = Rechteck(*a.bbox)
        kern = kern.vereinigen(Rechteck(max(g.x0, name.x0 - 40), max(g.top, kern.top - 40),
                                        min(g.x1, max(kern.x1, name.x1 + 40)), min(g.bottom, name.bottom + 70)))
    fremde = [Rechteck(*o.name_bbox) for o in andere if o is not a and o.name_bbox and o.name != a.name]
    fremde_preise = [Rechteck(*o.preis_bbox) for o in andere if o is not a and o.preis_bbox]
    breite = kern.x1 - kern.x0

    # Obergrenze: Texte anderer Angebote darüber in derselben Spalte
    oben = max(0.0, kern.top - MAX_FOTO_HOEHE)
    for r in fremde + fremde_preise:
        if r.bottom <= kern.top + 2 and _ueberlappung_x(r, kern) > 0.3 * min(breite, r.x1 - r.x0):
            oben = max(oben, r.bottom + 2)

    bereich = kern
    for b in bilder:
        b_breite = b.x1 - b.x0
        if b.flaeche > MAX_BILD_ANTEIL * seite_breite * seite_hoehe or b.flaeche < 400:
            continue                                   # Hintergrund oder Mini-Deko
        if _ueberlappung_x(b, kern) < 0.4 * min(b_breite, breite):
            continue                                   # liegt nicht in dieser Spalte
        if b_breite > 1.8 * breite + 60:
            continue                                   # viel breiter als die Kachel: Layout
        if b.bottom < kern.top - 60 or b.top > kern.top - 10:
            continue                                   # Foto muss über dem Text beginnen und daran anschließen
        if any(b.x0 < cx < b.x1 and b.top < cy < b.bottom for cx, cy in map(_mitte, fremde)):
            continue                                   # Foto gehört zu einem anderen Angebot
        bereich = bereich.vereinigen(Rechteck(max(b.x0, kern.x0 - 0.6 * breite), max(b.top, oben),
                                              min(b.x1, kern.x1 + 0.6 * breite), b.bottom))
    foto_oben = bereich.top < kern.top - 30
    if not foto_oben:
        # Foto neben dem Text (häufig bei Spar: Text in einer Spalte links/rechts vom Produkt)
        hoehe = kern.bottom - kern.top
        for b in bilder:
            if b.flaeche > MAX_BILD_ANTEIL * seite_breite * seite_hoehe or b.flaeche < 1500:
                continue
            senkrecht = min(b.bottom, kern.bottom) - max(b.top, kern.top - 40)
            if senkrecht < 0.4 * min(b.bottom - b.top, hoehe):
                continue                               # nicht auf Höhe des Textes
            links = b.x1 <= kern.x0 + 0.3 * breite and b.x1 >= kern.x0 - 30
            rechts = b.x0 >= kern.x1 - 0.3 * breite and b.x0 <= kern.x1 + 30
            if not (links or rechts) or (b.x1 - b.x0) > 2.2 * breite + 80:
                continue
            if any(b.x0 < cx < b.x1 and b.top < cy < b.bottom for cx, cy in map(_mitte, fremde)):
                continue
            eigen = _abstand(b, kern)
            if any(_abstand(b, f) < eigen - 5 for f in fremde + fremde_preise):
                continue                               # liegt näher an einem anderen Angebot: dessen Foto
            bereich = bereich.vereinigen(Rechteck(b.x0, max(b.top, oben), b.x1, min(b.bottom, kern.bottom + 40)))
    if bereich.top > kern.top - 30 and bereich.x1 - bereich.x0 < breite + 40 and oben < kern.top - 40:
        # Kein eigenes Foto gefunden (z. B. Teil eines großen Hintergrundbildes): Bereich über dem Text nehmen
        hoehe = min(kern.top - oben, max(90.0, 0.9 * breite))
        bereich = bereich.vereinigen(Rechteck(kern.x0, kern.top - hoehe, kern.x1, kern.top))

    # Fremde Namen heraushalten: daneben -> seitlich abschneiden, darüber/darunter -> oben/unten abschneiden
    for f in fremde:
        cx, cy = _mitte(f)
        if not (bereich.x0 < cx < bereich.x1 and bereich.top < cy < bereich.bottom):
            continue
        if f.top < kern.bottom and f.bottom > kern.top:        # gleiche Höhe wie unser Text: seitlich
            if cx > _mitte(name)[0]:
                bereich = Rechteck(bereich.x0, bereich.top, max(kern.x1, min(bereich.x1, f.x0 - 2)), bereich.bottom)
            else:
                bereich = Rechteck(min(kern.x0, max(bereich.x0, f.x1 + 2)), bereich.top, bereich.x1, bereich.bottom)
        elif cy < name.top:
            bereich = Rechteck(bereich.x0, max(bereich.top, f.bottom + 2), bereich.x1, bereich.bottom)
        else:
            bereich = Rechteck(bereich.x0, bereich.top, bereich.x1, max(kern.bottom, min(bereich.bottom, f.top - 2)))
    return Rechteck(
        max(0, bereich.x0 - RAND), max(0, bereich.top - RAND),
        min(seite_breite, bereich.x1 + RAND), min(seite_hoehe, bereich.bottom + RAND),
    )


def _ausschnitt_alt(
    a: FlugblattAngebot, bilder: list[Rechteck], seite_breite: float, seite_hoehe: float,
    andere: list[FlugblattAngebot] = (),
) -> Rechteck | None:
    """Alte Variante ohne Namens-Anker (für Angebote ohne name_bbox)."""
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
                          nur: set[int] | None = None, max_breite: int = 640, fortschritt=None) -> dict[int, Path]:
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

    if fortschritt:
        fortschritt.setze(0, len(nach_seite))
    with pdfplumber.open(pdf_pfad) as pdf:
        for nr, indizes in nach_seite.items():
            if fortschritt:
                fortschritt.weiter()
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
    if fortschritt:
        fortschritt.fertig(f"{len(ergebnis)} Ausschnitte")
    return ergebnis
