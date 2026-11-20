"""Spar Österreich.

Spar nutzt intern den Suchdienst FACT-Finder. Der alte Kanal `products_lmos_at` existiert seit
spätestens 11/2026 nicht mehr, der aktuelle Endpunkt muss noch im Browser ermittelt werden
(siehe docs/DATENQUELLEN.md). SEARCH_URL und die Aktionsfelder unten sind deshalb vorläufig.
"""

from __future__ import annotations

import httpx

from ..models import Angebot
from .base import USER_AGENT, Store, parse_menge, parse_preis

# TODO: aktuellen Kanal / Endpunkt aus den Browser-DevTools eintragen
SEARCH_URL = "https://search-spar.spar-ics.com/fact-finder/rest/v4/search/products_lmos_at"


class SparStore(Store):
    name = "spar"

    def __init__(self, search_url: str = SEARCH_URL, timeout: float = 30):
        self.search_url = search_url
        self.timeout = timeout

    def fetch_raw(self, query: str = "*", hits: int = 100) -> list[dict]:
        resp = httpx.get(
            self.search_url,
            params={"query": query, "q": query, "page": 1, "hitsPerPage": hits},
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=self.timeout,
        )
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"Spar-API Fehler: {data.get('errorDescription', data['error'])}")
        resp.raise_for_status()
        hits_ = data.get("hits", [])
        # alte API: hits ist direkt eine Liste, teils verschachtelt als {"hits": [...]}
        return hits_.get("hits", []) if isinstance(hits_, dict) else hits_

    def parse(self, raw: dict) -> Angebot | None:
        mv = raw.get("masterValues", raw)
        produkt_id = mv.get("product-number")
        preis = parse_preis(mv.get("price"))
        if not produkt_id or preis is None:
            return None

        name = mv.get("name") or mv.get("short-description") or ""
        mengen_text = mv.get("short-description-3") or mv.get("short-description-2") or name
        menge, einheit = parse_menge(mengen_text)

        if mv.get("item-type") == "WeightProduct":
            menge, einheit = 1000, "g"  # Preis bezieht sich auf 1 kg

        # TODO: echte Feldnamen für Aktionen aus einer echten Antwort übernehmen
        normalpreis = parse_preis(mv.get("regular-price") or mv.get("old-price"))
        aktion_text = mv.get("promotion-text") or mv.get("badge-text")

        return Angebot(
            kette=self.name,
            produkt_id=str(produkt_id),
            name=name.strip(),
            marke=mv.get("title"),
            preis=preis,
            menge=menge,
            einheit=einheit,
            normalpreis=normalpreis,
            aktion_text=aktion_text,
            ean=mv.get("ean"),
            bio=mv.get("biolevel") == "Bio",
        )
