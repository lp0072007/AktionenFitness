"""Prototyp (20.11.2026): Preise im Flugblatt-PDF per Position dem nächsten Produktnamen zuordnen.

Aufruf: python experimente/pdf_preise_proto.py flugblatt.pdf 14 9
Ergebnis NÖ KW47 S. 14: ca. 2 von 5 Zuordnungen richtig, siehe docs/DATENQUELLEN.md.
"""
import sys, re, pdfplumber
from collections import Counter

def analyse(page):
    words = page.extract_words(extra_attrs=["size", "fontname"])
    # 1. Preise: grosse Ganzzahl + rechts daneben kleinere 2-stellige Cents
    preise = []
    for w in words:
        if w["size"] >= 25 and re.fullmatch(r"\d{1,3}", w["text"]):
            cents = [c for c in words if re.fullmatch(r"\d{2}|-", c["text"]) and 12 <= c["size"] < w["size"]
                     and 0 <= c["x0"] - w["x1"] < 12 and abs(c["top"] - w["top"]) < 8]
            if cents:
                c = cents[0]
                preise.append({"wert": float(f'{w["text"]}.{c["text"].replace("-", "00")}'),
                               "x0": w["x0"], "x1": c["x1"], "top": w["top"] - 2, "bottom": w["bottom"]})
    # 2. Titel: Woerter in Titelschrift (Groesse 10.5-12.5), zu Bloecken gruppieren
    titel = [w for w in words if 10.5 <= w["size"] <= 12.5]
    titel.sort(key=lambda w: (round(w["top"]), w["x0"]))
    bloecke = []
    for w in titel:
        for b in bloecke:
            if abs(w["x0"] - b["x0"]) < 120 and 0 <= w["top"] - b["bottom"] < 8 or (abs(w["top"] - b["last_top"]) < 3 and 0 <= w["x0"] - b["x1"] < 15):
                b["text"] += " " + w["text"]; b["x1"] = max(b["x1"], w["x1"]); b["bottom"] = max(b["bottom"], w["bottom"]); b["last_top"] = w["top"]
                break
        else:
            bloecke.append({"text": w["text"], "x0": w["x0"], "x1": w["x1"], "top": w["top"], "bottom": w["bottom"], "last_top": w["top"]})
    # 3. Zuordnung: jeder Preis -> naechster Titelblock (Abstand Mittelpunkte)
    for p in preise:
        px, py = (p["x0"] + p["x1"]) / 2, (p["top"] + p["bottom"]) / 2
        best = min(bloecke, key=lambda b: abs((b["x0"] + b["x1"]) / 2 - px) + 1.5 * abs((b["top"] + b["bottom"]) / 2 - py), default=None)
        print(f'{p["wert"]:7.2f} €  <- {best["text"][:70] if best else "?"}')

with pdfplumber.open(sys.argv[1]) as pdf:
    for n in map(int, sys.argv[2:]):
        print(f"=== Seite {n}")
        analyse(pdf.pages[n - 1])
