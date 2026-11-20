"""Penny Österreich: Aktionsangebote über die Produkt-Schnittstelle von penny.at.

    GET https://www.penny.at/api/product-discovery/categories/alle-angebote-99000000/products?page=0&pageSize=100

Antwort: {"total": 591, "count": …, "offset": …, "results": [Produkt, …]}. Pro Produkt u. a.:
    name, brand.name, amount + volumeLabelShort ("250" + "g"), weightArticle (Kilo-Ware),
    price.regular.value (Cent), price.regular.promotionText ("ab 2 Becher"), price.regular.promotionQuantity,
    price.crossed (Streichpreis, Cent), price.discountPercentage (-33),
    price.validityStart/validityEnd ("2026-11-19"), images[], slug, sku, parentCategories.

Penny gehört wie Billa zur Rewe-Gruppe (gleiche Plattform). Angebote gelten österreichweit.
Von Cloud- und Heim-IP aus erreichbar (getestet 20.11.2026).
"""

from __future__ import annotations

import time
from datetime import date

import httpx

from ..flugblatt_pdf import FlugblattAngebot
from .base import USER_AGENT, get_mit_wiederholung

BASIS = "https://www.penny.at"
KATEGORIE = "alle-angebote-99000000"
UA = USER_AGENT
SEITENGROESSE = 100
_NICHT_LEBENSMITTEL = {"Haushalt", "Non-Food", "Haustier", "Pflege", "Drogerie"}
_EINHEITEN = {"g": (1, "g"), "kg": (1000, "g"), "ml": (1, "ml"), "liter": (1000, "ml"), "l": (1000, "ml"),
              "stk": (1, "stk")}


def _hauptkategorie(p: dict) -> str | None:
    for pfad in p.get("parentCategories") or []:
        if pfad and pfad[0].get("name") not in (None, "Alle Angebote"):
            return pfad[0]["name"]
    return None


def parse_produkt(p: dict) -> FlugblattAngebot | None:
    preis_info = p.get("price") or {}
    regulaer = preis_info.get("regular") or {}
    if regulaer.get("value") is None or _hauptkategorie(p) in _NICHT_LEBENSMITTEL:
        return None
    preis = regulaer["value"] / 100

    marke = ((p.get("brand") or {}).get("name") or "").strip()
    name = (p.get("name") or "").replace("*", "").strip()
    if marke and marke.lower() not in name.lower():
        name = f"{marke} {name}"

    pro_kg = bool(p.get("weightArticle"))
    menge = einheit = None
    if not pro_kg:
        faktor_einheit = _EINHEITEN.get((p.get("volumeLabelShort") or "").lower())
        try:
            anzahl = float(str(p.get("amount") or "").replace(",", "."))
        except ValueError:
            anzahl = None
        if faktor_einheit and anzahl:
            menge, einheit = anzahl * faktor_einheit[0], faktor_einheit[1]

    ab_menge = None
    if regulaer.get("promotionType") in ("FROM", "PER_SET_OF") and (regulaer.get("promotionQuantity") or 0) > 1:
        ab_menge = int(regulaer["promotionQuantity"])

    crossed = preis_info.get("crossed")
    normalpreis = crossed / 100 if crossed and crossed / 100 > preis else None

    aktion = []
    if preis_info.get("discountPercentage"):
        aktion.append(f"{preis_info['discountPercentage']}%")
    if ab_menge:
        aktion.append("MENGENVORTEIL")

    beschreibung = " · ".join(
        t for t in (p.get("descriptionShort"), regulaer.get("promotionText"), p.get("bundleInfo")) if t
    )
    von, bis = preis_info.get("validityStart"), preis_info.get("validityEnd")
    bilder = p.get("images") or []
    return FlugblattAngebot(
        seite=0,
        name=name,
        preis=round(preis, 2),
        beschreibung=beschreibung,
        normalpreis=round(normalpreis, 2) if normalpreis else None,
        ab_menge=ab_menge,
        aktion=aktion,
        menge=menge,
        einheit=einheit,
        pro_kg=pro_kg,
        grundpreis_ok=True,  # strukturierte Daten vom Händler
        gueltig_von=date.fromisoformat(von) if von else None,
        gueltig_bis=date.fromisoformat(bis) if bis else None,
        bild_url=bilder[0] if bilder else None,
        url=f"{BASIS}/produkte/{p['slug']}" if p.get("slug") else None,
        produkt_id=p.get("sku") or p.get("productId"),
    )


def aktuelle_angebote(heute: date | None = None, tage_voraus: int = 10, client: httpx.Client | None = None,
                      pause: float = 1.0) -> list[FlugblattAngebot]:
    """Alle Lebensmittel-Aktionen, die heute gelten oder in den nächsten `tage_voraus` Tagen starten."""
    heute = heute or date.today()
    client = client or httpx.Client(headers={"User-Agent": UA, "Accept": "application/json"}, timeout=60)
    gesehen: dict[str, FlugblattAngebot] = {}
    sorten: set[tuple] = set()
    seite = 0
    while True:
        url = f"{BASIS}/api/product-discovery/categories/{KATEGORIE}/products?page={seite}&pageSize={SEITENGROESSE}"
        r = get_mit_wiederholung(client, url)
        r.raise_for_status()
        daten = r.json()
        for p in daten.get("results") or []:
            a = parse_produkt(p)
            if a is None or not a.produkt_id or a.produkt_id in gesehen:
                continue
            if a.gueltig_bis and a.gueltig_bis < heute:
                continue
            if a.gueltig_von and (a.gueltig_von - heute).days > tage_voraus:
                continue
            # Sorten mit gleichem Namen, Preis, Menge und Zeitraum nur einmal (z. B. "Teigwaren" in 3 Formen)
            schluessel = (a.name, a.preis, a.menge, a.gueltig_von)
            if schluessel in sorten:
                continue
            sorten.add(schluessel)
            gesehen[a.produkt_id] = a
        seite += 1
        if not daten.get("results") or seite * SEITENGROESSE >= (daten.get("total") or 0):
            break
        time.sleep(pause)
    return list(gesehen.values())
