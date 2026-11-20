from datetime import date

from aktionen.stores.lidl import angebotsseiten, parse_produkt, produkte_aus_html

# Gekürzte echte Datensätze von lidl.at (20.11.2026)
DORSCH = {
    "productId": 10096371, "category": "Food", "title": "MSC Polar-Dorsch", "fullTitle": "MSC Polar-Dorsch",
    "canonicalUrl": "/p/msc-polar-dorsch/p10096371", "image": "https://www.lidl.at/assets/x.png",
    "storeStartDate": 1795388400, "storeEndDate": 1795647599,
    "price": {"price": 4.49, "packaging": {"text": "Bei 2 Stk. je 400 g (Einzeln = 8.99)"},
              "basePrice": {"text": "1 kg = 11.23"}},
}
BANANEN = {
    "productId": 11150766, "category": "F+V", "title": "Bananen", "fullTitle": "Bananen",
    "storeStartDate": 1795388400, "storeEndDate": 1795647599,
    "price": {"price": 1.11, "oldPrice": 1.69, "packaging": {"text": "Je kg"},
              "discount": {"discountText": "-34%", "deletedPrice": 1.69}},
    "lidlPlus": [{"price": {"price": 0.99}, "lidlPlusText": "Mit Lidl Plus"}],
}
THUNFISCH = {
    "productId": 11007054, "category": "Food", "title": "Thunfischfilets", "fullTitle": "Nixe Thunfischfilets",
    "price": {"price": 4.79, "packaging": {"text": "Je 4x 185 g"}, "basePrice": {"text": "1 kg = 6.47"}},
    "keyfacts": {"description": "<p>In Sonnenblumen&ouml;l</p>"},
}


def test_mengenaktion():
    a = parse_produkt(DORSCH)
    assert (a.preis, a.ab_menge, a.normalpreis, a.menge, a.einheit) == (4.49, 2, 8.99, 400, "g")
    assert "MENGENVORTEIL" in a.aktion
    assert a.gueltig_von == date(2026, 11, 23) and a.gueltig_bis == date(2026, 11, 25)  # österreichische Zeit
    assert a.url == "https://www.lidl.at/p/msc-polar-dorsch/p10096371"


def test_kilopreis_streichpreis_lidl_plus():
    a = parse_produkt(BANANEN)
    assert a.pro_kg and a.menge is None
    assert a.normalpreis == 1.69 and a.aktion == ["-34%"]
    assert (a.zusatzpreis, a.zusatz_text) == (0.99, "Lidl Plus")


def test_multipack_und_beschreibung():
    a = parse_produkt(THUNFISCH)
    assert (a.menge, a.einheit) == (740, "g")
    assert "In Sonnenblumenöl" in a.beschreibung


def test_nonfood_wird_ignoriert():
    assert parse_produkt({"category": "NonFood", "title": "Spielküche", "price": {"price": 39.99}}) is None


def test_angebotsseiten_und_grid_daten():
    html = ('<a href="/c/store/aktion/a10107111">x</a><a href="https://www.lidl.at/c/store/parkside-r-du-packst-das/a1">'
            '</a><a href="/c/store/aktion/a10107111"></a><div data-grid-data="{&quot;title&quot;:&quot;Nudeln&quot;}">')
    assert angebotsseiten(html) == ["/c/store/aktion/a10107111"]
    assert produkte_aus_html(html) == [{"title": "Nudeln"}]


def test_wiederholung_nach_abbruch():
    import httpx

    from aktionen.stores.base import get_mit_wiederholung

    versuche = []

    def handler(r):
        versuche.append(1)
        if len(versuche) < 3:
            raise httpx.RemoteProtocolError("Server disconnected without sending a response.")
        return httpx.Response(200, text="ok")

    c = httpx.Client(transport=httpx.MockTransport(handler))
    assert get_mit_wiederholung(c, "https://www.lidl.at/", warte=0).text == "ok"
    assert len(versuche) == 3


def test_wartet_bei_429():
    import httpx

    from aktionen.stores.base import get_mit_wiederholung

    antworten = [httpx.Response(429, headers={"retry-after": "0"}), httpx.Response(200, text="ok")]
    c = httpx.Client(transport=httpx.MockTransport(lambda r: antworten.pop(0)))
    assert get_mit_wiederholung(c, "https://x/", warte=0).text == "ok"
