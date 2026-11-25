"""Echte Nährwerte (pro 100 g/ml) statt Richtwerten – nur für fitnessrelevante Angebote.

Quellen (untersucht 25.11.2026, siehe docs/DATENQUELLEN.md):
    Billa   Produktdetail  GET shop.billa.at/api/product-discovery/products/<sku>
            -> additionalInformation[].foodInformation.nutritionInfos[].nutrients[]   (Stichprobe 40/40)
    MPreis  steckt schon in der Suche (mixins.markantAttributes.data.nutrient)          (ca. 2/3 der Aktionen)
    Lidl    keine Nährwerte, aber EAN auf der Produktseite (JSON-LD "gtin13") -> Open Food Facts
    Open Food Facts  GET world.openfoodfacts.org/api/v2/product/<ean>.json  (freie Datenbank, Lizenz ODbL)
    Penny, Hofer: keine Nährwerte und keine EAN online -> Richtwerte der Kategorie (fitness.py)

Jedes Produkt wird nur einmal abgefragt: Ergebnisse (auch "nichts gefunden") liegen im Zwischenspeicher
data/naehrwerte.json, "nichts gefunden" wird nach 30 Tagen erneut versucht.
"""

from __future__ import annotations

import html
import json
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import httpx

from .models import Naehrwerte

CACHE_PFAD = Path(__file__).resolve().parents[2] / "data" / "naehrwerte.json"
OFF_UA = "AktionenFitness/0.1 (+https://github.com/lp0072007/AktionenFitness)"  # Open Food Facts verlangt eine Kennung
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0 Safari/537.36"
NOCHMAL_NACH_TAGEN = 30
VERSION = 3  # erhöhen, wenn sich die Auswertung ändert -> alte Einträge werden neu geholt (3: zubereitet markiert)

QUELLE_HAENDLER = "Etikett"            # Angabe des Händlers
QUELLE_OFF = "Open Food Facts"
ZUBEREITET = " (zubereitet)"   # Zusatz zur Quelle: Werte gelten für das zubereitete Produkt


# ---------- Plausibilität ----------

def plausibel(nw: Naehrwerte | None) -> bool:
    """Grobe Prüfung gegen Tippfehler/Unsinn: Werte im möglichen Bereich, kcal passen ungefähr zu den Makros."""
    if nw is None or nw.kcal is None or nw.protein is None:
        return False
    if not (0 <= nw.kcal <= 950 and 0 <= nw.protein <= 100):
        return False
    makros = [x for x in (nw.protein, nw.kohlenhydrate, nw.fett) if x is not None]
    if any(x < 0 or x > 100 for x in makros) or sum(makros) > 105:
        return False
    if nw.kohlenhydrate is not None and nw.fett is not None:  # ±15 kcal Spielraum: Wasser, Light-Getränke
        # Atwater: 4 kcal/g Eiweiß und Kohlenhydrate, 9 kcal/g Fett (Ballaststoffe/Alkohol/Zuckeralkohole -> großzügig)
        geschaetzt = 4 * nw.protein + 4 * nw.kohlenhydrate + 9 * nw.fett
        if not (0.6 * nw.kcal - 15 <= geschaetzt <= 1.4 * nw.kcal + 15):
            return False
    return True


def _zahl(x) -> float | None:
    try:
        return round(float(str(x).replace(",", ".")), 1)
    except (TypeError, ValueError):
        return None


# ---------- Billa ----------

