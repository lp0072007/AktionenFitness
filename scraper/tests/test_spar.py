"""Tests für den Spar-Parser.

Die Fixture `spar_alt_format.json` ist von Hand nachgebaut nach dem (alten) Feldformat aus heissepreise.
Sobald eine echte Antwort vorliegt, als `spar_echt.json` ablegen und Tests darauf umstellen.
"""

import json
from pathlib import Path

import pytest

from aktionen.models import Angebot
from aktionen.stores.base import parse_menge, parse_preis
from aktionen.stores.spar import SparStore

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def raw():
    return json.loads((FIXTURES / "spar_alt_format.json").read_text(encoding="utf-8"))


def test_parse_normales_produkt(raw):
    a = SparStore().parse(raw[0])
    assert a.produkt_id == "2020001234567"
    assert a.name == "Magertopfen"
    assert a.marke == "SPAR"
    assert a.preis == 0.99
    assert (a.menge, a.einheit) == (250, "g")
    assert a.preis_pro_kg == 3.96
    assert not a.bio


def test_parse_gewichtsware(raw):
    a = SparStore().parse(raw[1])
    assert a.preis == 18.99
    assert (a.menge, a.einheit) == (1000, "g")
    assert a.bio


def test_parse_ohne_produktnummer_wird_ignoriert(raw):
    assert SparStore().parse(raw[2]) is None


@pytest.mark.parametrize(
    "text,erwartet",
    [
        ("450 g", (450, "g")),
        ("1,5 l", (1500, "ml")),
        ("4 x 125 g", (500, "g")),
        ("1 kg", (1000, "g")),
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
