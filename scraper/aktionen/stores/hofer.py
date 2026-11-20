"""Hofer: Aktionsangebote von hofer.at.

- Übersicht https://www.hofer.at/angebote verlinkt pro Starttag eine Seite: /angebote/2026-11-19
- Die Seiten sind serverseitig gerendert. Jedes Produkt ist eine Kachel `<div id="product-tile-…">` mit
  Marke, Name, Packungsgröße ("product-tile__unit-of-measurement"), Vergleichspreis ("1 kg = 5,96"),
  Preis ("base-price") und Badges ("Tiefpreisaktion", "Verfügbar seit 16.11.2026").

Achtung: hofer.at sperrt Rechenzentrums-IPs (Akamai, "Access Denied"). Von einer Heim-IP aus funktioniert es.
Hofer-Angebote gelten österreichweit.
"""

from __future__ import annotations

import html
import re
import time
from datetime import date

import httpx

from ..flugblatt_pdf import FlugblattAngebot
from .base import USER_AGENT, get_mit_wiederholung, parse_menge

BASIS = "https://www.hofer.at"
# Ehrliche Programm-Kennung. Eine vorgetäuschte Chrome-Kennung wird von Hofers Bot-Schutz gesperrt (403).
UA = USER_AGENT

_TAG_SEITE_RE = re.compile(r'href="(?:https://www\.hofer\.at)?/angebote/(\d{4}-\d{2}-\d{2})(?:"|\?)')
_KACHEL_RE = re.compile(
    r'<div id="product-tile-(\d+)"(.*?)(?=<div id="product-tile-|class="product-teaser-list__header|</main>|$)', re.S
)
_PREIS_RE = re.compile(r"€\s*(\d{1,3}(?:\.\d{3})+|\d+),(\d{2}|-)")  # auch "€ 1.399,00"
# Hofer schreibt "(€ 3,98/1 l)" bzw. "(€ 45,69/100 g)"
_VERGLEICH_RE = re.compile(r"€\s*(\d+,\d{2})\s*/\s*(\d+(?:,\d+)?)\s*(kg|g|l|ml)\b", re.I)


class HoferBlockiert(RuntimeError):
    pass


