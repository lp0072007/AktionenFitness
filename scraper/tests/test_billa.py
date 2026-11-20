from datetime import date

import httpx

from aktionen.stores.billa import aktuelle_angebote, kategorien_aus_html, parse_produkt


def produkt(**kw):
    # Aufbau wie shop.billa.at/api/product-discovery/categories/kuehlwaren-15416/products?inPromotion=true (20.11.2026)
    p = {
        "sku": "00-123", "name": "Skyr Natur Ungesüßt", "brand": {"name": "Alpro"}, "amount": "400",
        "volumeLabelShort": "g", "weightArticle": False, "slug": "alpro-skyr-natur-00123", "images": ["https://x/y.jpg"],
        "parentCategories": [[{"name": "Kühlwaren"}, {"name": "Milchprodukte"}, {"name": "Joghurt"}]],
        "price": {"crossed": 199, "discountPercentage": -33,
                  "regular": {"value": 132, "promotionQuantity": 3, "promotionType": "PER_SET_OF",
                              "promotionText": "Bei 3 Becher je"},
                  "standard": {"value": 199}},
    }
    p.update(kw)
    return p


def test_parse_billa():
    a = parse_produkt(produkt())
    assert (a.name, a.preis, a.normalpreis, a.ab_menge, a.menge) == ("Alpro Skyr Natur Ungesüßt", 1.32, 1.99, 3, 400)
    assert a.gueltig_von is None  # Billa liefert keine Gültigkeit
    assert a.url == "https://shop.billa.at/produkte/alpro-skyr-natur-00123"
    assert a.kategorie_pfad == "Kühlwaren > Milchprodukte > Joghurt"


def test_normalpreis_aus_standard_ohne_crossed():
    p = produkt()
    p["price"] = {"regular": {"value": 269}, "standard": {"value": 399}}
    assert parse_produkt(p).normalpreis == 3.99


def test_kategorien_aus_html():
    html = ('product-group-kuehlwaren-15416-{\\"inPromotion\\":\\"true\\"} product-group-haustier-15672-{\\"inPromotion\\"'
            ' product-group-tiefkuehl-15415-{"inPromotion":"true"}')
    assert kategorien_aus_html(html) == ["kuehlwaren-15416", "tiefkuehl-15415"]


def test_ablauf_mehrere_kategorien():
    def handler(r):
        if r.url.path == "/aktionen":
            return httpx.Response(200, text='product-group-kuehlwaren-15416-{"inPromotion" product-group-tiefkuehl-15415-{"inPromotion"')
        if "kuehlwaren" in r.url.path:
            return httpx.Response(200, json={"total": 2, "results": [produkt(sku="1"), produkt(sku="2", name="Skyr Vanille")]})
        return httpx.Response(200, json={"total": 1, "results": [produkt(sku="1")]})  # doppelt -> nur einmal

    c = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://shop.billa.at")
    a = aktuelle_angebote(heute=date(2026, 11, 20), client=c, pause=0)
    assert sorted(x.name for x in a) == ["Alpro Skyr Natur Ungesüßt", "Alpro Skyr Vanille"]


def test_kategorie_umbenannt_liest_aktuelle_liste():
    from aktionen.stores import billa

    aufrufe = []

    def handler(r):
        aufrufe.append(r.url.path)
        if r.url.path == "/aktionen":
            return httpx.Response(200, text='product-group-kuehlwaren-neu-99999-{"inPromotion"')
        if "kuehlwaren-neu-99999" in r.url.path:
            return httpx.Response(200, json={"total": 1, "results": [produkt(sku="9")]})
        if "obst-und-gemuese" in r.url.path:
            return httpx.Response(404, json={})
        return httpx.Response(200, json={"total": 0, "results": []})

    c = httpx.Client(transport=httpx.MockTransport(handler))
    a = billa.aktuelle_angebote(heute=date(2026, 11, 20), client=c, pause=0)
    assert [x.produkt_id for x in a] == ["9"]
    assert aufrufe.count("/aktionen") == 1      # Übersicht nur einmal und nur wegen der 404