def aus_billa(detail: dict) -> tuple[Naehrwerte | None, bool]:
    """Produktdetail von shop.billa.at -> (Nährwerte pro 100 g/ml, zubereitet?). Unzubereitet wird bevorzugt."""
    tabellen = [ni for info in detail.get("additionalInformation") or []
                for ni in ((info or {}).get("foodInformation") or {}).get("nutritionInfos") or []]
    # Pro 100 g/ml; "wie verkauft" zuerst. Nur zubereitete Werte (gekochter Reis 155 statt 355 kcal, TK-Gemüse ≈ gleich)
    # werden markiert – fitness.py entscheidet je Produktart, ob sie taugen.
    tabellen = [t for t in tabellen if (t.get("relationValue") or 100) == 100]
    tabellen.sort(key=lambda t: (t.get("preparationGrade") or "Unzubereitet") != "Unzubereitet")
    for t in tabellen:
        zubereitet = (t.get("preparationGrade") or "Unzubereitet") != "Unzubereitet"
        nw = Naehrwerte()
        for n in t.get("nutrients") or []:
            name, wert, einheit = (n.get("name") or "").strip(), _zahl(n.get("value")), (n.get("unit") or {}).get("symbol")
            if name == "Energie" and einheit == "kcal":
                nw.kcal = wert
            elif name == "Eiweiß":
                nw.protein = wert
            elif name == "Kohlenhydrate":
                nw.kohlenhydrate = wert
            elif name == "Fett":
                nw.fett = wert
            elif name.startswith("davon Zucker"):
                nw.zucker = wert
        if plausibel(nw):
            return nw, zubereitet
    return None, False


# ---------- MPreis ----------

def aus_mpreis(nutrient: dict | None) -> tuple[Naehrwerte | None, bool]:
    """mixins.markantAttributes.data.nutrient aus der MPreis-Suche -> (Nährwerte, zubereitet?)."""
    koepfe = [k for k in ((nutrient or {}).get("nutrientHeader") or {}).values()
              if (k.get("nutrientBasisQuantity") or 100) == 100]
    # "UnpreparedNormed" zuerst, "PreparedNormed" (z. B. gekochter Reis) nur als Ersatz – markiert
    koepfe.sort(key=lambda k: not (k.get("preparationState") or "Unprepared").startswith("Unprepared"))
    for kopf in koepfe:
        zubereitet = not (kopf.get("preparationState") or "Unprepared").startswith("Unprepared")
        nw = Naehrwerte(kcal=_zahl(kopf.get("energyKcal")))
        for inhalt in (kopf.get("nutrientContent") or {}).values():
            typ = html.unescape(inhalt.get("nutrientType") or "").replace("\xa0", " ").strip()
            wert = _zahl(inhalt.get("quantityContained"))
            if typ == "Eiweiß":
                nw.protein = wert
            elif typ == "Kohlenhydrate":
                nw.kohlenhydrate = wert
            elif typ == "Fett":
                nw.fett = wert
            elif typ.endswith("davon Zucker"):
                nw.zucker = wert
        if plausibel(nw):
            return nw, zubereitet
    return None, False


# ---------- Open Food Facts ----------

def aus_off(antwort: dict) -> Naehrwerte | None:
    n = (antwort.get("product") or {}).get("nutriments") or {}
    nw = Naehrwerte(kcal=_zahl(n.get("energy-kcal_100g")), protein=_zahl(n.get("proteins_100g")),
                    kohlenhydrate=_zahl(n.get("carbohydrates_100g")), fett=_zahl(n.get("fat_100g")),
                    zucker=_zahl(n.get("sugars_100g")))
    return nw if plausibel(nw) else None


def ean_aus_lidl_seite(seite: str) -> str | None:
    """Lidl-Produktseite: JSON-LD {"@type":"Product", "gtin13":["4002566003118"]}."""
    m = re.search(r'"gtin13"\s*:\s*\[?\s*"(\d{8,14})"', seite)
    return m.group(1) if m else None


# ---------- Zwischenspeicher ----------

