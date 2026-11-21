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


@pytest.mark.parametrize(
    "name,kategorie",
    [
        # Billa-Fehlerkennungen (KW 47)
        ("Knorr Basis für Pasta Gemüse", None),
        ("nöm PRO Banane Proteindrink", None),
        ("Billa immer gut BILLA Peanut Butter Eis", None),
        ("Billa immer gut BILLA Thunfisch Baguette", None),
        ("Iglo Backrohr Kartoffelpuffer", None),
        ("Billa immer gut BILLA Erdäpfeltascherl", None),
        ("Iglo Mohnnudeln", None),
        ("Vegavita Bananensplit", None),
        ("Clever Alaska Seelachs paniert", None),
        # weiterhin erkannt
        ("Clever Alaska-Seelachsfilets ohne Haut", "Magerer Fisch"),
        ("Recheis Familie Spaghetti", "Nudeln"),
        ("Alpro Skyr Natur Ungesüßt", "Skyr"),
        ("d'aucy Linsen", "Linsen & Bohnen"),
        ("Berida Lachsfilet", "Lachs"),
    ],
)
def test_billa_fehlerkennungen(name, kategorie):
    k = kategorie_fuer(name)
    assert (k.name if k else None) == kategorie


def test_zero_sirup_ist_fitnessrelevant():
    from aktionen.fitness import kategorie_fuer
    for name in ["fyl Sirup Holunderblüte", "flavour your life Himbeere", "Mautner Markhof 0% Himbeer Sirup",
                 "Zero Sirup Cola"]:
        assert kategorie_fuer(name).name == "Zero-Sirup", name
    assert kategorie_fuer("Mautner Markhof Holunderblüten Sirup") is None  # mit Zucker


def test_reicht_fuer_ist_keine_packungsgroesse():
    from aktionen.flugblatt_pdf import _menge_aus_text
    assert _menge_aus_text("1 Flasche reicht für 12 Liter Fertiggetränke, 48-ml-EINWEG-Flasche (= per Liter 72,70)") == (48, "ml")


def test_energy_und_zero_getraenke():
    from aktionen.fitness import kategorie_fuer
    assert kategorie_fuer("KONG STRONG Energy Drink Classic").name == "Energy Drink"
    assert kategorie_fuer("KONG STRONG Energy Drink light").name == "Energy Drink zero"
    assert kategorie_fuer("Red Bull Sugarfree").name == "Energy Drink zero"
    assert kategorie_fuer("Coca Cola Zero").name == "Zero-Getränk"
    assert kategorie_fuer("Almdudler od. Almdudler zuckerfrei").name == "Zero-Getränk"
    assert kategorie_fuer("Gösser Zero Bier") is None
    assert kategorie_fuer("Krispel Zero Rot") is None


def test_joghurt_und_kefir():
    from aktionen.fitness import kategorie_fuer
    assert kategorie_fuer("Alpengut Kefir Natur").name == "Kefir"
    assert kategorie_fuer("Ich bin Österreich Naturjoghurt").name == "Joghurt"
    assert kategorie_fuer("Schärdinger Greek Style Mango & Maracuja Joghurt").name == "Griechisches Joghurt"
    assert kategorie_fuer("Müller Knusperjoghurt") is None
    assert kategorie_fuer("Schärdinger Joghurttraum") is None


def test_obst_und_gemuese_nur_unverarbeitet():
    from aktionen.flugblatt_pdf import FlugblattAngebot
    from aktionen.fitness import fitness_angebote, kategorie_fuer
    assert kategorie_fuer("Apfel rot").name == "Obst"
    assert kategorie_fuer("WUNDERLINGE Erdäpfel").name == "Erdäpfel"  # nicht Obst
    assert kategorie_fuer("Knackiger Eissalat").name == "Gemüse"
    assert kategorie_fuer("Billa immer gut BILLA Nudel Salat nach griechischer Art") is None
    assert kategorie_fuer("Oswald Schofrulade Himbeere") is None
    # Händler-Kategorie entscheidet mit: Saft ist kein Obst, TK-Gemüse schon
    saft = FlugblattAngebot(seite=0, name="Rauch Happy Day Orange Mild", preis=2.0,
                            kategorie_pfad="Getränke > Alkoholfreie Getränke > Frucht- & Gemüsesäfte")
    tk = FlugblattAngebot(seite=0, name="Iglo Erbsen", preis=2.0, kategorie_pfad="Tiefkühl > Obst, Gemüse & Kräuter > Gemüse")
    assert [t.angebot.name for t in fitness_angebote([saft, tk])] == ["Iglo Erbsen"]
