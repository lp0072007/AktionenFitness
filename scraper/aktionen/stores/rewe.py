"""Gemeinsame Teile für die Rewe-Plattform (Penny, Billa).

Beide Shops liefern Produkte im selben JSON-Format über /api/product-discovery/…:
    name, brand.name, amount + volumeLabelShort ("250" + "g"), weightArticle (Kilo-Ware),
    price.regular.value (Cent, Aktionspreis), price.regular.promotionText ("ab 2 Becher"),
    price.regular.promotionQuantity / promotionType (FROM, PER_SET_OF),
    price.crossed (Streichpreis), price.standard.value (Normalpreis, nur Billa),
    price.discountPercentage, price.validityStart/validityEnd (nur Penny), images[], slug, sku, parentCategories,
    price.loyalty.value (Preis mit jö-Karte, Cent), badges[] ("pp-vegan", "pp-veget", "pp-bio", …).
"""

from __future__ import annotations

from datetime import date

from ..flugblatt_pdf import FlugblattAngebot

NICHT_LEBENSMITTEL = {"Haushalt", "Non-Food", "Haustier", "Pflege", "Drogerie", "Drogerie & Kosmetik",
                      "Küche, Haushalt & Garten", "Baby & Kleinkind"}
_EINHEITEN = {"g": (1, "g"), "kg": (1000, "g"), "ml": (1, "ml"), "liter": (1000, "ml"), "l": (1000, "ml"),
              "stk": (1, "stk")}
# Kennzeichnungen des Händlers -> Merkmale für die Website (Filter vegan/vegetarisch/Bio)
_BADGE_MERKMALE = {"pp-vegan": "vegan", "gs-vegan": "vegan", "pp-veget": "vegetarisch", "pp-bio": "bio"}


def merkmale(p: dict) -> list[str]:
    gefunden = {_BADGE_MERKMALE[b] for b in p.get("badges") or [] if b in _BADGE_MERKMALE}
    if "vegan" in gefunden:
        gefunden.add("vegetarisch")
    return sorted(gefunden)


def kategorie_pfad(p: dict) -> str | None:
    for pfad in p.get("parentCategories") or []:
        if pfad and pfad[0].get("name") not in (None, "Alle Angebote"):
            return " > ".join(x.get("name", "") for x in pfad)
    return None


def hauptkategorie(p: dict) -> str | None:
    for pfad in p.get("parentCategories") or []:
        if pfad and pfad[0].get("name") not in (None, "Alle Angebote"):
            return pfad[0]["name"]
    return None


def parse_produkt(p: dict, produkt_basis_url: str) -> FlugblattAngebot | None:
    """produkt_basis_url z. B. "https://www.penny.at/produkte" -> Link = {basis}/{slug}"""
    preis_info = p.get("price") or {}
    regulaer = preis_info.get("regular") or {}
    if regulaer.get("value") is None or hauptkategorie(p) in NICHT_LEBENSMITTEL:
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
            # Tippfehler beim Händler: "0.25" + "ml" (Penny, Oxxenkracherl 24.11.2026) meint 0,25 Liter.
            # Unter 5 ml/g mit Nachkommastellen gibt es im Lebensmittelhandel nicht.
            if einheit in ("g", "ml") and menge < 5 and menge != int(menge):
                menge *= 1000

    ab_menge = None
    if regulaer.get("promotionType") in ("FROM", "PER_SET_OF") and (regulaer.get("promotionQuantity") or 0) > 1:
        ab_menge = int(regulaer["promotionQuantity"])

    vorher = preis_info.get("crossed") or (preis_info.get("standard") or {}).get("value")
    normalpreis = vorher / 100 if vorher and vorher / 100 > preis else None

    # Kartenpreis (jö Bonus Club), nur wenn wirklich günstiger
    karte = (preis_info.get("loyalty") or {}).get("value")
    zusatzpreis = round(karte / 100, 2) if karte and karte < regulaer["value"] else None

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
        zusatzpreis=zusatzpreis,
        zusatz_text="jö" if zusatzpreis else None,
        aktion=aktion,
        menge=menge,
        einheit=einheit,
        pro_kg=pro_kg,
        merkmale=merkmale(p),
        grundpreis_ok=True,  # strukturierte Daten vom Händler
        gueltig_von=date.fromisoformat(von) if von else None,
        gueltig_bis=date.fromisoformat(bis) if bis else None,
        bild_url=bilder[0] if bilder else None,
        url=f"{produkt_basis_url}/{p['slug']}" if p.get("slug") else None,
        produkt_id=p.get("sku") or p.get("productId"),
        kategorie_pfad=kategorie_pfad(p),
    )


def sammeln(produkte, heute: date, tage_voraus: int, gesehen: dict, sorten: set, produkt_basis_url: str) -> None:
    """Produkte parsen, Abgelaufene/zu Späte und doppelte Sorten (gleicher Name/Preis/Menge) weglassen."""
    for p in produkte:
        a = parse_produkt(p, produkt_basis_url)
        if a is None or not a.produkt_id or a.produkt_id in gesehen:
            continue
        if a.gueltig_bis and a.gueltig_bis < heute:
            continue
        if a.gueltig_von and (a.gueltig_von - heute).days > tage_voraus:
            continue
        schluessel = (a.name, a.preis, a.menge, a.gueltig_von)
        if schluessel in sorten:
            continue
        sorten.add(schluessel)
        gesehen[a.produkt_id] = a
