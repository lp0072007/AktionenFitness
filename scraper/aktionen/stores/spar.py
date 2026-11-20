"""Spar Österreich (Daten über den Interspar-Onlineshop).

Endpunkte (gefunden über die Browser-DevTools, 20.11.2026):
    /api/search/flyout?q=skyr&scope=all                   Vorschläge im Suchfeld (max. 5 Produkte)
    /api/search/results?q=skyr&scope=all&productLimit=…   Suchergebnisseite

Beide liefern JSON mit `products[]`, Format siehe tests/fixtures/spar_flyout_skyr.json.
Achtung: interspar.at ist hinter Cloudflare. Anfragen von Rechenzentrums-IPs (Cloud, GitHub Actions)
bekommen eine "Just a moment..."-Seite statt JSON.
"""

from __future__ import annotations

import httpx

from ..models import Angebot
from .base import USER_AGENT, Store, parse_menge

BASE_URL = "https://www.interspar.at"
RESULTS_PATH = "/api/search/results"

# Mögliche Feldnamen für den Streichpreis. Die echten Namen sind noch unbekannt,
# weil in der bisherigen Beispielantwort kein Produkt in Aktion war.
_NORMALPREIS_KEYS = ("regularPrice", "previousPrice", "strikePrice", "originalPrice", "oldPrice", "listPrice")


class CloudflareBlockiert(RuntimeError):
    pass


def produkte_aus_antwort(data: dict) -> list[dict]:
    """Holt die Produktliste aus einer flyout- oder results-Antwort."""
    if isinstance(data.get("products"), list):
        return data["products"]
    # results-Antwort ist evtl. verschachtelt, z. B. {"products": {"items": [...]}}
    prods = data.get("products") or data.get("hits") or {}
    if isinstance(prods, dict):
        for key in ("items", "products", "hits"):
            if isinstance(prods.get(key), list):
                return prods[key]
    return []


class SparStore(Store):
    name = "spar"

    def __init__(self, base_url: str = BASE_URL, timeout: float = 30):
        self.base_url = base_url
        self.timeout = timeout

    def fetch_json(self, query: str, limit: int = 100) -> dict:
        resp = httpx.get(
            self.base_url + RESULTS_PATH,
            params={"q": query, "scope": "all", "productLimit": limit},
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
                "Referer": f"{self.base_url}/suche?q={query}",
            },
            timeout=self.timeout,
        )
        if "Just a moment" in resp.text[:2000]:
            raise CloudflareBlockiert(
                "interspar.at hat mit einer Cloudflare-Prüfung geantwortet (HTTP "
                f"{resp.status_code}). Von zuhause aus probieren oder die JSON-Antwort aus dem Browser "
                "speichern und mit --datei einlesen."
            )
        resp.raise_for_status()
        return resp.json()

    def fetch_raw(self, query: str = "*") -> list[dict]:
        return produkte_aus_antwort(self.fetch_json(query))

    def parse(self, raw: dict) -> Angebot | None:
        produkt_id = raw.get("productNumber")
        preis_info = raw.get("price") or {}
        preis = preis_info.get("currentPrice")
        if not produkt_id or preis is None:
            return None

        name = (raw.get("name") or "").strip()
        menge, einheit = parse_menge(name)

        # Fallback: Menge aus Grundpreis berechnen (Preis / Preis pro kg)
        ref = preis_info.get("referencePrice") or {}
        ref_einheit = (raw.get("unit") or {}).get("shortCode")
        if menge is None and ref.get("price") and ref_einheit in ("kg", "l"):
            menge = round(preis / ref["price"] * 1000)
            einheit = "g" if ref_einheit == "kg" else "ml"

        normalpreis = next(
            (float(preis_info[k]) for k in _NORMALPREIS_KEYS if preis_info.get(k)), None
        )

        tags = [b["key"] for b in (raw.get("badges") or {}).get("image", []) if b.get("key")]

        return Angebot(
            kette=self.name,
            produkt_id=str(produkt_id),
            name=name,
            marke=raw.get("brand") or None,
            preis=float(preis),
            menge=menge,
            einheit=einheit,
            normalpreis=normalpreis,
            bild_url=(raw.get("image") or {}).get("url"),
            tags=tags,
            bio="bio" in tags or name.lower().startswith("bio ") or " bio " in name.lower(),
        )
