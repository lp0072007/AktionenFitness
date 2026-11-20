"""Lidl Österreich: Aktionsangebote von den Angebotsseiten auf lidl.at.

Die Angebotsseiten (z. B. /c/store/aktion/a10107111, /c/store/frische-angebote/a10107118) enthalten jedes Produkt
als JSON im Attribut `data-grid-data`: Titel, Preis, Streichpreis, Packungsgröße ("Je 4x 185 g"),
Grundpreis ("1 kg = 6.47"), Lidl-Plus-Preis, Gültigkeit (Unix-Zeit), Bild.
Die Seiten-Nummern ändern sich jede Woche, deshalb werden die Links von der Startseite gelesen.

Lidl-Angebote gelten österreichweit (regions [1, 2, 3]).
Die Flugblatt-Schnittstelle (endpoints.leaflets.schwarz) enthält strukturierte Produkte nur für Non-Food,
deshalb wird sie hier nicht verwendet.
"""

from __future__ import annotations

import html
import json
import re
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

import httpx

from ..flugblatt_pdf import FlugblattAngebot
from .base import get_mit_wiederholung, parse_menge

BASIS = "https://www.lidl.at"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0 Safari/537.36"
WIEN = ZoneInfo("Europe/Vienna")

_SEITEN_RE = re.compile(r'href="(?:https://www\.lidl\.at)?(/c/store/[a-z0-9-]+/a\d+)"')
_GRID_RE = re.compile(r'data-grid-data="([^"]+)"')
# "Ab 2 Stk. je 500 g (Einzeln = 0.85)", "Bei 2 Stk. je 400 g (Einzeln = 8.99)"
_MENGENAKTION_RE = re.compile(r"(?i)(?:ab|bei)\s+(\d+)\s*Stk\.?\s*je\s+(.+?)\s*\(Einzeln\s*=\s*([\d.,]+)\)")
# Seiten, die sicher keine Lebensmittel-Aktionen enthalten
_IGNORIEREN = ("parkside", "blumen-pflanzen", "baby-kind-spielzeug", "lidl-punkte", "beste-freunde", "funkelnde")


def angebotsseiten(startseite_html: str) -> list[str]:
    seiten = []
    for pfad in _SEITEN_RE.findall(startseite_html):
        if pfad not in seiten and not any(i in pfad for i in _IGNORIEREN):
            seiten.append(pfad)
    return seiten


def produkte_aus_html(seite_html: str) -> list[dict]:
    return [json.loads(html.unescape(m)) for m in _GRID_RE.findall(seite_html)]


def _datum(ts: int | None, ende: bool = False) -> date | None:
    if not ts:
        return None
    return datetime.fromtimestamp(ts, WIEN).date()


def _text(s: str | None) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def parse_produkt(item: dict) -> FlugblattAngebot | None:
    preis_info = item.get("price") or {}
    preis = preis_info.get("price")
    if preis is None or item.get("category") == "NonFood":
        return None

    name = (item.get("fullTitle") or item.get("title") or "").strip(" -–")
    verpackung = ((preis_info.get("packaging") or {}).get("text") or "").strip()

    ab_menge = normalpreis = None
    mengen_text = verpackung
    if m := _MENGENAKTION_RE.search(verpackung):
        ab_menge, mengen_text, normalpreis = int(m.group(1)), m.group(2), float(m.group(3).replace(",", "."))

    pro_kg = bool(re.fullmatch(r"(?i)je\s+kg", mengen_text))
    menge, einheit = (None, None) if pro_kg else parse_menge(mengen_text)

    rabatt = preis_info.get("discount") or {}
    if normalpreis is None:
        alt = preis_info.get("oldPrice") or rabatt.get("deletedPrice")
        normalpreis = float(alt) if alt and float(alt) > preis else None

    aktion = []
    if rabatt.get("discountText"):
        aktion.append(rabatt["discountText"])
    if ab_menge:
        aktion.append("MENGENVORTEIL")

    zusatzpreis = zusatz_text = None
    for lp in item.get("lidlPlus") or []:
        lp_preis = (lp.get("price") or {}).get("price")
        if lp_preis and lp_preis < preis:
            zusatzpreis, zusatz_text = float(lp_preis), "Lidl Plus"
            break

    grundpreis = ((preis_info.get("basePrice") or {}).get("text") or "")
    return FlugblattAngebot(
        seite=0,
        name=name,
        preis=float(preis),
        beschreibung=" · ".join(t for t in (verpackung, grundpreis, _text((item.get("keyfacts") or {}).get("description"))) if t),
        normalpreis=normalpreis,
        ab_menge=ab_menge,
        zusatzpreis=zusatzpreis,
        zusatz_text=zusatz_text,
        aktion=aktion,
        menge=menge,
        einheit=einheit,
        pro_kg=pro_kg,
        grundpreis_ok=True,  # strukturierte Daten vom Händler, keine Zuordnung nötig
        gueltig_von=_datum(item.get("storeStartDate")),
        gueltig_bis=_datum(item.get("storeEndDate")),
        bild_url=item.get("image"),
        url=BASIS + item["canonicalUrl"] if item.get("canonicalUrl") else None,
        produkt_id=str(item.get("productId") or item.get("erpNumber") or ""),
    )


def aktuelle_angebote(heute: date | None = None, tage_voraus: int = 10, client: httpx.Client | None = None,
                      pause: float = 0.3, fortschritt=None) -> list[FlugblattAngebot]:
    """Alle Lebensmittel-Aktionen, die heute gelten oder in den nächsten `tage_voraus` Tagen starten."""
    heute = heute or date.today()
    client = client or httpx.Client(headers={"User-Agent": UA}, timeout=60, follow_redirects=True)
    start = get_mit_wiederholung(client, BASIS + "/")
    start.raise_for_status()
    gesehen: dict[str, FlugblattAngebot] = {}
    seiten = angebotsseiten(start.text)
    for pfad in seiten:
        if fortschritt:
            fortschritt.weiter(1, len(seiten))
        r = get_mit_wiederholung(client, BASIS + pfad)
        if r.status_code != 200:
            continue
        for item in produkte_aus_html(r.text):
            a = parse_produkt(item)
            if a is None or not a.produkt_id or a.produkt_id in gesehen:
                continue
            if a.gueltig_bis and a.gueltig_bis < heute:
                continue
            if a.gueltig_von and (a.gueltig_von - heute).days > tage_voraus:
                continue
            gesehen[a.produkt_id] = a
        time.sleep(pause)  # höflich bleiben
    return list(gesehen.values())
