import httpx

from aktionen.fitness import fitness_angebote, kategorie_fuer
from aktionen.stores.dm import aktuelle_angebote, parse_produkt


def produkt(titel, preis="2,00 €", marke="dmBio", kategorien=("Gemüsesäfte & Ingwershots",), vorher=None, dan=1):
    # Aufbau wie product-search.services.dmtech.com/at/search/crawl (20.11.2026), gekürzt
    p = {"dan": dan, "brandName": marke, "title": titel, "tileData": {
        "self": f"/p/d/{dan}/x", "images": [{"tileSrc": "https://products.dm-static.com/x"}],
        "trackingData": {"categories": list(kategorien)},
        "price": {"price": {"current": {"value": preis}}, "tileInfos": ["1 l (2,00 € je 1 l)"]}}}
    if vorher:
        p["tileData"]["price"]["price"]["previous"] = {"value": vorher}
    return p


def test_parse_direktsaft():
    a = parse_produkt(produkt("Direktsaft Rote Bete, 1 l"))
    assert (a.name, a.preis, a.menge, a.einheit) == ("dmBio Direktsaft Rote Bete", 2.0, 1000, "ml")
    assert a.url == "https://www.dm.at/p/d/1/x" and a.gueltig_von is None
    assert kategorie_fuer(a.name).name == "Rote-Rüben-Saft"
    assert kategorie_fuer("dmBio Ingwer & Rote Bete Shot") is None


def test_tausender_leerzeichen_und_streichpreis():
    a = parse_produkt(produkt("Haferflocken Feinblatt, 1 000 g", "1,75 €", kategorien=("Flocken & Flakes",),
                              vorher="2,25 €"))
    assert (a.menge, a.einheit, a.normalpreis, a.aktion) == (1000, "g", 2.25, ["-22%"])


def test_drogerie_wird_ausgeschlossen():
    linsen = parse_produkt(produkt("Kontaktlinsenbehälter, 1 St", marke="Visiomax",
                                   kategorien=("Kontaktlinsenflüssigkeit & Augentropfen",), dan=2))
    dusche = parse_produkt(produkt("Cremedusche Naturals Mandel & Milch, 250 ml", marke="Palmolive",
                                   kategorien=("Duschgel",), dan=3))
    tofu = parse_produkt(produkt("Tofu natur, 200 g", kategorien=("Tofu",), dan=4))
    assert [t.angebot.name for t in fitness_angebote([linsen, dusche, tofu])] == ["dmBio Tofu natur"]


def test_ablauf_doppelte_treffer():
    def handler(r):
        return httpx.Response(200, json={"totalPages": 1, "products": [produkt("Tofu natur, 200 g", dan=7)]})

    c = httpx.Client(transport=httpx.MockTransport(handler))
    a = aktuelle_angebote(client=c, pause=0)
    assert len(a) == 1  # gleiches Produkt bei mehreren Suchbegriffen nur einmal


def test_tofu_fertigprodukte():
    assert kategorie_fuer("dmBio Tofu Natur").name == "Tofu"
    assert kategorie_fuer("dmBio Chili con Tofu") is None
    assert kategorie_fuer("dmBio Tofu Bratwürstchen vegan") is None
