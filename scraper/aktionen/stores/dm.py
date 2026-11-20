"""dm drogerie markt Österreich: Dauerpreise fitnessrelevanter Lebensmittel (Tofu, Proteinpulver, Haferflocken, …).

dm macht kaum Aktionen (Stichprobe 11/2026: 1 von 200 Proteinprodukten mit Streichpreis, ein Ausverkauf), deshalb
liefert dieses Modul **Dauerpreise** zum Vergleich mit den Aktionen der Supermärkte.

Produktsuche (von Heim- und Cloud-IP erreichbar). Achtung: dm begrenzt die Anfragen (429 Too Many Requests),
deshalb 3 s Pause und nur eine Ergebnisseite pro Suchbegriff:
    GET https://product-search.services.dmtech.com/at/search/crawl?query=tofu&pageSize=100&currentPage=0
Antwort: {"products": [...], "count": …, "totalPages": …}. Pro Produkt u. a.:
    brandName, title ("Bio Tofu natur, 200 g"), dan (Artikelnummer), gtin (EAN),
    tileData.price.price.current.value ("2,85 €"), tileData.price.price.previous.value (selten),
    tileData.price.tileInfos (["0,2 kg (9,95 € je 1 kg)"]), tileData.self (Link), tileData.images[].tileSrc,
    tileData.trackingData.categories (["Tofu"]).
"""

from __future__ import annotations

import re
import time
from datetime import date

import httpx

from ..flugblatt_pdf import FlugblattAngebot
from .base import USER_AGENT, get_mit_wiederholung, parse_menge

BASIS = "https://www.dm.at"
SUCHE = "https://product-search.services.dmtech.com/at/search/crawl"
UA = USER_AGENT
SEITENGROESSE = 100
# Suchbegriffe für fitnessrelevante Produkte bei dm. Ob ein Treffer zählt, entscheidet danach die Fitness-Erkennung.
SUCHBEGRIFFE = [
    "tofu", "proteinpulver", "whey", "haferflocken", "direktsaft rote bete", "linsen", "kichererbsen",
    "erdnussmus", "mandeln", "nüsse", "reis", "nudeln", "quinoa", "bohnen",
]
_PREIS_RE = re.compile(r"(\d+(?:\.\d{3})*),(\d{2})")


def _preis(text: str | None) -> float | None:
    m = _PREIS_RE.search(text or "")
    return float(f"{m.group(1).replace('.', '')}.{m.group(2)}") if m else None


def parse_produkt(p: dict) -> FlugblattAngebot | None:
    kachel = p.get("tileData") or {}
    preise = (kachel.get("price") or {}).get("price") or {}
    preis = _preis((preise.get("current") or {}).get("value"))
    if preis is None:
        return None
    vorher = _preis((preise.get("previous") or {}).get("value"))

    titel = re.sub(r"(\d) (\d{3})\b", r"\1\2", (p.get("title") or "").strip())  # "1 000 g" -> "1000 g"
    # "Bio Tofu natur, 200 g" -> Name ohne Mengenangabe, Menge aus dem Teil nach dem letzten Komma
    name_teil, _, mengen_teil = titel.rpartition(",")
    name_ohne_menge = name_teil.strip() if name_teil and parse_menge(mengen_teil)[0] else titel
    marke = (p.get("brandName") or "").strip()
    name = f"{marke} {name_ohne_menge}".strip() if marke and marke.lower() not in name_ohne_menge.lower() else name_ohne_menge

    infos = (kachel.get("price") or {}).get("tileInfos") or []
    menge, einheit = parse_menge(mengen_teil) if mengen_teil else (None, None)
    if menge is None and infos:
        menge, einheit = parse_menge(infos[0].split("(")[0])

    kategorien = ((kachel.get("trackingData") or {}).get("categories")) or []
    bilder = kachel.get("images") or []
    aktion = []
    if vorher and vorher > preis:
        aktion.append(f"-{round((1 - preis / vorher) * 100)}%")
    return FlugblattAngebot(
        seite=0,
        name=name,
        preis=preis,
        beschreibung=" · ".join([*infos, *kategorien]),
        normalpreis=vorher if vorher and vorher > preis else None,
        aktion=aktion,
        menge=menge,
        einheit=einheit,
        grundpreis_ok=True,
        bild_url=bilder[0].get("tileSrc") if bilder else None,
        url=BASIS + kachel["self"] if kachel.get("self") else None,
        produkt_id=str(p.get("dan") or p.get("gtin") or ""),
        kategorie_pfad=" > ".join(kategorien) if kategorien else None,
        zusatz_text=None,
    )


def aktuelle_angebote(heute: date | None = None, tage_voraus: int = 10, client: httpx.Client | None = None,
                      pause: float = 3.0, fortschritt=None) -> list[FlugblattAngebot]:
    """Fitnessrelevante dm-Produkte zu Dauerpreisen (heute/tage_voraus nur für eine einheitliche Schnittstelle)."""
    client = client or httpx.Client(headers={"User-Agent": UA, "Accept": "application/json"}, timeout=60,
                                    follow_redirects=True)
    gesehen: dict[str, FlugblattAngebot] = {}
    for i, begriff in enumerate(SUCHBEGRIFFE, start=1):
        if fortschritt:
            fortschritt.setze(i - 1, len(SUCHBEGRIFFE))
        seite = 0
        while True:
            r = get_mit_wiederholung(
                client, f"{SUCHE}?query={begriff}&pageSize={SEITENGROESSE}&currentPage={seite}&sort=editorial_relevance")
            r.raise_for_status()
            daten = r.json()
            for p in daten.get("products") or []:
                a = parse_produkt(p)
                if a and a.produkt_id and a.produkt_id not in gesehen:
                    gesehen[a.produkt_id] = a
            seite += 1
            time.sleep(pause)
            if seite >= min(daten.get("totalPages") or 1, 1):  # nur die 100 relevantesten Treffer pro Suchbegriff
                break
    if fortschritt:
        fortschritt.setze(len(SUCHBEGRIFFE), len(SUCHBEGRIFFE))
    return list(gesehen.values())
