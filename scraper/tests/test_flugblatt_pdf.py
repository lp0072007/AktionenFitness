"""Tests für die PDF-Auswertung, geprüft gegen das echte Flugblatt (Spar NÖ KW47).

Die erwarteten Werte stammen aus dem Ansehen der jeweiligen Seite.
"""

import json
from pathlib import Path

import pytest

from aktionen.flugblatt_pdf import aktion_normalisieren, analysiere_seite, erwartete_preise

FIXTURES = Path(__file__).parent / "fixtures"


def seite(n):
    woerter = json.loads((FIXTURES / f"spar_pdf_noe_kw47_s{n}.json").read_text(encoding="utf-8"))["woerter"]
    return {a.name: a for a in analysiere_seite(woerter, n)}


# Name: (Preis, Normalpreis/Einzelpreis, ab Menge, Zusatzpreis)
ERWARTET = {
    14: {
        "Bio-Wiener Kipferl": (1.03, 1.55, 3, 0.77),
        "Premium-Baguette Korn": (2.29, 2.89, None, 1.99),
        "Premium Bio-Handsemmel": (0.60, 0.90, 3, 0.45),
        "Ciabattaweckerl": (0.62, 0.94, 3, None),
        "Vorarlberger Bergkäse g.U.": (5.49, 7.99, None, None),
        "DESPAR Gorgonzola Mascarpone": (2.39, 2.99, None, None),
        "Schärdinger Bergbaron": (2.52, 3.79, 3, None),
        "Wojnar‘s Original Liptauer": (3.99, None, None, None),
        "Schärdinger Mozzarella Minis": (1.26, 1.89, 3, None),
        "NÖM PRO Cottage Cheese oder Cottage Cheese Natur": (1.19, 1.99, 2, None),
    },
    9: {
        "Rindsschnitzel aus Österreich": (19.99, None, None, 14.99),
        "Ausgelöster Schweinsschopfbraten aus Österreich": (7.99, None, None, 5.99),
        "Karreebraten aus Österreich": (7.99, None, None, 5.99),
        "Frische Putenbrust, Putenschnitzerl, Putengeschnetzeltes oder Maishendlfilet": (12.99, None, None, 9.74),
        "S-BUDGET Puteninnenfilet": (13.99, None, None, None),
        "Faschierte Laibchen oder Geflügel Laibchen": (2.29, 2.49, None, None),
        "Chicken Nuggets": (2.49, 2.99, None, None),
        "Wieselburger 0,0% Alkoholfrei": (8.04, None, None, 4.02),
    },
    12: {
        "Schärdinger Kefir Himbeer oder Mango-Maracuja": (0.64, 1.29, 2, None),
        "Schärdinger Joghurttraum": (0.79, 1.23, 2, None),
        "Oswald Schofrulade": (2.49, 3.49, 2, None),
        "Ferrero Kinder Maxi King": (1.69, 1.99, 2, None),
        "Schärdinger Bergbauern Joghurt": (0.40, 0.81, 4, None),
        "Iglo Gemüse oder Protein Mix": (2.08, 3.13, 3, None),
    },
}


@pytest.mark.parametrize("n", sorted(ERWARTET))
def test_preise_richtig_zugeordnet(n):
    gefunden = seite(n)
    for name, (preis, normal, ab, zusatz) in ERWARTET[n].items():
        assert name in gefunden, f"S. {n}: {name} fehlt, gefunden: {sorted(gefunden)}"
        a = gefunden[name]
        assert (a.preis, a.normalpreis, a.ab_menge, a.zusatzpreis) == (preis, normal, ab, zusatz), name


def test_seite_14_vollstaendig():
    assert len(seite(14)) == 10


def test_wieselburger_beide_gebinde():
    preise = sorted(a.preis for a in analysiere_seite(
        json.loads((FIXTURES / "spar_pdf_noe_kw47_s9.json").read_text(encoding="utf-8"))["woerter"], 9
    ) if a.name == "Wieselburger Gold")
    assert preise == [26.80, 34.80]


def test_mengen_und_aktion():
    s14 = seite(14)
    nom = s14["NÖM PRO Cottage Cheese oder Cottage Cheese Natur"]
    assert (nom.menge, nom.einheit) == (215, "g")
    assert nom.aktion == ["MENGENVORTEIL", "-40%"]
    assert s14["Schärdinger Bergbaron"].aktion == ["2+1 GRATIS"]
    assert seite(9)["Rindsschnitzel aus Österreich"].pro_kg


@pytest.mark.parametrize(
    "text,erwartet",
    [
        ("Aus Österreich, 400-g-Becher (= per kg 1,98)", [0.79]),
        ("215-/200-g-Becher (= per kg 5,53/5,95)", [1.19, 1.11, 1.28, 1.19]),
        ("0,75-Liter-Flasche (= per Liter 14,65)", [10.99]),
        ("In Bedienung per kg", []),
    ],
)
def test_erwartete_preise(text, erwartet):
    assert erwartete_preise(text) == erwartet


def test_aktion_normalisieren():
    assert aktion_normalisieren(["MENGEN", "VORTEIL", "40% billiger!"]) == ["MENGENVORTEIL", "-40%"]
    assert aktion_normalisieren(["2 + 1", "GRATIS", "F r , 2 0 .", "400 g"]) == ["2+1 GRATIS"]
