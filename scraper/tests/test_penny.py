from datetime import date

import httpx

from aktionen.fitness import kategorie_fuer
from aktionen.stores.penny import aktuelle_angebote, parse_produkt


def produkt(**kw):
    # Aufbau wie in der echten Antwort von penny.at/api/product-discovery (20.11.2026), gekürzt
    p = {
        "sku": "78-100272", "name": "Cottage Cheese", "brand": {"name": "Nöm"}, "amount": "200",
        "volumeLabelShort": "g", "weightArticle": False, "slug": "noem-cottage-cheese-123",
        "images": ["https://images.cdn.europe-west1.gcp.commercetools.com/x.jpg"],
        "parentCategories": [[{"name": "Kühlwaren"}, {"name": "Milchprodukte"}]],
        "price": {"regular": {"value": 100, "tags": ["pt-aktion"]}, "crossed": 199, "discountPercentage": -50,
                  "validityStart": "2026-11-19", "validityEnd": "2026-11-25"},
    }
    p.update(kw)
    return p


def test_streichpreis_und_gueltigkeit():
    a = parse_produkt(produkt())
    assert (a.name, a.preis, a.normalpreis, a.menge, a.einheit) == ("Nöm Cottage Cheese", 1.0, 1.99, 200, "g")
    assert a.aktion == ["-50%"]
    assert (a.gueltig_von, a.gueltig_bis) == (date(2026, 11, 19), date(2026, 11, 25))
    assert a.url == "https://www.penny.at/produkte/noem-cottage-cheese-123"


def test_mengenaktion_liter_und_kiloware():
    milch = parse_produkt(produkt(name="Formil Haltbare Vollmilch*", amount="1", volumeLabelShort="liter",
                                  price={"regular": {"value": 89, "promotionQuantity": 12, "promotionType": "FROM",
                                                     "promotionText": "ab 12 Packungen"},
                                         "validityStart": "2026-11-19", "validityEnd": "2026-11-25"}))
    assert (milch.preis, milch.ab_menge, milch.menge, milch.einheit) == (0.89, 12, 1000, "ml")
    assert "*" not in milch.name and "ab 12 Packungen" in milch.beschreibung
    putenbrust = parse_produkt(produkt(name="Putenbrust", brand={"name": "Delikatessa"}, amount="1",
                                       volumeLabelShort="kg", weightArticle=True))
    assert putenbrust.pro_kg and putenbrust.menge is None


def test_non_food_wird_ignoriert():
    assert parse_produkt(produkt(parentCategories=[[{"name": "Alle Angebote"}], [{"name": "Haushalt"}]])) is None


def test_seiten_und_sorten_zusammenfassen():
    seiten = {
        0: [produkt(sku="1", name="Teigwaren"), produkt(sku="2", name="Teigwaren"), produkt(sku="3", name="Skyr")],
        1: [produkt(sku="4", name="Alt", price={"regular": {"value": 100}, "validityStart": "2026-11-01",
                                                  "validityEnd": "2026-11-05"})],
    }

    def handler(r):
        s = int(r.url.params["page"])
        return httpx.Response(200, json={"total": 101, "results": seiten.get(s, [])})

    c = httpx.Client(transport=httpx.MockTransport(handler))
    a = aktuelle_angebote(heute=date(2026, 11, 20), client=c, pause=0)
    assert sorted(x.name for x in a) == ["Nöm Skyr", "Nöm Teigwaren"]   # Sorte doppelt, "Alt" abgelaufen


def test_kategorien_penny_namen():
    assert kategorie_fuer("Federike Hühner-Innenfilet").name == "Hühnerbrust"
    assert kategorie_fuer("Federike Hendl-Filet").name == "Hühnerbrust"
    assert kategorie_fuer("Salzburg Milch Premium Käse-Selektion") is None
    assert kategorie_fuer("Iglo Polardorsch Knusperhülle") is None
    assert kategorie_fuer("Bens Original Express Reis") is None


def test_kategoriepfad_schliesst_fertiggerichte_aus():
    from aktionen.fitness import fitness_angebote

    fertig = parse_produkt(produkt(name="Tagliatelle Wildlachs", brand={"name": "Frosta"}, parentCategories=[
        [{"name": "Tiefkühl"}, {"name": "Tiefkühlgerichte"}, {"name": "Reis & Pasta"}]]))
    lachs = parse_produkt(produkt(name="Lachsfilet", brand={"name": "Berida"}, parentCategories=[
        [{"name": "Tiefkühl"}, {"name": "Fleisch & Fisch"}, {"name": "Fisch"}]]))
    assert fertig.kategorie_pfad == "Tiefkühl > Tiefkühlgerichte > Reis & Pasta"
    assert [t.angebot.name for t in fitness_angebote([fertig, lachs])] == ["Berida Lachsfilet"]
