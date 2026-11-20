"""Tests für den Spar-Parser auf Basis einer echten Interspar-Antwort (tests/fixtures/spar_flyout_skyr.json)."""

import json
from pathlib import Path

import pytest

from aktionen.models import Angebot
from aktionen.stores.base import parse_menge, parse_naehrwert_tabelle, parse_preis
from aktionen.stores.spar import SparStore, produkte_aus_antwort

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def produkte():
    data = json.loads((FIXTURES / "spar_flyout_skyr.json").read_text(encoding="utf-8"))
    return {p["productNumber"]: p for p in produkte_aus_antwort(data)}


def test_alle_produkte_gefunden(produkte):
    assert len(produkte) == 5


def test_parse_skyr_1kg(produkte):
    a = SparStore().parse(produkte["2020004900746"])
    assert a.kette == "spar"
    assert a.name == "S-BUDGET Skyr 1 KG"
    assert a.marke == "S-BUDGET"
    assert a.preis == 2.99
    assert (a.menge, a.einheit) == (1000, "g")
    assert a.preis_pro_kg == 2.99
    assert not a.ist_aktion
    assert a.bild_url.startswith("https://www.interspar.at/media/")


def test_parse_400g_mit_badges(produkte):
    a = SparStore().parse(produkte["2020003999345"])
    assert (a.menge, a.einheit) == (400, "g")
    assert a.preis_pro_kg == 4.98  # stimmt mit referencePrice von Spar überein
    assert a.tags == ["vegan", "lactose-free", "gluten-free"]


def test_parse_liter(produkte):
    a = SparStore().parse(produkte["2020000432623"])
    assert (a.menge, a.einheit) == (700, "ml")


def test_menge_fallback_aus_grundpreis(produkte):
    raw = dict(produkte["2020003562716"], name="Arla Skyr Natur")  # ohne Mengenangabe im Namen
    a = SparStore().parse(raw)
    assert (a.menge, a.einheit) == (400, "g")  # 1,99 € / 4,98 €/kg ≈ 400 g


def test_streichpreis_wird_erkannt(produkte):
    raw = json.loads(json.dumps(produkte["2020003562716"]))
    raw["price"]["regularPrice"] = 2.49
    a = SparStore().parse(raw)
    assert a.ist_aktion
    assert a.rabatt_prozent == 20.1


def test_ohne_produktnummer_wird_ignoriert():
    assert SparStore().parse({"name": "kaputt", "price": {"currentPrice": 1}}) is None


@pytest.mark.parametrize(
    "text,erwartet",
    [
        ("450 g", (450, "g")),
        ("Skyr 1 KG", (1000, "g")),
        ("Whisky 0,7 L", (700, "ml")),
        ("4 x 125 g", (500, "g")),
        ("10 Stk.", (10, "stk")),
        ("ohne Angabe", (None, None)),
    ],
)
def test_parse_menge(text, erwartet):
    assert parse_menge(text) == erwartet


@pytest.mark.parametrize("wert,erwartet", [(1.99, 1.99), ("1,99", 1.99), ("€8,87/kg", 8.87), ("x", None)])
def test_parse_preis(wert, erwartet):
    assert parse_preis(wert) == erwartet


def test_rabatt():
    a = Angebot(kette="spar", produkt_id="1", name="Skyr", preis=1.49, normalpreis=1.99)
    assert a.ist_aktion
    assert a.rabatt_prozent == 25.1


# --- Produktdetails ---------------------------------------------------------


@pytest.fixture
def detail():
    return json.loads((FIXTURES / "spar_detail_cottage_protein.json").read_text(encoding="utf-8"))


def test_parse_detail_grunddaten(detail):
    a = SparStore().parse_detail(detail)
    assert a.produkt_id == "2020005744769"
    assert a.marke == "Schärdinger"
    assert a.preis == 4.59
    assert (a.menge, a.einheit) == (500, "g")  # aus infoSections "Menge 0,500 / Einheit KG"
    assert a.kategorie == "Frischkäse"
    assert "preisgesenkt" in a.tags
    assert not a.ist_aktion


def test_parse_detail_naehrwerte(detail):
    n = SparStore().parse_detail(detail).naehrwerte
    assert n.kcal == 70
    assert n.protein == 12
    assert n.kohlenhydrate == 4.3
    assert n.zucker == 4.3
    assert n.fett == 0.5           # "< 0,5g"
    assert n.gesaettigte_fettsaeuren == 0.5
    assert n.salz == 0.7


def test_protein_pro_euro(detail):
    a = SparStore().parse_detail(detail)
    # 500 g * 12 g/100 g = 60 g Protein für 4,59 €
    assert a.protein_pro_euro == 13.1
    assert a.kcal_pro_euro == 76.3


def test_naehrwert_tabelle_varianten():
    n = parse_naehrwert_tabelle("Brennwert | 1500 kJ | 358 kcal\nProtein | 13,5 g\nBallaststoffe | 10 g\nNatrium | 5 mg")
    assert (n.kcal, n.protein, n.ballaststoffe) == (358, 13.5, 10)
    assert parse_naehrwert_tabelle("") is None


def test_naehrwerte_mit_prozent_spalte():
    # NÖM Cottage Cheese natur (2020001850105), echte Tabelle mit Referenzmengen-%-Spalte
    text = (
        "Energie | ca. 382kJ | ca. 91kcal | ca. 5%<br />\nFett | ca. 4,5g | ca. 6%<br />\n"
        "Fett, davon gesättigte Fettsäuren | ca. 2,7g | ca. 14%<br />\nKohlenhydrate | ca. 2,8g | ca. 1%<br />\n"
        "Kohlenhydrate, davon Zucker | ca. 2,8g | ca. 3%<br />\nEiweiß | ca. 9,9g | ca. 20%<br />\nSalz | ca. 0,85g | ca. 14%<br />"
    )
    n = parse_naehrwert_tabelle(text)
    assert (n.kcal, n.protein, n.fett, n.gesaettigte_fettsaeuren, n.kohlenhydrate, n.salz) == (91, 9.9, 4.5, 2.7, 2.8, 0.85)