class Speicher:
    """Ergebnisse pro Produkt: {"kette:id": {"nw": {...} | null, "quelle": ..., "ean": ..., "datum": "2026-11-25"}}"""

    def __init__(self, pfad: Path = CACHE_PFAD):
        self.pfad = pfad
        try:
            self.daten: dict = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.daten = {}
        self.neu = 0

    def holen(self, schluessel: str, heute: date) -> dict | None:
        e = self.daten.get(schluessel)
        if not e or e.get("v") != VERSION:
            return None
        if e.get("nw") is None and date.fromisoformat(e["datum"]) < heute - timedelta(days=NOCHMAL_NACH_TAGEN):
            return None  # damals nichts gefunden -> wieder versuchen
        return e

    def setzen(self, schluessel: str, nw: Naehrwerte | None, quelle: str | None, ean: str | None, heute: date) -> dict:
        e = {"nw": _als_dict(nw), "quelle": quelle if nw else None, "ean": ean, "datum": heute.isoformat(), "v": VERSION}
        self.daten[schluessel] = e
        self.neu += 1
        return e

    def speichern(self) -> None:
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        self.pfad.write_text(json.dumps(self.daten, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def _als_dict(nw: Naehrwerte | None) -> dict | None:
    if nw is None:
        return None
    return {k: v for k, v in (("kcal", nw.kcal), ("protein", nw.protein), ("kohlenhydrate", nw.kohlenhydrate),
                              ("fett", nw.fett), ("zucker", nw.zucker)) if v is not None}


def _aus_dict(d: dict | None) -> Naehrwerte | None:
    return Naehrwerte(**d) if d else None


# ---------- Anreichern ----------

class Abrufer:
    """Holt fehlende Nährwerte höflich (Pausen, wenige Anfragen) und merkt sich alles im Speicher."""

    def __init__(self, speicher: Speicher, heute: date | None = None, pause: float = 0.3,
                 haendler: httpx.Client | None = None, off: httpx.Client | None = None):
        self.speicher, self.heute, self.pause = speicher, heute or date.today(), pause
        self.haendler = haendler or httpx.Client(headers={"User-Agent": BROWSER_UA}, timeout=30, follow_redirects=True)
        self.off = off or httpx.Client(headers={"User-Agent": OFF_UA}, timeout=30)

    def _off(self, ean: str | None) -> Naehrwerte | None:
        if not ean:
            return None
        try:
            r = self.off.get(f"https://world.openfoodfacts.org/api/v2/product/{ean}.json",
                             params={"fields": "nutriments"})
            time.sleep(self.pause)
            return aus_off(r.json()) if r.status_code == 200 else None
        except (httpx.HTTPError, ValueError):
            return None

    def fuer(self, kette: str, angebot) -> None:
        """Setzt angebot.naehrwerte / naehrwerte_quelle / ean, falls eine Quelle etwas liefert."""
        if angebot.naehrwerte is not None:  # MPreis: schon aus der Suche
            return
        schluessel = f"{kette}:{angebot.produkt_id}"
        e = self.speicher.holen(schluessel, self.heute)
        if e is None:
            e = self._abrufen(kette, angebot, schluessel)
        if e and e.get("nw"):
            angebot.naehrwerte, angebot.naehrwerte_quelle = _aus_dict(e["nw"]), e["quelle"]
        if e and e.get("ean") and not angebot.ean:
            angebot.ean = e["ean"]

    def _abrufen(self, kette: str, angebot, schluessel: str) -> dict | None:
        nw = quelle = None
        ean = angebot.ean
        try:
            if kette == "billa":
                r = self.haendler.get(f"https://shop.billa.at/api/product-discovery/products/{angebot.produkt_id}",
                                      headers={"Accept": "application/json"})
                time.sleep(self.pause)
                nw, zubereitet = aus_billa(r.json()) if r.status_code == 200 else (None, False)
                quelle = (QUELLE_HAENDLER + (ZUBEREITET if zubereitet else "")) if nw else None
            elif kette == "lidl" and angebot.url:
                r = self.haendler.get(angebot.url, headers={"Accept": "text/html"})
                time.sleep(self.pause)
                ean = ean_aus_lidl_seite(r.text) if r.status_code == 200 else None
            if nw is None and ean:  # Lidl, MPreis ohne eigene Werte
                nw = self._off(ean)
                quelle = QUELLE_OFF if nw else None
        except (httpx.HTTPError, ValueError) as e:
            print(f"    Nährwerte {schluessel}: {e}", file=sys.stderr)
            return None  # Netzfehler: nicht merken, nächstes Mal wieder versuchen
        return self.speicher.setzen(schluessel, nw, quelle, ean, self.heute)


def anreichern(kette: str, angebote, abrufer: Abrufer | None) -> None:
    """Für jedes (fitnessrelevante) Angebot echte Nährwerte holen, soweit die Kette welche hat."""
    if abrufer is None or kette not in ("billa", "lidl", "mpreis"):
        return
    for a in angebote:
        abrufer.fuer(kette, a)
