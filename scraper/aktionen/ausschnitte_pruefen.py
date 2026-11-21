"""Qualität der Flugblatt-Ausschnitte messen.

    python -m aktionen.ausschnitte_pruefen ../data/spar_wien_kw47.pdf [weitere.pdf …] [-v]

Ein Ausschnitt gilt als schlecht, wenn der eigene Name fehlt, ein fremder Produktname drin ist (nicht in derselben
Zeile, z. B. "Milka Nikolo oder Krampus"), kein Foto drin ist oder er über ein Viertel der Seite groß ist.
"kein Foto" ist manchmal falsch: Fotos, die Teil eines großen Hintergrundbildes sind, erkennt die Messung nicht.
"""

from __future__ import annotations

import argparse

from .ausschnitte import MAX_BILD_ANTEIL, Rechteck, ausschnitt_bereich
from .export import angebote_aus_pdf


def pruefen(pdf_pfad: str) -> list[tuple[int, str, list[str]]]:
    import pdfplumber

    ergebnis = []
    angebote = angebote_aus_pdf(pdf_pfad)
    with pdfplumber.open(pdf_pfad) as pdf:
        for nr in sorted({a.seite for a in angebote}):
            page = pdf.pages[nr - 1]
            breite, hoehe = float(page.width), float(page.height)
            bilder = [Rechteck(b["x0"], b["top"], b["x1"], b["bottom"]) for b in page.images]
            fotos = [b for b in bilder if 400 <= b.flaeche <= MAX_BILD_ANTEIL * breite * hoehe]
            gleiche = [a for a in angebote if a.seite == nr]
            for a in gleiche:
                k = ausschnitt_bereich(a, bilder, breite, hoehe, gleiche)
                if k is None or a.name_bbox is None:
                    continue
                fehler = []
                n = Rechteck(*a.name_bbox)
                if k.schnitt(n) < 0.9 * n.flaeche:
                    fehler.append("eigener Name fehlt")
                for o in gleiche:
                    if o is a or not o.name_bbox or o.name == a.name:
                        continue
                    on = Rechteck(*o.name_bbox)
                    cx, cy = (on.x0 + on.x1) / 2, (on.top + on.bottom) / 2
                    if k.x0 < cx < k.x1 and k.top < cy < k.bottom and abs(cy - (n.top + n.bottom) / 2) > 25:
                        fehler.append(f"fremder Name ({o.name[:20]})")
                        break
                if sum(k.schnitt(f) for f in fotos) < 0.12 * k.flaeche:
                    fehler.append("kein Foto")
                if k.flaeche > 0.25 * breite * hoehe:
                    fehler.append("zu groß")
                ergebnis.append((nr, a.name, fehler))
    return ergebnis


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m aktionen.ausschnitte_pruefen")
    p.add_argument("pdf", nargs="+")
    p.add_argument("-v", action="store_true", help="schlechte Ausschnitte einzeln auflisten")
    args = p.parse_args(argv)
    gesamt = schlecht = 0
    for pfad in args.pdf:
        for nr, name, fehler in pruefen(pfad):
            gesamt += 1
            if fehler:
                schlecht += 1
                if args.v:
                    print(f"  S{nr:<3} {name[:40]:<40} {', '.join(fehler)}")
    print(f"{gesamt} Ausschnitte, {schlecht} schlecht ({100 * schlecht / max(gesamt, 1):.0f} %)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
