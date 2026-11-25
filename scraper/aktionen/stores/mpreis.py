"""MPreis: Aktionen über die Produktsuche der Website (Typesense, untersucht 24.11.2026).

    POST https://data-hub.mpreis.at/typesense-proxy/multi_search
    {"searches": [{"collection": "products", "q": "*", "filter_by": "… && $product_store_data(storeId:=8450 && …)",
                   "include_fields": "…,$product_store_data(sitePrice,strategy:nest_array)", "per_page": 250, "page": 1}]}

Kein API-Schlüssel nötig (Proxy von MPreis). Stammdaten in `products`, Preise pro Markt in `product_store_data`
(per Join). Die Preise sind in allen Märkten gleich (stichprobenartig geprüft: 229 Märkte), deshalb reicht der
Standardmarkt der Website (8450). Es gibt keine Gültigkeitsdaten (aktueller Stand, wie Billa).

sitePrice: effective (aktuell), original (Normalpreis), base (Grundpreis), promotionType, isInFlyer,
wholesale.minQuantity ("In der Menge billiger": ab x Stück), discounts.forQuantity/discountQuantity ("1+1 gratis").
Details: docs/DATENQUELLEN.md, Abschnitt MPreis.
"""

from __future__ import annotations

import time
from datetime import date

import httpx

from ..flugblatt_pdf import FlugblattAngebot
from ..naehrwerte import QUELLE_HAENDLER, ZUBEREITET, aus_mpreis
from .base import parse_menge

SUCHE = "https://data-hub.mpreis.at/typesense-proxy/multi_search"
BASIS = "https://www.mpreis.at"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0 Safari/537.36"
MARKT = "8450"                       # Standardmarkt der Website
SEITENGROESSE = 250
# Echte Aktionen. "Immer günstig" und "Dauertiefpreis" sind Dauerpreise und zählen nicht.
AKTIONSTYPEN = ("Preisgesenkt", "In der Menge billiger", "1+1 gratis")
HAUPTKATEGORIEN = ("Lebensmittel", "Getränke")
# Eigenschaften (mixins.mpreisAttributes.properties) -> Merkmale für die Website
_EIGENSCHAFTEN = {"VGN": "vegan", "BIO": "bio"}

FELDER = ",".join([
    "id", "name", "image", "categories", "prices", "mixins.productCustomAttributes.packagingUnit",
    "mixins.productCustomAttributes.weightDependent", "mixins.markantAttributes.data.description.brandName",
    "mixins.mpreisAttributes.properties", "mixins.markantAttributes.data.nutrient", "mixins.markantAttributes.data.gtin",
    "$product_store_data(sitePrice,strategy:nest_array)",
])


def suchanfrage(seite: int, markt: str = MARKT) -> dict:
    typen = ",".join(f"`{t}`" for t in AKTIONSTYPEN)
    kategorien = ",".join(f"`{k}`" for k in HAUPTKATEGORIEN)
    return {"searches": [{
        "collection": "products",
        "q": "*",
        "filter_by": (f"available:true && priceMissing:false && categories:=[{kategorien}] && "
                      f"$product_store_data(storeId:={markt} && "
                      f"(sitePrice.promotionType:=[{typen}] || sitePrice.isInFlyer:true))"),
        "include_fields": FELDER,
        "per_page": SEITENGROESSE,
        "page": seite,
    }]}


def kategorie_pfad(kategorien: list[str]) -> str | None:
    """["Topfen", "Milch & Eier", "Lebensmittel", "ProductRoot"] -> "Lebensmittel > Milch & Eier > Topfen"."""
    teile = [k for k in reversed(kategorien or []) if k != "ProductRoot"]
    return " > ".join(teile) or None


def _aktion(preis: dict) -> tuple[list[str], int | None]:
    """Aktions-Labels und Mindestmenge aus sitePrice."""
    labels: list[str] = []
    ab_menge = None
    rabatt = preis.get("discounts") or {}
    gesamt, gratis = rabatt.get("forQuantity"), rabatt.get("discountQuantity")
    if gesamt and gratis and gesamt > gratis:
        labels.append(f"{gesamt - gratis}+{gratis} GRATIS")   # Typ heißt immer "1+1 gratis", auch bei 2+1
        ab_menge = int(gesamt)
    menge = (preis.get("wholesale") or {}).get("minQuantity")
    if menge and menge > 1:
        ab_menge = int(menge)
        labels.append("MENGENVORTEIL")
    original, effektiv = preis.get("original"), preis.get("effective")
    if preis.get("promotionType") == "Preisgesenkt" and original and effektiv and original > effektiv:
        labels.append(f"-{round((1 - effektiv / original) * 100)}%")
    if preis.get("isInFlyer"):
        labels.append("FLUGBLATT")
    return labels, ab_menge


