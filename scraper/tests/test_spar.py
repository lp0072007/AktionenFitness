"""Tests für den Spar-Parser auf Basis einer echten Interspar-Antwort (tests/fixtures/spar_flyout_skyr.json)."""

import json
from pathlib import Path

import pytest

from aktionen.models import Angebot
from aktionen.stores.base import parse_menge, parse_preis
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
