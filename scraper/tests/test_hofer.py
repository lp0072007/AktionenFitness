from datetime import date
from pathlib import Path

import httpx
import pytest

from aktionen.stores.hofer import HoferBlockiert, aktuelle_angebote, angebote_aus_html, parse_kachel, tag_seiten

HTML = (Path(__file__).parent / "fixtures" / "hofer_kacheln.html").read_text(encoding="utf-8")


def test_tag_seiten():
    assert tag_seiten(HTML) == ["2026-11-19", "2026-11-20"]


def test_echte_kacheln():
    a = {x.name: x for x in angebote_aus_html(HTML, date(2026, 11, 20))}
    kokos = a["BIO Kokosnussmilch"]
    assert (kokos.preis, kokos.menge, kokos.einheit) == (1.59, 400, "ml")
    assert kokos.gueltig_von == date(2026, 11, 20)
    assert kokos.url.startswith("https://www.hofer.at/produkt/")
    assert kokos.bild_url.startswith("https://dm.emea.cms.aldi.cx/")
    ananas = a["BIO Ananas Stücke"]
    assert (ananas.menge, ananas.einheit) == (200, "g")            # "0,2 KG/ATG per Stück"
    baum = a["HOME CREATION Weihnachtsbaum Animation"]
    assert baum.preis == 9.99 and baum.menge is None and "Tiefpreisaktion" in baum.aktion


def test_rabatt_und_menge_aus_vergleichspreis():
    kachel = '''<div class="product-tile__brandname"><p>ZURÜCK ZUM URSPRUNG</p></div>
      <div class="product-tile__name"><p>Bio-Magertopfen</p></div>
      <div class="product-tile__unit-of-measurement"><p>per Packung</p></div>
      <div class="product-tile__comparison-price"><p>(€ 3,96/1 kg)</p></div>
      <div class="base-price base-price--product-tile"><span class="base-price__regular"><span>€ 1,29</span></span>
      <span class="base-price__discounted"><span>€ 0,99</span></span></div></a>'''
    a = parse_kachel("000000000000123", kachel)
    assert (a.preis, a.normalpreis, a.produkt_id) == (0.99, 1.29, "123")
    assert a.aktion[0] == "-23%"
    assert (a.menge, a.einheit) == (250, "g")                      # 0,99 € / 3,96 €/kg


def test_kilo_ware():
    kachel = '''<div class="product-tile__name"><p>Hühnerbrustfilet</p></div>
      <div class="product-tile__unit-of-measurement"><p>per kg</p></div>
      <div class="base-price base-price--product-tile"><span class="base-price__regular"><span>€ 9,99</span></span></div>'''
    a = parse_kachel("1", kachel)
    assert a.pro_kg and a.menge is None and a.preis == 9.99


def test_gesperrt():
    c = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(403, text="<HTML>Access Denied</HTML>")))
    with pytest.raises(HoferBlockiert):
        aktuelle_angebote(client=c, pause=0)


def test_ablauf_mit_tagesseiten():
    def handler(r):
        if r.url.path == "/angebote":
            return httpx.Response(200, text=HTML)
        return httpx.Response(200, text=HTML)  # jede Tagesseite liefert dieselben Kacheln
    c = httpx.Client(transport=httpx.MockTransport(handler))
    a = aktuelle_angebote(heute=date(2026, 11, 20), client=c, pause=0)
    assert len(a) == 3                                                 # doppelte Produkte nur einmal
    assert {x.gueltig_von for x in a} == {date(2026, 11, 19)}          # erster Starttag zählt