def _text(x: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()


def _feld(kachel: str, klasse: str) -> str:
    m = re.search(r'class="' + re.escape(klasse) + r'(?:\s[^"]*)?"[^>]*>(.*?)</div>', kachel, re.S)
    return _text(m.group(1)) if m else ""


def tag_seiten(uebersicht_html: str) -> list[str]:
    """Starttage der Angebote, z. B. ['2026-11-16', '2026-11-19', …]."""
    return sorted(set(_TAG_SEITE_RE.findall(uebersicht_html)))


def _preis_aus(text: str) -> float | None:
    p = _PREIS_RE.search(_text(text))
    return float(f"{p.group(1).replace('.', '')}.{'00' if p.group(2) == '-' else p.group(2)}") if p else None


def _preise(kachel: str) -> tuple[float | None, float | None]:
    """(aktueller Preis, Streichpreis).

    Normal:    <span class="base-price__regular"><span>€ 9,99</span>…
    Reduziert: <div class="base-price base-price--on-sale base-price--product-tile">
                 <span class="base-price__regular"><ins class="base-price__discounted">€ 2,09</ins>…</span>
                 <span class="base-price__was-price"><del>€ 2,99</del></span>
    """
    block = re.search(r'class="base-price [^"]*base-price--product-tile[^"]*"(.*?)(?:</a>|$)', kachel, re.S)
    if not block:
        return None, None
    b = block.group(1)
    rabatt = re.search(r'class="base-price__discounted[^"]*"[^>]*>(.*?)</ins>', b, re.S)
    vorher = re.search(r'class="base-price__was-price[^"]*"[^>]*>(.*?)</span>', b, re.S)
    if rabatt and (preis := _preis_aus(rabatt.group(1))) is not None:
        return preis, _preis_aus(vorher.group(1)) if vorher else None
    regulaer = re.search(r'class="base-price__regular[^"]*"[^>]*>(.*?)</span>', b, re.S)
    return (_preis_aus(regulaer.group(1)) if regulaer else None), None


def parse_kachel(produkt_id: str, kachel: str, ab: date | None = None) -> FlugblattAngebot | None:
    preis, streich = _preise(kachel)
    if preis is None:
        return None
    marke = _feld(kachel, "product-tile__brandname")
    name = _feld(kachel, "product-tile__name")
    einheit_text = _feld(kachel, "product-tile__unit-of-measurement")      # z. B. "250 g Packung", "per kg"
    vergleich = _feld(kachel, "product-tile__comparison-price")            # z. B. "(€ 3,96/1 kg)"
    badges = [_text(x) for x in re.findall(r'class="base-label[^"]*"[^>]*>(.*?)</div>', kachel, re.S)]

    pro_kg = bool(re.search(r"(?i)\bper\s+kg\b|\bje\s+kg\b", einheit_text))
    menge, einheit = (None, None) if pro_kg else parse_menge(einheit_text)
    # Fallback: Menge aus Vergleichspreis berechnen ("(€ 3,96/1 kg)" bei Preis 0,99 -> 250 g)
    if menge is None and not pro_kg and (m := _VERGLEICH_RE.search(vergleich)):
        grundpreis = float(m.group(1).replace(",", "."))
        basis_menge, basis_einheit = parse_menge(f"{m.group(2)} {m.group(3)}")
        if basis_menge and grundpreis:
            menge, einheit = round(preis / grundpreis * basis_menge), basis_einheit

    link = re.search(r'href="(/produkt/[^"]+)"', kachel)
    bild = re.search(r'<img[^>]*\ssrc="([^"]+)"', kachel)
    aktion = [b for b in badges if b and not b.lower().startswith(("verfügbar", "ab "))]
    if streich and streich > preis:
        aktion.insert(0, f"-{round((1 - preis / streich) * 100)}%")

    return FlugblattAngebot(
        seite=0,
        name=f"{marke} {name}".strip() if marke and marke.lower() not in name.lower() else name,
        preis=preis,
        beschreibung=" · ".join(t for t in (einheit_text, vergleich) if t),
        normalpreis=streich if streich and streich > preis else None,
        aktion=aktion,
        menge=menge,
        einheit=einheit,
        pro_kg=pro_kg,
        grundpreis_ok=True,  # strukturierte Daten vom Händler
        gueltig_von=ab,
        bild_url=html.unescape(bild.group(1)) if bild else None,
        url=BASIS + link.group(1) if link else None,
        produkt_id=produkt_id.lstrip("0"),
    )


def angebote_aus_html(seite_html: str, ab: date | None = None) -> list[FlugblattAngebot]:
    ergebnis = []
    for produkt_id, kachel in _KACHEL_RE.findall(seite_html):
        a = parse_kachel(produkt_id, kachel, ab)
        if a is not None:
            ergebnis.append(a)
    return ergebnis


def _holen(client: httpx.Client, url: str) -> str:
    r = get_mit_wiederholung(client, url)
    if r.status_code == 403 or "Access Denied" in r.text[:500]:
        raise HoferBlockiert(f"hofer.at hat die Anfrage gesperrt (403): {url}")
    r.raise_for_status()
    return r.text


def aktuelle_angebote(heute: date | None = None, tage_voraus: int = 10, client: httpx.Client | None = None,
                      pause: float = 0.3, fortschritt=None) -> list[FlugblattAngebot]:
    """Alle Angebote mit Starttag von gestern-vor-7-Tagen bis `tage_voraus` Tage in der Zukunft."""
    heute = heute or date.today()
    client = client or httpx.Client(headers={"User-Agent": UA}, timeout=60, follow_redirects=True)
    uebersicht = _holen(client, BASIS + "/angebote")
    gesehen: dict[str, FlugblattAngebot] = {}
    tage = [t for t in tag_seiten(uebersicht)
            if -7 <= (date.fromisoformat(t) - heute).days <= tage_voraus]
    for tag in tage:
        ab = date.fromisoformat(tag)
        if fortschritt:
            fortschritt.weiter(1, len(tage))
        for a in angebote_aus_html(_holen(client, f"{BASIS}/angebote/{tag}"), ab):
            gesehen.setdefault(a.produkt_id, a)  # gleiches Produkt an mehreren Tagen: erster Starttag zählt
        time.sleep(pause)
    return list(gesehen.values())
