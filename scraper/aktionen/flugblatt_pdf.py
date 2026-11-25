"""Angebote aus Flugblatt-PDFs lesen, ohne KI: Rollen über Schriftarten, Zuordnung über Positionen.

Ablauf:
1. Wörter mit Position/Schrift aus dem PDF holen (pdfplumber) und zu Segmenten zusammenfassen
2. Rollen über die Schriftart bestimmen (pro Kette konfigurierbar, siehe SPAR_SCHRIFTEN):
   Produktname, Beschreibung, Preis (Euro groß + Cent klein), Bedingung ("1 Becher 1,99 ab 2 Becher je"),
   Badge ("40% billiger!", "2+1 GRATIS")
3. Zuordnen:
   - Hinweise wie "Zusätzlich -25%" oder "SPAR-App-Gutschein" → nächster Preis darunter = Zusatzpreis
   - Bedingungen → nächster Preis darunter
   - Hauptpreise → Produktnamen (global, jeder Name max. 1 Hauptpreis, Preis links vom Namen kostet extra)
   - Zusatzpreise und Badges → nächster Hauptpreis

Die Analyse arbeitet auf einer Wortliste (dicts mit text, x0, x1, top, bottom, size, fontname), damit sie
ohne PDF testbar ist.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from .models import Naehrwerte
from .stores.base import parse_menge


@dataclass
class Schriften:
    titel: str
    beschreibung: str
    preis: tuple[str, ...]
    bedingung: tuple[str, ...]


SPAR_SCHRIFTEN = Schriften(
    titel="MuseoSansCond-900",
    beschreibung="MuseoSansCond-500",
    preis=("MuseoSansRounded-900", "TrueNorth3DBlack-Regular"),  # TrueNorth: rote "AKTION!"-Kästen
    bedingung=("MuseoSansRounded-700",),
)

LINKS_STRAFE = 100       # Preis steht links vom Produktnamen: unüblich, aber möglich
GRUNDPREIS_BONUS = -150  # Preis passt zu "(= per kg …)" in der Beschreibung
GRUNDPREIS_STRAFE = 80   # Beschreibung hat Grundpreis, Preis passt nicht dazu
MAX_ABSTAND_BADGE = 130
MAX_ABSTAND_BEDINGUNG = 60
_ZUSATZ_MARKER = ("zusätzlich", "spar-app", "%-akti")  # "%-Aktion" steht teils auf einer Kurve und zerfällt


@dataclass
class Box:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float
    size: float = 0
    font: str = ""

    @property
    def kompakt(self) -> str:
        """Text ohne Leerzeichen, für gesperrte Schrift wie 'Z u s ä t z l i c h'."""
        return self.text.replace(" ", "")

    def abstand(self, o: "Box") -> float:
        dx = max(0.0, o.x0 - self.x1, self.x0 - o.x1)
        dy = max(0.0, o.top - self.bottom, self.top - o.bottom)
        return dx + dy


@dataclass
class Preis(Box):
    wert: float = 0.0
    zusatz: bool = False
    zusatz_text: str | None = None  # "SPAR-App" bei App-Gutscheinen, sonst None (z. B. Aktionstag)


@dataclass
class FlugblattAngebot:
    seite: int
    name: str
    preis: float
    beschreibung: str = ""
    normalpreis: float | None = None   # "statt 2,89" oder "1 Becher 1,99"
    ab_menge: int | None = None        # "ab 2 Becher je"
    zusatzpreis: float | None = None   # z. B. Fr/Sa -25% oder mit App-Gutschein
    aktion: list[str] = field(default_factory=list)
    menge: float | None = None
    einheit: str | None = None
    pro_kg: bool = False               # Preis gilt per kg (Theke, Gewichtsware)
    bbox: tuple[float, float, float, float] | None = None  # x0, top, x1, bottom aller zugehörigen Texte (PDF-Punkte)
    name_bbox: tuple[float, float, float, float] | None = None   # nur der Produktname (Anker für den Bildausschnitt)
    preis_bbox: tuple[float, float, float, float] | None = None  # nur der Hauptpreis
    grundpreis_ok: bool | None = None  # True: Preis passt zu "(= per kg …)", False: passt nicht, None: kein Grundpreis
    # Nur bei Ketten mit strukturierten Daten (z. B. Lidl):
    zusatz_text: str | None = None     # Bedeutung des Zusatzpreises, z. B. "Lidl Plus"
    gueltig_von: "date | None" = None
    gueltig_bis: "date | None" = None
    bild_url: str | None = None
    url: str | None = None
    produkt_id: str | None = None
    kategorie_pfad: str | None = None  # Kategorie beim Händler, z. B. "Tiefkühl > Tiefkühlgerichte > Reis & Pasta"
    merkmale: list[str] = field(default_factory=list)  # Kennzeichnung des Händlers: "vegan", "vegetarisch", "bio"
    # Echte Nährwerte pro 100 g/ml (naehrwerte.py); None = nur Richtwert der Fitness-Kategorie
    naehrwerte: Naehrwerte | None = None
    naehrwerte_quelle: str | None = None   # "Etikett" (Händler) oder "Open Food Facts"
    ean: str | None = None

    def _erweitern(self, b: "Box") -> None:
        if self.bbox is None:
            self.bbox = (b.x0, b.top, b.x1, b.bottom)
        else:
            x0, t, x1, u = self.bbox
            self.bbox = (min(x0, b.x0), min(t, b.top), max(x1, b.x1), max(u, b.bottom))


def _font(fontname: str) -> str:
    return fontname.split("+", 1)[-1]


def segmente(woerter: list[dict]) -> list[Box]:
    """Fasst Wörter gleicher Schrift auf derselben Zeile zu Segmenten zusammen."""
    boxen: list[Box] = []
    for w in woerter:
        font = _font(w["fontname"])
        b = boxen[-1] if boxen else None
        if (
            b
            and b.font == font
            and abs(b.size - w["size"]) < 0.6
            and abs(b.top - w["top"]) < 3
            and -2 <= w["x0"] - b.x1 < max(6.0, w["size"] * 0.8)
        ):
            b.text += " " + w["text"]
            b.x1, b.bottom = w["x1"], max(b.bottom, w["bottom"])
        else:
            boxen.append(Box(w["text"], w["x0"], w["x1"], w["top"], w["bottom"], w["size"], font))
    return boxen


def _ziffern_verbinden(boxen: list[Box]) -> list[Box]:
    """Einzeln gesetzte Ziffern ('1' '3') zu Zahlen ('13') verbinden, unabhängig von der Stream-Reihenfolge."""
    ziffern = sorted((b for b in boxen if re.fullmatch(r"\d+", b.kompakt)), key=lambda b: (b.font, b.x0))
    ergebnis: list[Box] = []
    for z in ziffern:
        z = Box(z.kompakt, z.x0, z.x1, z.top, z.bottom, z.size, z.font)
        partner = next(
            (
                e for e in reversed(ergebnis)
                if e.font == z.font and abs(e.size - z.size) < 1.5 and abs(e.top - z.top) < 4
                and -3 <= z.x0 - e.x1 < z.size * 0.3
            ),
            None,
        )
        if partner:
            partner.text += z.text
            partner.x1, partner.bottom = z.x1, max(partner.bottom, z.bottom)
        else:
            ergebnis.append(z)
    return ergebnis


def zeilen(boxen: list[Box]) -> list[Box]:
    """Segmente gleicher Schrift auf einer Zeile verbinden, unabhängig von der Stream-Reihenfolge.

    Nötig für gesperrte/zerstückelte Hinweise wie '%' + '- A k t i' + 'o n'.
    """
    ergebnis: list[Box] = []
    for b in sorted(boxen, key=lambda b: (b.font, b.x0)):  # links nach rechts, Zeile über |top| < 5
        z = next(
            (
                e for e in reversed(ergebnis)
                if e.font == b.font and abs(e.top - b.top) < 5 and -3 <= b.x0 - e.x1 < max(8.0, b.size * 0.6)
            ),
            None,
        )
        if z:
            z.text += " " + b.text
            z.x1, z.bottom = max(z.x1, b.x1), max(z.bottom, b.bottom)
        else:
            ergebnis.append(Box(b.text, b.x0, b.x1, b.top, b.bottom, b.size, b.font))
    return ergebnis


def _preise(boxen: list[Box], s: Schriften) -> list[Preis]:
    """Euro (groß) + Cent (kleiner, rechts daneben, 2 Ziffern oder '-')."""
    kandidaten = _ziffern_verbinden([b for b in boxen if b.font in s.preis])
    kandidaten += [b for b in boxen if b.font in s.preis and b.kompakt == "-"]
    preise = []
    for e in kandidaten:
        if e.size < 25 or not re.fullmatch(r"\d{1,3}", e.text):
            continue
        cent = next(
            (
                c
                for c in kandidaten
                if re.fullmatch(r"\d{2}|-", c.kompakt)   # "4 5" = gesperrt gesetztes "45"
                and 12 <= c.size < e.size
                and -6 <= c.x0 - e.x1 < 15                # Cent überlappen den Euro leicht (Kerning)
                and abs(c.top - e.top) < 12
            ),
            None,
        )
        if cent is None:
            continue
        wert = float(f"{e.text}.{'00' if cent.kompakt == '-' else cent.kompakt}")
        preise.append(Preis(f"{e.text},{cent.kompakt}", e.x0, cent.x1, min(e.top, cent.top),
                            max(e.bottom, cent.bottom), e.size, e.font, wert=wert))
    return preise


def _titel(boxen: list[Box], s: Schriften) -> list[Box]:
    """Titelsegmente zu Blöcken (mehrzeilige Namen, 'A oder B') zusammenfassen."""
    teile = sorted((b for b in boxen if b.font == s.titel), key=lambda b: (b.top, b.x0))
    oder = [b for b in boxen if b.font == s.beschreibung and b.text.strip() == "oder"]
    bloecke: list[Box] = []
    benutzt: set[int] = set()
    for t in teile:
        for b in bloecke:
            buendig = abs(t.x0 - b.x0) < 25 or abs(t.x1 - b.x1) < 6  # links- oder rechtsbündig
            if buendig and -3 <= t.top - b.bottom < 15:
                im_block = [o for o in oder if id(o) not in benutzt and b.x0 - 5 <= o.x0 <= max(b.x1, t.x1) + 5]
                zw = [
                    o for o in im_block
                    if b.bottom - 12 < o.top < t.top - 1                      # Zeilenende davor / eigene Zeile
                    or (abs(o.top - t.top) < 5 and o.x1 <= t.x0 + 2)          # "oder Cottage Cheese Natur"
                ]
                dh = [o for o in im_block if abs(o.top - t.top) < 4 and o.x0 >= t.x1 - 2]
                zwischen, dahinter = bool(zw), bool(dh) and not zw
                benutzt.update(id(o) for o in zw + dh)
                b.text += (" oder " if zwischen else " ") + t.text + (" oder" if dahinter else "")
                b.x0, b.x1, b.bottom = min(b.x0, t.x0), max(b.x1, t.x1), max(b.bottom, t.bottom)
                break
        else:
            bloecke.append(Box(t.text, t.x0, t.x1, t.top, t.bottom, t.size, t.font))
    return bloecke


def _naechster(quelle: Box, ziele: list, max_abstand: float, nur_darunter: bool = False):
    beste, beste_d = None, max_abstand
    for z in ziele:
        if nur_darunter and z.top < quelle.top - 5:
            continue
        d = quelle.abstand(z)
        if d < beste_d:
            beste, beste_d = z, d
    return beste


def _beschreibung(titel: Box, boxen: list[Box], s: Schriften, alle_titel: list[Box] = ()) -> str:
    return " ".join(b.text for b in _beschreibung_boxen(titel, boxen, s, alle_titel))


def _beschreibung_boxen(titel: Box, boxen: list[Box], s: Schriften, alle_titel: list[Box] = ()) -> list[Box]:
    # bis zum nächsten Produktnamen in derselben Spalte, höchstens 130 pt
    darunter = [t.top for t in alle_titel if t.top > titel.bottom and abs(t.x0 - titel.x0) < 60]
    grenze = min([titel.bottom + 130] + [t - 2 for t in darunter])
    return [
        b for b in boxen
        if b.font == s.beschreibung and b.text.strip() != "oder"
        and b.size >= 7.5 and b.x1 - b.x0 < 320                # keine Fußzeilen/Kleingedrucktes
        and titel.bottom - 3 <= b.top <= grenze
        and (titel.x0 - 5 <= b.x0 <= titel.x0 + 40 or abs(b.x1 - titel.x1) < 8)  # links- oder rechtsbündig
    ]


_NORMALPREIS_RE = re.compile(r"(?i)(?:statt\*?|^\s*1\s+\w+)\s+(\d+,\d{2}|\d+,-)")
_AB_MENGE_RE = re.compile(r"(?:ab|bei)\s+(\d+)\s+\w+\s+je")
_MENGE_RE = re.compile(
    r"(?:(\d+)\s*x\s*)?(\d+(?:,\d+)?)(?:\s*[-–/]+\s*\d+(?:,\d+)?)*\s*-?\s*(kg|g|ml|Liter|l)\b(?!\))"
)


def _zahl(text: str) -> float:
    return float(text.replace(",-", ",00").replace(",", "."))


def analysiere_seite(woerter: list[dict], seite: int, s: Schriften = SPAR_SCHRIFTEN) -> list[FlugblattAngebot]:
    boxen = segmente(woerter)
    preise = _preise(boxen, s)
    titel = _titel(boxen, s)

    # 1. Zusatzpreise markieren (Hinweis steht über dem Preis)
    for m in (z for z in zeilen(boxen) if any(k in z.kompakt.lower() for k in _ZUSATZ_MARKER)):
        p = _naechster(m, preise, 120, nur_darunter=True)
        if p:
            p.zusatz = True
            if "spar-app" in m.kompakt.lower():
                p.zusatz_text = "SPAR-App"
    haupt = [p for p in preise if not p.zusatz]

    # 2. Hauptpreise → Titel (greedy über alle Paare, bester Abstand zuerst)
    erwartet = {id(t): erwartete_preise(_beschreibung(t, boxen, s, titel) or t.text) for t in titel}
    paare = []
    for p in haupt:
        for t in titel:
            d = p.abstand(t) + (LINKS_STRAFE if p.x1 < t.x0 else 0)
            if erwartet[id(t)]:  # Grundpreis-Kontrolle: "400-g-Becher (= per kg 1,98)" -> 0,79
                passt = any(abs(p.wert - e) <= max(0.02, e * 0.015) for e in erwartet[id(t)])
                d += GRUNDPREIS_BONUS if passt else GRUNDPREIS_STRAFE
            paare.append((d, id(p), id(t), p, t))
    paare.sort(key=lambda x: x[0])
    zuordnung: dict[int, Box] = {}
    vergeben: set[int] = set()
    for d, pid, tid, p, t in paare:
        if pid in zuordnung or tid in vergeben or d > 400:
            continue
        zuordnung[pid], _ = t, vergeben.add(tid)

    angebote: dict[int, FlugblattAngebot] = {}
    for p in haupt:
        t = zuordnung.get(id(p))
        if t is None:
            continue
        beschr = _beschreibung(t, boxen, s, titel)
        menge, einheit = _menge_aus_text(beschr) or _menge_aus_text(t.text) or _stueck_aus_text(beschr) or (None, None)
        erw = erwartet[id(t)]
        angebot = FlugblattAngebot(
            seite=seite, name=t.text, preis=p.wert, beschreibung=beschr,
            menge=menge, einheit=einheit, pro_kg=bool(re.search(r"\bper kg\b", beschr)) and menge is None,
            grundpreis_ok=any(abs(p.wert - e) <= max(0.02, e * 0.015) for e in erw) if erw else None,
        )
        for b in (t, p, *_beschreibung_boxen(t, boxen, s, titel)):
            angebot._erweitern(b)
        angebot.name_bbox = (t.x0, t.top, t.x1, t.bottom)
        angebot.preis_bbox = (p.x0, p.top, p.x1, p.bottom)
        angebote[id(p)] = angebot

    # 3. Bedingungen ("statt 7,99", "1 Becher 1,99 ab 2 Becher je") → Preis darunter
    bedingungen: dict[int, list[Box]] = {}
    for b in (b for b in boxen if b.font in s.bedingung or re.match(r"(?i)statt\b", b.text)):
        p = _naechster(b, haupt, MAX_ABSTAND_BEDINGUNG, nur_darunter=True) or _naechster(
            b, haupt, MAX_ABSTAND_BEDINGUNG / 2  # z. B. "20% billiger!" unter dem Preis
        )
        if p is not None and id(p) in angebote:
            bedingungen.setdefault(id(p), []).append(b)
    vorlagen = _vorlagen_bedingungen(bedingungen)
    for pid, bs in bedingungen.items():
        a = angebote[pid]
        for b in bs:
            a._erweitern(b)
            if id(b) in vorlagen:
                continue
            if (m := _NORMALPREIS_RE.search(b.text)) and a.normalpreis is None:
                a.normalpreis = _zahl(m.group(1))
            if m := _AB_MENGE_RE.search(b.text):
                a.ab_menge = int(m.group(1))
            if "billiger" in b.text or "SPAREN" in b.text:
                a.aktion.append(re.sub(r"statt\s+\S+\s*", "", b.text).strip())

    # 4. Zusatzpreise → nächster Hauptpreis
    for p in (p for p in preise if p.zusatz):
        h = _naechster(p, [h for h in haupt if id(h) in angebote], 200)
        if h:
            angebote[id(h)].zusatzpreis = p.wert
            angebote[id(h)].zusatz_text = p.zusatz_text
            angebote[id(h)]._erweitern(p)

    # 5. Badges (Preisschrift, aber kein Preis) → nächster Hauptpreis
    preis_teile = {(b.x0, b.top) for p in preise for b in boxen if p.x0 <= b.x0 <= p.x1 and p.top <= b.top <= p.bottom}
    for b in boxen:
        if b.font not in s.preis or (b.x0, b.top) in preis_teile or b.size < 9:
            continue
        if any(k in b.kompakt.lower() for k in _ZUSATZ_MARKER) or re.fullmatch(r"[\d\s.,%-]+", b.text):
            continue
        h = _naechster(b, [h for h in haupt if id(h) in angebote], MAX_ABSTAND_BADGE, nur_darunter=True)
        if h:
            angebote[id(h)].aktion.append(b.text)
            angebote[id(h)]._erweitern(b)

    for a in angebote.values():
        a.aktion = aktion_normalisieren(a.aktion)
    return sorted(angebote.values(), key=lambda a: a.name)


def _vorlagen_bedingungen(bedingungen: dict[int, list[Box]]) -> set[int]:
    """Bedingungen (id der Box), die übrig gebliebene Vorlagen sind und ignoriert werden müssen.

    Manche Seiten enthalten unter dem echten Hinweis ("1 Packung 14,99 / ab 2 Packungen je") eine verdeckte Vorlage
    in anderer Schriftgröße ("1 PACKUNG 2,29 / AB 4 PACKUNGEN JE"), die bei allen Angeboten gleich lautet.
    Erkennung: Ein Preis hat Bedingungen in mehreren Schriftgrößen, und eine davon steht wortgleich auch bei anderen
    Preisen. Diese Gruppe fällt weg – nur, wenn eine andere Gruppe übrig bleibt.
    """
    preis_bezogen = lambda b: bool(_NORMALPREIS_RE.search(b.text) or _AB_MENGE_RE.search(b.text.lower()))
    haeufigkeit: dict[str, int] = {}
    for bs in bedingungen.values():
        for text in {b.text for b in bs if preis_bezogen(b)}:
            haeufigkeit[text] = haeufigkeit.get(text, 0) + 1
    vorlagen: set[int] = set()
    for bs in bedingungen.values():
        gruppen: dict[float, list[Box]] = {}
        for b in (b for b in bs if preis_bezogen(b)):
            gruppen.setdefault(round(b.size, 1), []).append(b)
        if len(gruppen) < 2:
            continue
        doppelt = [g for g in gruppen.values() if all(haeufigkeit[b.text] > 1 for b in g)]
        if 0 < len(doppelt) < len(gruppen):
            vorlagen.update(id(b) for g in doppelt for b in g)
    return vorlagen


_AKTION_MUSTER = [
    (re.compile(r"(\d+)\s*\+\s*(\d+)\s*GRATIS", re.I), lambda m: f"{m.group(1)}+{m.group(2)} GRATIS"),
    (re.compile(r"MENGEN\s*VORTEIL", re.I), lambda m: "MENGENVORTEIL"),
    (re.compile(r"(?:bis zu\s+)?(\d+)\s*%\s*(billiger|SPAREN)!?", re.I), lambda m: f"-{m.group(1)}%"),
    (re.compile(r"1\s*/\s*2\s*PREIS", re.I), lambda m: "1/2 PREIS"),
    (re.compile(r"Sie sparen\s+([\d,]+-?)!?", re.I), lambda m: f"Sie sparen {m.group(1)}"),
    (re.compile(r"Nur für kurze Zeit", re.I), lambda m: "Nur für kurze Zeit"),
    (re.compile(r"MONATSSPARER", re.I), lambda m: "MONATSSPARER"),
    (re.compile(r"IMMER BILLIG", re.I), lambda m: "IMMER BILLIG"),
    (re.compile(r"\bNEU\b"), lambda m: "NEU"),
]


def aktion_normalisieren(teile: list[str]) -> list[str]:
    """Badge-Fragmente ('MENGEN', 'VORTEIL', '2 + 1', 'GRATIS', 'F r , 2 0 .') zu sauberen Labels."""
    text = " ".join(teile)
    labels = []
    for muster, label in _AKTION_MUSTER:
        for m in muster.finditer(text):
            l = label(m)
            if l not in labels:
                labels.append(l)
    return labels


_GRUNDPREIS_RE = re.compile(r"\(=\s*per\s+(kg|Liter)\s+([\d,/–\-\s]+?)\)")


# "1 Flasche reicht für 12 Liter Fertiggetränk", "ergibt 6 l": das ist nicht die Packungsgröße
_ERGIBT_RE = re.compile(r"(?:reicht\s+für|ergibt|für\s+ca\.?)\s*\d+(?:,\d+)?\s*(?:Liter|l|ml)\b", re.IGNORECASE)


def erwartete_preise(beschreibung: str) -> list[float]:
    """Aus Menge und Grundpreis die zu erwartenden Preise berechnen.

    "400-g-Becher (= per kg 1,98)" -> [0.79]; "215-/200-g-Becher (= per kg 5,53/5,95)" -> [1.19, 1.28]
    """
    m = _GRUNDPREIS_RE.search(beschreibung)
    mengen = _alle_mengen(beschreibung)
    if not m or not mengen:
        return []
    werte = [_zahl(w) for w in re.split(r"[/–]|\s-\s", m.group(2)) if re.fullmatch(r"\s*\d+,\d+\s*", w)]
    return [round(w * menge / 1000, 2) for w in werte for menge in mengen]


def _alle_mengen(text: str) -> list[float]:
    """Alle Mengenvarianten in g/ml: '215-/200-g-Becher' -> [215, 200], '20 x 0,5-Liter' -> [10000]."""
    m = _MENGE_RE.search(_ERGIBT_RE.sub(" ", text))
    if not m:
        return []
    faktor = {"kg": 1000, "g": 1, "ml": 1, "Liter": 1000, "l": 1000}[m.group(3)]
    anzahl = int(m.group(1)) if m.group(1) else 1
    zahlen = re.findall(r"\d+(?:,\d+)?", m.group(0)[len(m.group(1) or ""):])
    return [_zahl(z) * faktor * anzahl for z in zahlen]


_STUECK_RE = re.compile(r"(\d+)(?:er|-Stück)-(?:Packung|Pack|Tray|Box)")


def _stueck_aus_text(text: str) -> tuple[float, str] | None:
    """'10er-Packung' -> (10, 'stk')."""
    m = _STUECK_RE.search(text)
    return (float(m.group(1)), "stk") if m else None


def _menge_aus_text(text: str) -> tuple[float, str] | None:
    text = _ERGIBT_RE.sub(" ", text)
    if re.search(r"\bper 100\s?g\b", text) and not re.search(r"\d-g-", text):
        return 100.0, "g"   # Thekenware "In Bedienung per 100 g": Preis gilt für 100 g
    m = _MENGE_RE.search(text)
    if not m:
        return None
    anzahl = f"{m.group(1)} x " if m.group(1) else ""
    menge, einheit = parse_menge(f"{anzahl}{m.group(2)} {m.group(3).replace('Liter', 'l')}")
    return (menge, einheit) if menge else None


def woerter_aus_pdf(pfad, seite: int) -> list[dict]:
    """Wörter einer PDF-Seite (1-basiert) in Content-Stream-Reihenfolge. Braucht pdfplumber."""
    import pdfplumber

    with pdfplumber.open(pfad) as pdf:
        return pdf.pages[seite - 1].extract_words(use_text_flow=True, extra_attrs=["size", "fontname"])


def main(argv: list[str] | None = None) -> int:
    """python -m aktionen.flugblatt_pdf flugblatt.pdf [seite ...]"""
    import argparse

    import pdfplumber

    p = argparse.ArgumentParser(prog="python -m aktionen.flugblatt_pdf")
    p.add_argument("pdf")
    p.add_argument("seiten", nargs="*", type=int, help="Seitennummern (Standard: alle)")
    args = p.parse_args(argv)

    with pdfplumber.open(args.pdf) as pdf:
        seiten = args.seiten or range(1, len(pdf.pages) + 1)
        for n in seiten:
            woerter = pdf.pages[n - 1].extract_words(use_text_flow=True, extra_attrs=["size", "fontname"])
            angebote = analysiere_seite(woerter, n)
            if not angebote:
                continue
            print(f"=== Seite {n}")
            for a in angebote:
                extra = []
                if a.normalpreis:
                    extra.append(f"{'ab ' + str(a.ab_menge) + ' Stk, ' if a.ab_menge else ''}sonst {a.normalpreis:.2f}")
                if a.zusatzpreis:
                    extra.append(f"Zusatz {a.zusatzpreis:.2f}")
                extra += a.aktion
                menge = f"{a.menge:g} {a.einheit}" if a.menge else ("per kg" if a.pro_kg else "")
                print(f"{a.preis:7.2f} €  {a.name[:50]:50s} {menge:9s} {' | '.join(extra)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
