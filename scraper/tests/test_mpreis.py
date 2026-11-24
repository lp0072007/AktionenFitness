"""MPreis: echte Antwort der Typesense-Suche (Markt 8450, 24.11.2026), je ein Produkt pro Aktionsart."""

import json
from pathlib import Path

import httpx

from aktionen.stores import mpreis
from aktionen.stores.mpreis import aktuelle_angebote, kategorie_pfad, parse_produkt, suchanfrage

FIXTURE = Path(__file__).parent / "fixtures" / "mpreis_suche.json"


def dokumente():
    return {h["document"]["id"]: h["document"] for h in json.loads(FIXTURE.read_text(encoding="utf-8"))["results"][0]["hits"]}


def test_1_plus_1_gratis():
    a = parse_produkt(dokumente()["144440"])  # Ben&Jerry's-Eis (Marke laut MPreis: Tony's Chocolonely): 1 Stk 4,99, ab 2 je 2,49
    assert a.name == "Tony's Chocolonely Dark Milk Brownie Ben&Jerry's"  # Marke vorangestellt
    assert (a.preis, a.normalpreis, a.ab_menge) == (2.49, 4.99, 2)
    assert a.aktion[0] == "1+1 GRATIS"
    assert (a.menge, a.einheit) == (180, "g")


def test_typ_1_plus_1_ist_eigentlich_2_plus_1():
    # promotionType heißt "1+1 gratis", discounts sagt aber: 3 kaufen, 1 gratis
    a = parse_produkt(dokumente()["145910"])
    assert (a.preis, a.normalpreis, a.ab_menge) == (1.32, 1.99, 3)
    assert a.aktion[0] == "2+1 GRATIS"


def test_mengenaktion():
    a = parse_produkt(dokumente()["171839"])  # Lindor: "In der Menge billiger", ab 2
    assert (a.preis, a.normalpreis, a.ab_menge) == (6.0, 8.0, 2)
    assert "MENGENVORTEIL" in a.aktion


def test_preis_gesenkt_mit_rabatt():
    a = parse_produkt(dokumente()["118203"])
    assert (a.preis, a.normalpreis, a.ab_menge) == (10.0, 22.99, None)
    assert "-57%" in a.aktion
    assert a.url == "https://www.mpreis.at/shop/p/118203"
    assert a.kategorie_pfad.startswith("Getränke")


def test_dauerhaft_gesenkt_ist_keine_aktion():
    # "Preisgesenkt", aber gleicher Preis wie vorher und nicht im Flugblatt -> weglassen
    assert parse_produkt(dokumente()["206620"]) is None


def test_flugblatt_ohne_rabatt_bleibt():
    a = parse_produkt(dokumente()["172449"])
    assert a is not None and a.normalpreis is None and "FLUGBLATT" in a.aktion


def test_kiloware():
    a = parse_produkt(dokumente()["666089"])  # Salame Ungherese, Preis per kg
    assert a.pro_kg and a.menge is None
    assert (a.preis, a.normalpreis) == (19.99, 28.99)


def test_thekenware_pro_100_gramm():
    # Tiroler Adler 45% (echte Werte 24.11.2026): 1,79 € gilt pro 100 g, nicht pro kg
    d = {"id": "1", "name": "Tiroler Adler 45%", "categories": ["Käse", "Milch & Eier", "Lebensmittel", "ProductRoot"],
         "prices": {"base": {"unit": {"code": "g", "quantity": 100}}, "unit": {"code": "Stk", "quantity": 1}},
         "mixins": {"productCustomAttributes": {"weightDependent": True}},
         "product_store_data": [{"sitePrice": {"effective": 1.79, "original": 2.39, "promotionType": "Preisgesenkt"}}]}
    a = parse_produkt(d)
    assert (a.pro_kg, a.menge, a.einheit, a.preis) == (False, 100.0, "g", 1.79)
    # pro kg bleibt pro kg (Salame Ungherese: base unit kg)
    d["prices"]["base"]["unit"] = {"code": "kg", "quantity": 1}
    assert parse_produkt(d).pro_kg


def test_tippfehler_kg_statt_g():
    # Echt (24.11.2026): Milram Grieß-Dessert Kirsche mit packagingUnit "175kg" für 0,59 €
    d = {"id": "2", "name": "Grieß-Dessert Kirsche", "categories": ["Desserts", "Milch & Eier", "Lebensmittel", "ProductRoot"],
         "mixins": {"productCustomAttributes": {"packagingUnit": "175kg"}},
         "product_store_data": [{"sitePrice": {"effective": 0.59, "original": 0.89, "promotionType": "1+1 gratis",
                                               "discounts": {"forQuantity": 3, "discountQuantity": 1}}}]}
    a = parse_produkt(d)
    assert (a.menge, a.einheit) == (175, "g")
    # echte große Gebinde bleiben: 25 kg Kartoffeln um 9,99 € sind 0,40 €/kg
    d["mixins"]["productCustomAttributes"]["packagingUnit"] = "25kg"
    d["product_store_data"][0]["sitePrice"]["effective"] = 9.99
    assert parse_produkt(d).menge == 25000


def test_merkmale_vegan_bio():
    # Beide Produkte sind in der Fixture nur dauerhaft gesenkt -> keine Aktion; mit Rabatt werden sie übernommen
    assert parse_produkt(dokumente()["365763"]) is None
    vegan = mpreis.parse_produkt({**dokumente()["365763"], "product_store_data": [{"sitePrice": {
        "effective": 2.5, "original": 3.0, "promotionType": "Preisgesenkt"}}]})
    assert set(vegan.merkmale) >= {"vegan", "vegetarisch"}
    bio = mpreis.parse_produkt({**dokumente()["365270"], "product_store_data": [{"sitePrice": {
        "effective": 1.5, "original": 2.0, "promotionType": "Preisgesenkt"}}]})
    assert "bio" in bio.merkmale


def test_kategorie_pfad():
    assert kategorie_pfad(["Topfen", "Milch & Eier", "Lebensmittel", "ProductRoot"]) == "Lebensmittel > Milch & Eier > Topfen"
    assert kategorie_pfad([]) is None


def test_suchanfrage_filtert_aktionen_und_lebensmittel():
    f = suchanfrage(1)["searches"][0]["filter_by"]
    assert "storeId:=8450" in f and "isInFlyer:true" in f and "`1+1 gratis`" in f
    assert "`Immer günstig`" not in f and "`Lebensmittel`" in f


def test_aktuelle_angebote_blaettert():
    docs = list(dokumente().values())
    seiten = []

    def antwort(request):
        body = json.loads(request.content)
        seite = body["searches"][0]["page"]
        seiten.append(seite)
        # 2 Seiten simulieren: found größer als eine Seite
        hits = [{"document": d} for d in (docs[:5] if seite == 1 else docs[5:])]
        return httpx.Response(200, json={"results": [{"found": mpreis.SEITENGROESSE + 1, "hits": hits}]})

    alt = mpreis.SEITENGROESSE
    try:
        client = httpx.Client(transport=httpx.MockTransport(antwort))
        angebote = aktuelle_angebote(client=client, pause=0)
    finally:
        mpreis.SEITENGROESSE = alt
    assert seiten == [1, 2]
    ids = [a.produkt_id for a in angebote]
    assert len(ids) == len(set(ids)) and "206620" not in ids  # keine Doppelten, dauerhaft gesenkt weg
