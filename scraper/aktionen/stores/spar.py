"""Spar Österreich (Daten über den Interspar-Onlineshop).

Endpunkte (gefunden über die Browser-DevTools, 20.11.2026):
    /api/search/flyout?q=skyr&scope=all                   Vorschläge im Suchfeld (max. 5 Produkte)
    /api/search/results?q=skyr&scope=all&productLimit=…   Suchergebnisseite
    /api/product/by-number/{productNumber}                Produktdetails inkl. Nährwerten und Aktionsfeldern

Formate siehe tests/fixtures/spar_flyout_skyr.json und tests/fixtures/spar_detail_cottage_protein.json.
Achtung: interspar.at ist hinter Cloudflare. Anfragen von Rechenzentrums-IPs (Cloud, GitHub Actions)
bekommen eine "Just a moment..."-Seite statt JSON.
"""

from __future__ import annotations

import httpx

from ..models import Angebot
from .base import USER_AGENT, Store, parse_menge, parse_naehrwert_tabelle

BASE_URL = "https://www.interspar.at"
RESULTS_PATH = "/api/search/results"
DETAIL_PATH = "/api/product/by-number/{nr}"

# Mögliche Feldnamen für den Streichpreis in der Suche. Die echten Namen sind noch unbekannt,
# weil in den bisherigen Beispielantworten kein Produkt in Aktion war.
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


def _info_items(product: dict) -> dict[str, str]:
    """Alle infoSections als {Label: Wert}."""
    items = {}
    for section in product.get("infoSections") or []:
        for item in section.get("items") or []:
            if item.get("label"):
                items[item["label"]] = item.get("value")
    return items


def _menge_aus_info(info: dict[str, str]) -> tuple[float | None, str | None]:
    """'Menge: 0,500' + 'Einheit: KG' -> (500, 'g')."""
    if not info.get("Menge") or not info.get("Einheit"):
        return None, None
    return parse_menge(f"{info['Menge']} {info['Einheit']}")


def _normalpreis(preis_info: dict, preis: float, uvp=None) -> float | None:
    kandidaten = [preis_info.get(k) for k in _NORMALPREIS_KEYS] + [uvp]
    for k in kandidaten:
        if isinstance(k, (int, float)) and k > preis:
            return float(k)
    return None


class SparStore(Store):
    name = "spar"

    def __init__(self, base_url: str = BASE_URL, timeout: float = 30):
        self.base_url = base_url
        self.timeout = timeout

    def _get_json(self, path: str, params: dict | None = None, referer: str = "/") -> dict:
        resp = httpx.get(
            self.base_url + path,
            params=params,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json", "Referer": self.base_url + referer},
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

    # --- Suche -------------------------------------------------------------

    def fetch_json(self, query: str, limit: int = 100) -> dict:
        return self._get_json(
            RESULTS_PATH, {"q": query, "scope": "all", "productLimit": limit}, referer=f"/suche?q={query}"
        )

    def fetch_raw(self, query: str = "*") -> list[dict]:
        return produkte_aus_antwort(self.fetch_json(query))

    def parse(self, raw: dict) -> Angebot | None:
        """Ein Produkt aus der Such-Antwort (ohne Nährwerte)."""
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

        tags = [b["key"] for b in (raw.get("badges") or {}).get("image", []) if b.get("key")]

        return Angebot(
            kette=self.name,
            produkt_id=str(produkt_id),
            name=name,
            marke=raw.get("brand") or None,
            preis=float(preis),
            menge=menge,
            einheit=einheit,
            normalpreis=_normalpreis(preis_info, preis),
            bild_url=(raw.get("image") or {}).get("url"),
            tags=tags,
            bio="bio" in tags or name.lower().startswith("bio ") or " bio " in name.lower(),
        )

    # --- Produktdetails ----------------------------------------------------

    def fetch_detail(self, produkt_nr: str) -> dict:
        return self._get_json(DETAIL_PATH.format(nr=produkt_nr), referer=f"/p/{produkt_nr}")

    def parse_detail(self, data: dict) -> Angebot | None:
        """Produktdetail-Antwort inkl. Nährwerten, Kategorie und Aktionsinfos."""
        p = data.get("product") or data
        produkt_id = p.get("articleNumber")
        preis_info = p.get("price") or {}
        preis = preis_info.get("currentPrice")
        if not produkt_id or preis is None:
            return None

        name = (p.get("name") or "").strip()
        info = _info_items(p)
        menge, einheit = _menge_aus_info(info)
        if menge is None:
            menge, einheit = parse_menge(name)

        naehrwert_text = next(
            (n.get("value") for n in p.get("nutrition") or [] if n.get("key") == "INTERSPARPRODUCTNUTRITIONFACTSTABLE"),
            None,
        )

        tags = [b["key"] for b in (p.get("badges") or {}).get("image", []) if b.get("key")]
        if info.get("Preisgesenkt"):
            tags.append("preisgesenkt")  # Spar "Dauerhaft preisgesenkt", keine Flugblatt-Aktion

        # TODO: Struktur von promotions[] / promotionCampaign an einem Aktionsprodukt prüfen
        aktion_text = p.get("promotionBadgeText")
        if not aktion_text and isinstance(p.get("promotionCampaign"), dict):
            aktion_text = p["promotionCampaign"].get("name") or p["promotionCampaign"].get("title")

        breadcrumb = [b.get("text") for b in data.get("breadcrumb") or [] if b.get("link")]
        media = p.get("media") or []

        return Angebot(
            kette=self.name,
            produkt_id=str(produkt_id),
            name=name,
            marke=p.get("brandName") or None,
            preis=float(preis),
            menge=menge,
            einheit=einheit,
            normalpreis=_normalpreis(preis_info, preis, p.get("uvp")),
            aktion_text=aktion_text,
            bild_url=media[0].get("url") if media else None,
            tags=tags,
            kategorie=breadcrumb[-1] if breadcrumb else None,
            naehrwerte=parse_naehrwert_tabelle(naehrwert_text),
            bio="bio" in tags or name.lower().startswith("bio "),
        )