def parse_produkt(d: dict) -> FlugblattAngebot | None:
    markt = (d.get("product_store_data") or [{}])[0]
    preis = markt.get("sitePrice") or {}
    effektiv = preis.get("effective")
    if not effektiv or effektiv <= 0:
        return None
    mixins = d.get("mixins") or {}
    eigen = mixins.get("productCustomAttributes") or {}
    marke = (((mixins.get("markantAttributes") or {}).get("data") or {}).get("description") or {}).get("brandName")
    name = (d.get("name") or "").strip()
    if marke and marke.lower() not in name.lower():  # auch "MPREIS": nötig für den Filter "keine Eigenmarken"
        name = f"{marke} {name}"

    pro_kg = bool(eigen.get("weightDependent"))
    menge, einheit = (None, None) if pro_kg else parse_menge(eigen.get("packagingUnit"))
    # Thekenware: Preis gilt pro kg ODER pro 100 g (Käse, Wurst, Schinken) – steht in prices.base.unit.
    # "pro 100 g" wie bei Spar-Thekenware als Menge 100 g speichern, sonst wäre der Kilopreis 10-mal zu niedrig.
    basis = ((d.get("prices") or {}).get("base") or {}).get("unit") or {}
    if pro_kg and basis.get("code") == "g" and basis.get("quantity"):
        pro_kg, menge, einheit = False, float(basis["quantity"]), "g"
    # Tippfehler bei MPreis: "175kg" Grieß-Dessert, "360kg" Babybrei (24.11.2026). Über 25 kg und unter 0,20 €/kg
    # ist sicher "g" gemeint – sonst stünden sie beim Sortieren nach Kilopreis ganz oben.
    if menge and einheit in ("g", "ml") and menge >= 25000 and effektiv / menge * 1000 < 0.2:
        menge /= 1000
    original = preis.get("original")
    aktion, ab_menge = _aktion(preis)
    # "Preisgesenkt" ohne niedrigeren Preis = dauerhaft gesenkt, keine Aktion (außer im Flugblatt beworben)
    if not (original and original > effektiv) and not ab_menge and not preis.get("isInFlyer"):
        return None
    merkmale = {_EIGENSCHAFTEN[p] for p in (mixins.get("mpreisAttributes") or {}).get("properties") or []
                if p in _EIGENSCHAFTEN}
    if "vegan" in merkmale:
        merkmale.add("vegetarisch")
    markant = (mixins.get("markantAttributes") or {}).get("data") or {}
    nw, zubereitet = aus_mpreis(markant.get("nutrient"))
    gtin = str(markant.get("gtin") or "").lstrip("0") or None  # "05711953106309" -> EAN-13 ohne führende 0
    if gtin and len(gtin) < 8:
        gtin = None
    return FlugblattAngebot(
        seite=0,
        name=name,
        preis=round(float(effektiv), 2),
        beschreibung=" · ".join(t for t in (eigen.get("packagingUnit"), preis.get("promotionType")) if t),
        normalpreis=round(float(original), 2) if original and original > effektiv else None,
        ab_menge=ab_menge,
        aktion=aktion,
        menge=menge,
        einheit=einheit,
        pro_kg=pro_kg,
        grundpreis_ok=True,  # strukturierte Daten vom Händler
        bild_url=d.get("image"),
        url=f"{BASIS}/shop/p/{d['id']}" if d.get("id") else None,  # leitet auf die Produktseite weiter
        produkt_id=str(d.get("id") or ""),
        kategorie_pfad=kategorie_pfad(d.get("categories") or []),
        merkmale=sorted(merkmale),
        naehrwerte=nw,
        naehrwerte_quelle=(QUELLE_HAENDLER + (ZUBEREITET if zubereitet else "")) if nw else None,
        ean=gtin.zfill(13) if gtin and len(gtin) <= 13 else gtin,
    )


def aktuelle_angebote(heute: date | None = None, tage_voraus: int = 10, client: httpx.Client | None = None,
                      pause: float = 0.3, fortschritt=None) -> list[FlugblattAngebot]:
    """Alle Lebensmittel- und Getränke-Aktionen (Preis gesenkt, Mengenaktion, 1+1 gratis, Flugblatt)."""
    client = client or httpx.Client(headers={"User-Agent": UA, "Origin": BASIS, "Referer": BASIS + "/"}, timeout=60)
    gesehen: dict[str, FlugblattAngebot] = {}
    seite = 1
    while True:
        r = client.post(SUCHE, json=suchanfrage(seite))
        r.raise_for_status()
        ergebnis = r.json()["results"][0]
        if ergebnis.get("error"):
            raise RuntimeError(f"MPreis-Suche: {ergebnis['error']}")
        treffer = ergebnis.get("hits") or []
        for h in treffer:
            a = parse_produkt(h.get("document") or {})
            if a and a.produkt_id and a.produkt_id not in gesehen:
                gesehen[a.produkt_id] = a
        if fortschritt:
            fortschritt.weiter(len(treffer), ergebnis.get("found"))
        if not treffer or seite * SEITENGROESSE >= (ergebnis.get("found") or 0):
            break
        seite += 1
        time.sleep(pause)
    return list(gesehen.values())
