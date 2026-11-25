"""Ganzes Lebensmittel-Sortiment mit aktuellen Regalpreisen (für den Einkaufslisten-Vergleich).

    python -m aktionen.sortiment                 # Billa, MPreis und Spar  -> web/data/sortiment.js
    python -m aktionen.sortiment --ohne-spar     # so läuft es auf GitHub, solange Spar nicht zugestimmt hat

Nur Märkte mit Online-Shop und erlaubtem Abruf (docs/DATENQUELLEN.md, Abschnitt Sortiment):
- Billa:  shop.billa.at/api/product-discovery/categories/<kategorie>/products   (wie billa.py, ohne Aktionsfilter)
- MPreis: data-hub.mpreis.at/typesense-proxy/multi_search                      (wie mpreis.py, ohne Aktionsfilter)
- Spar:   www.interspar.at/api/listing/<kategorie>?p=<seite>                   (32 Produkte je Seite)
Lidl, Hofer und Penny stellen keine Normalpreise online; Gurkerl und dm verbieten den Abruf.

Ausgabe (kompakt, wird nur von einkauf.html geladen):
    window.SORTIMENT = {"erstellt": "...", "ketten": {"billa": {"stand": "...", "link": "https://…/{}",
                        "kategorien": ["Kühlwaren > Milchprodukte", …],
                        "produkte": [[id, name, preis, menge, einheit, pro_kg, normalpreis, kategorie_nr], …]}, …}}
preis = aktueller Regalpreis (bei laufender Shop-Aktion der Aktionspreis), normalpreis nur, wenn höher.
kategorie_nr zeigt in "kategorien" (Händler-Kategorie, hilft dem Abgleich: "Butter" ist kein Popcorn aus "Süßes").
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

from .fortschritt import Fortschritt
from .stores import billa, mpreis, rewe
from .stores.base import USER_AGENT, get_mit_wiederholung

WIEN = ZoneInfo("Europe/Vienna")
ZIEL = Path(__file__).resolve().parents[2] / "web" / "data" / "sortiment.js"

SPAR_BASIS = "https://www.interspar.at"
# Lebensmittel-Abteilungen des Interspar-Shops (Stand 11/2026). Ohne Wein, Spirituosen, Backformen, Kochgeschirr.
SPAR_KATEGORIEN = ["obst-gemuese", "brot-gebaeck", "kuehlregal", "tiefkuehlung", "vorratsschrank", "getraenke",
                   "suesswaren-knabbereien"]
SPAR_SEITE = 32  # fest vom Shop vorgegeben
_SPAR_EINHEIT = {"Kilogramm": "g", "Liter": "ml", "Stück": "stk"}
# Abteilung als Kategorie (die Liste liefert keine genauere)
SPAR_KATEGORIE_NAMEN = {"obst-gemuese": "Obst & Gemüse", "brot-gebaeck": "Brot & Gebäck", "kuehlregal": "Kühlregal",
                        "tiefkuehlung": "Tiefkühl", "vorratsschrank": "Vorratsschrank", "getraenke": "Getränke",
                        "suesswaren-knabbereien": "Süßwaren & Knabbereien"}

LINKS = {
    "billa": f"{billa.BASIS}/produkte/{{}}",
    "mpreis": f"{mpreis.BASIS}/shop/p/{{}}",
    "spar": f"{SPAR_BASIS}/p/{{}}",
}


def _zeile(pid: str, name: str, preis: float, menge, einheit, pro_kg: bool, normal, kategorie: str | None = None) -> list:
    """Kategorie steht vorerst als Text drin; kategorien_nummerieren() macht daraus eine Nummer."""
    return [str(pid), name, round(float(preis), 2), round(menge, 1) if menge else None, einheit, 1 if pro_kg else 0,
            round(float(normal), 2) if normal and normal > preis else None, kategorie]


def kategorien_nummerieren(produkte: list[list]) -> tuple[list[str], list[list]]:
    """Kategorie-Text -> Nummer in einer Liste (spart rund ein Drittel der Dateigröße)."""
    kategorien: list[str] = []
    nummer: dict[str, int] = {}
    aus = []
    for z in produkte:
        k = z[7]
        if k and k not in nummer:
            nummer[k] = len(kategorien)
            kategorien.append(k)
        aus.append(z[:7] + [nummer[k] if k else None])
    return kategorien, aus


# ---------- Billa ----------
def billa_zeile(p: dict) -> list | None:
    a = rewe.parse_produkt(p, "")
    if a is None or not p.get("slug"):
        return None
    return _zeile(p["slug"], a.name, a.preis, a.menge, a.einheit, a.pro_kg, a.normalpreis, a.kategorie_pfad)


def billa_laden(client: httpx.Client, pause: float, fortschritt=None) -> list[list]:
    produkte: dict[str, list] = {}
    for i, kat in enumerate(billa.STANDARD_KATEGORIEN):
        seite = 0
        while True:
            r = get_mit_wiederholung(client, f"{billa.BASIS}/api/product-discovery/categories/{kat}/products"
                                             f"?sortBy=relevance&page={seite}&pageSize={billa.SEITENGROESSE}")
            r.raise_for_status()
            daten = r.json()
            for p in daten.get("results") or []:
                z = billa_zeile(p)
                if z and z[0] not in produkte:  # "Rein pflanzlich" überschneidet sich mit den anderen Abteilungen
                    produkte[z[0]] = z
            seite += 1
            if fortschritt:
                fortschritt.setze(i + min(1.0, seite * billa.SEITENGROESSE / max(1, daten.get("total") or 1)),
                                  len(billa.STANDARD_KATEGORIEN))
            time.sleep(pause)
            if not daten.get("results") or seite * billa.SEITENGROESSE >= (daten.get("total") or 0):
                break
    return list(produkte.values())


# ---------- MPreis ----------
def mpreis_anfrage(seite: int) -> dict:
    anfrage = mpreis.suchanfrage(seite)
    kategorien = ",".join(f"`{k}`" for k in mpreis.HAUPTKATEGORIEN)
    anfrage["searches"][0]["filter_by"] = (f"available:true && priceMissing:false && categories:=[{kategorien}] && "
                                           f"$product_store_data(storeId:={mpreis.MARKT})")
    return anfrage


def mpreis_zeile(d: dict) -> list | None:
    a = mpreis.parse_produkt(d, nur_aktionen=False)
    if a is None or not a.produkt_id:
        return None
    return _zeile(a.produkt_id, a.name, a.preis, a.menge, a.einheit, a.pro_kg, a.normalpreis, a.kategorie_pfad)


def mpreis_laden(client: httpx.Client, pause: float, fortschritt=None) -> list[list]:
    produkte: dict[str, list] = {}
    seite = 1
    while True:
        r = client.post(mpreis.SUCHE, json=mpreis_anfrage(seite))
        r.raise_for_status()
        ergebnis = r.json()["results"][0]
        if ergebnis.get("error"):
            raise RuntimeError(f"MPreis-Suche: {ergebnis['error']}")
        treffer = ergebnis.get("hits") or []
        for h in treffer:
            z = mpreis_zeile(h.get("document") or {})
            if z and z[0] not in produkte:
                produkte[z[0]] = z
        if fortschritt:
            fortschritt.weiter(len(treffer), ergebnis.get("found"))
        if not treffer or seite * mpreis.SEITENGROESSE >= (ergebnis.get("found") or 0):
            break
        seite += 1
        time.sleep(pause)
    return list(produkte.values())


# ---------- Spar ----------
def spar_zeile(p: dict, kategorie: str | None = None) -> list | None:
    """Produkt aus /api/listing. Packungsgröße aus Preis / Grundpreis ("2,99 € bei 16,61 €/kg" -> 180 g)."""
    preis = p.get("price") or {}
    jetzt = preis.get("currentPrice")
    if not jetzt or jetzt <= 0 or not p.get("productNumber"):
        return None
    name = " ".join((p.get("name") or "").split())
    menge = einheit = None
    ref = preis.get("referencePrice") or {}
    e = _SPAR_EINHEIT.get(ref.get("unitName"))
    if e and ref.get("price") and (ref.get("referenceUnit") or 1) == 1:
        if e == "stk":
            menge, einheit = round(jetzt / ref["price"]), "stk"
        else:
            menge, einheit = round(jetzt / ref["price"] * 1000), e
        if not menge:
            menge = einheit = None
    return _zeile(p["productNumber"], name, jetzt, menge, einheit, False, preis.get("originalPrice"), kategorie)


def spar_laden(client: httpx.Client, pause: float, fortschritt=None) -> list[list]:
    produkte: dict[str, list] = {}
    for i, kat in enumerate(SPAR_KATEGORIEN):
        seite = 1
        while True:
            r = get_mit_wiederholung(client, f"{SPAR_BASIS}/api/listing/{kat}?p={seite}")
            if r.status_code == 403 or "json" not in r.headers.get("content-type", ""):
                raise RuntimeError(f"Spar-Shop gesperrt (HTTP {r.status_code}) – von Rechenzentrums-IPs (Cloudflare) "
                                   "kommt keine Antwort, lokal ausführen")
            r.raise_for_status()
            daten = r.json()
            for p in daten.get("products") or []:
                z = spar_zeile(p, SPAR_KATEGORIE_NAMEN.get(kat))
                if z and z[0] not in produkte:
                    produkte[z[0]] = z
            gesamt = daten.get("total") or 0
            if fortschritt:
                fortschritt.setze(i + min(1.0, seite * SPAR_SEITE / max(1, gesamt)), len(SPAR_KATEGORIEN))
            time.sleep(pause)
            if not daten.get("products") or seite * SPAR_SEITE >= gesamt:
                break
            seite += 1
    return list(produkte.values())


LADER = {"billa": billa_laden, "mpreis": mpreis_laden, "spar": spar_laden}


def _client(kette: str) -> httpx.Client:
    if kette == "mpreis":
        return httpx.Client(headers={"User-Agent": mpreis.UA, "Origin": mpreis.BASIS, "Referer": mpreis.BASIS + "/"},
                            timeout=60)
    return httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60, follow_redirects=True)


def alten_stand_laden(pfad: Path) -> dict:
    """Vorhandene sortiment.js lesen (für Ketten, die diesmal nicht geladen werden können)."""
    try:
        text = pfad.read_text(encoding="utf-8").strip()
        return json.loads(text.removeprefix("window.SORTIMENT = ").removesuffix(";"))
    except (OSError, ValueError):
        return {}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--ziel", type=Path, default=ZIEL)
    p.add_argument("--alt", type=Path, help="letzte sortiment.js: deren Daten bleiben für Ketten, die fehlschlagen")
    p.add_argument("--ohne-spar", action="store_true", help="Spar weglassen (auf GitHub, bis Spar zustimmt)")
    p.add_argument("--ohne-billa", action="store_true")
    p.add_argument("--ohne-mpreis", action="store_true")
    p.add_argument("--pause", type=float, default=0.5, help="Sekunden zwischen zwei Abrufen (Server schonen)")
    args = p.parse_args(argv)

    ketten = [k for k in LADER if not getattr(args, f"ohne_{k}")]
    alt = alten_stand_laden(args.alt or args.ziel).get("ketten", {})
    ergebnis: dict[str, dict] = {}
    fehler = 0
    for kette in ketten:
        fortschritt = Fortschritt(f"Sortiment {kette}")
        try:
            with _client(kette) as client:
                produkte = LADER[kette](client, args.pause, fortschritt)
            fortschritt.fertig()
            if not produkte:
                raise RuntimeError("keine Produkte")
            stand = datetime.now(WIEN).isoformat(timespec="seconds")
            kategorien, produkte = kategorien_nummerieren(produkte)
            ergebnis[kette] = {"stand": stand, "link": LINKS[kette], "kategorien": kategorien, "produkte": produkte}
            print(f"  {kette}: {len(produkte)} Produkte", flush=True)
        except (httpx.HTTPError, RuntimeError, ValueError) as e:
            fehler += 1
            print(f"::warning::Sortiment {kette} nicht geladen: {e}", file=sys.stderr, flush=True)
            if kette in alt:
                ergebnis[kette] = alt[kette]
                print(f"  {kette}: alter Stand vom {alt[kette].get('stand')} bleibt", flush=True)

    daten = {"erstellt": datetime.now(WIEN).isoformat(timespec="seconds"), "ketten": ergebnis}
    args.ziel.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(daten, ensure_ascii=False, separators=(",", ":"))
    args.ziel.write_text(f"window.SORTIMENT = {text};\n", encoding="utf-8")
    print(f"{args.ziel}: {', '.join(f'{k} {len(v['produkte'])}' for k, v in ergebnis.items()) or 'leer'} "
          f"({len(text) / 1e6:.1f} MB)")
    return 1 if fehler == len(ketten) and ketten else 0


if __name__ == "__main__":
    raise SystemExit(main())
