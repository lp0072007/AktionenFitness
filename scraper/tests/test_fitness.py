import json
from pathlib import Path

import pytest

from aktionen.fitness import fitness_angebote, kategorie_fuer, rangliste
from aktionen.flugblatt_pdf import FlugblattAngebot, analysiere_seite

FIXTURES = Path(__file__).parent / "fixtures"


def angebote(*seiten):
    out = []
    for n in seiten:
        w = json.loads((FIXTURES / f"spar_pdf_noe_kw47_s{n}.json").read_text(encoding="utf-8"))["woerter"]
        out += analysiere_seite(w, n)
    return out


@pytest.mark.parametrize(
    "name,kategorie",
    [
        ("NÖM PRO Cottage Cheese oder Cottage Cheese Natur", "Cottage Cheese"),
        ("S-BUDGET Hendlfilet aus Österreich", "Hühnerbrust"),
        ("S-BUDGET Puten-Faschiertes oder Hendl-Faschiertes", "Geflügel-Faschiertes"),
        ("Frische Putenbrust, Putenschnitzerl, Putengeschnetzeltes oder Maishendlfilet", "Hühnerbrust"),
        ("Bio-Basmati-Reis", "Reis"),
        ("Rummo Pasta", "Nudeln"),
        ("Große Bio-Eier", "Eier"),
        ("Meisterbäcker Ölz Eiweißbrot geschnitten", "Eiweißbrot"),
        # nicht fitnessrelevant
        ("Playmobil großer Traktor mit Kartoffelroder", None),
        ("Lindt Lindor Kugeln", None),
        ("Wieselburger Gold", None),
        ("Chicken Nuggets", None),
        ("Maggi Magic Asia Saucy Noodles oder Korean Style Noodles", None),
    ],
)
def test_kategorie(name, kategorie):
    k = kategorie_fuer(name)
    assert (k.name if k else None) == kategorie


def test_protein_pro_euro_cottage_cheese():
    t = {t.angebot.name: t for t in fitness_angebote(angebote(14))}
    cc = t["NÖM PRO Cottage Cheese oder Cottage Cheese Natur"]
    # 215 g * 10,5 g/100 g = 22,6 g Protein für 1,19 € (Aktionspreis ab 2 Stück)
    assert cc.protein_pro_euro == 19.0
    assert cc.protein_pro_100kcal == 11.1
    assert len(t) == 1  # Käse, Gebäck & Co. auf S. 14 sind nicht fitnessrelevant (Cottage Cheese schon)


def test_per_kg_und_zusatzpreis():
    t = {t.angebot.name: t for t in fitness_angebote(angebote(9))}
    rind = t["Rindsschnitzel aus Österreich"]
    assert rind.gramm == 1000
    assert rind.protein_pro_euro == 11.0          # 220 g / 19,99 €
    assert rind.protein_pro_euro_zusatz == 14.7   # 220 g / 14,99 € (Fr/Sa)
    assert "Chicken Nuggets" not in t


def test_stueckware_eier():
    a = FlugblattAngebot(seite=8, name="Große Bio-Eier", preis=5.14, menge=10, einheit="stk")
    (t,) = fitness_angebote([a])
    assert t.gramm == 600
    assert t.protein_pro_euro == 14.6


def test_rangliste_ziele():
    t = fitness_angebote(angebote(9, 14))
    protein = rangliste(t, "protein")
    assert [x.protein_pro_euro for x in protein] == sorted((x.protein_pro_euro or 0 for x in t), reverse=True)
    diaet = rangliste(t, "diaet")
    assert all(x.protein_pro_100kcal >= 8 for x in diaet[:3])


def test_thunfisch_in_oel_ueber_beschreibung():
    assert kategorie_fuer("Nixe Thunfischfilets", "Je 4x 185 g · 1 kg = 6.47 · In Sonnenblumenöl").name == "Thunfisch in Öl"
    assert kategorie_fuer("Nixe Thunfischfilets", "Je 4x 185 g · im eigenen Saft").name == "Thunfisch"
    assert kategorie_fuer("Deluxe Frische Lammlachse vom Merino Lamm natur") is None
