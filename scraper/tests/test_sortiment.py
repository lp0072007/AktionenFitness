"""Sortiment (Normalpreise) von Billa, MPreis und Spar: Auslesen, Ablauf, Ausfall einer Kette."""

import json
from pathlib import Path

import httpx

from aktionen import sortiment
from test_billa import produkt as billa_produkt
from test_mpreis import dokumente as mpreis_dokumente

FIXTURES = Path(__file__).parent / "fixtures"


def spar_produkte():
    return json.loads((FIXTURES / "spar_listing.json").read_text(encoding="utf-8"))["products"]


# ---------- Auslesen ----------
def test_billa_normalpreis_ohne_aktion():
    p = billa_produkt()
    p["price"] = {"regular": {"value": 249}}
    assert sortiment.billa_zeile(p) == ["alpro-skyr-natur-00123", "Alpro Skyr Natur Ungesüßt", 2.49, 400, "g", 0, None,
                                        "Kühlwaren > Milchprodukte > Joghurt"]


def test_billa_laufende_aktion_mit_normalpreis():
    z = sortiment.billa_zeile(billa_produkt())
    assert (z[2], z[6]) == (1.32, 1.99)


def test_billa_ohne_slug_weg():
    assert sortiment.billa_zeile(billa_produkt(slug=None)) is None


def test_mpreis_auch_ohne_aktion():
    # Dauerhaft gesenkt: für die Aktionen uninteressant, im Sortiment aber ein ganz normaler Preis
    z = sortiment.mpreis_zeile(mpreis_dokumente()["206620"])
    assert z is not None and z[0] == "206620" and z[2] > 0


def test_mpreis_anfrage_ohne_aktionsfilter():
    f = sortiment.mpreis_anfrage(1)["searches"][0]["filter_by"]
    assert "promotionType" not in f and "isInFlyer" not in f and "storeId:=8450" in f


def test_spar_packung_aus_grundpreis():
    normal, aktion, ohne_grundpreis = spar_produkte()
    assert sortiment.spar_zeile(normal, "Brot & Gebäck") == ["1002966", "Schoko Donuts 9er 180g 180 G", 2.99, 180, "g", 0,
                                                             None, "Brot & Gebäck"]
    assert sortiment.spar_zeile(aktion)[:7] == ["2020001085101", "SPAR Zitronen Kuchen 400 G", 2.29, 400, "g", 0, 2.99]
    assert sortiment.spar_zeile(ohne_grundpreis)[2:5] == [1.99, None, None]


def test_spar_liter():
    p = {"productNumber": "1", "name": "Milch 1 L", "price": {"currentPrice": 1.49,
         "referencePrice": {"price": 1.49, "referenceUnit": 1, "unitName": "Liter"}}}
    assert sortiment.spar_zeile(p)[3:5] == [1000, "ml"]


def test_kategorien_nummerieren():
    k, p = sortiment.kategorien_nummerieren([["1", "A", 1, None, None, 0, None, "Obst"], ["2", "B", 1, None, None, 0, None, None],
                                             ["3", "C", 1, None, None, 0, None, "Obst"], ["4", "D", 1, None, None, 0, None, "Käse"]])
    assert k == ["Obst", "Käse"] and [z[7] for z in p] == [0, None, 0, 1]


# ---------- Ablauf ----------
def test_spar_seiten_bis_total(monkeypatch):
    monkeypatch.setattr(sortiment, "SPAR_KATEGORIEN", ["brot-gebaeck"])
    seiten = []

    def handler(r):
        seiten.append(r.url.params["p"])
        ps = spar_produkte()
        return httpx.Response(200, json={"total": 40, "products": ps[:2] if r.url.params["p"] == "1" else ps[2:]})

    c = httpx.Client(transport=httpx.MockTransport(handler))
    z = sortiment.spar_laden(c, 0)
    assert seiten == ["1", "2"] and len(z) == 3


def test_spar_cloudflare_sperre_ist_fehler(monkeypatch):
    monkeypatch.setattr(sortiment, "SPAR_KATEGORIEN", ["brot-gebaeck"])
    c = httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(403, text="<title>Just a moment...</title>", headers={"content-type": "text/html"})))
    try:
        sortiment.spar_laden(c, 0)
    except RuntimeError as e:
        assert "gesperrt" in str(e)
    else:
        raise AssertionError("Sperre nicht erkannt")


def test_main_kette_faellt_aus_alter_stand_bleibt(tmp_path, monkeypatch):
    ziel = tmp_path / "sortiment.js"
    alt = {"erstellt": "x", "ketten": {"spar": {"stand": "2026-11-20", "link": "l", "produkte": [["1", "Alt", 1.0, None, None, 0, None]]}}}
    ziel.write_text(f"window.SORTIMENT = {json.dumps(alt)};\n", encoding="utf-8")

    def kaputt(*_):
        raise RuntimeError("gesperrt")

    monkeypatch.setattr(sortiment, "LADER", {"billa": lambda *_: [["b", "Topfen", 0.99, 250, "g", 0, None, "Kühlwaren"]],
                                             "mpreis": kaputt, "spar": kaputt})
    assert sortiment.main(["--ziel", str(ziel), "--pause", "0"]) == 0
    neu = sortiment.alten_stand_laden(ziel)["ketten"]
    assert neu["billa"]["produkte"][0][1] == "Topfen" and neu["billa"]["kategorien"] == ["Kühlwaren"]
    assert neu["spar"]["stand"] == "2026-11-20"  # alter Stand behalten
    assert "mpreis" not in neu                     # nie geladen -> fehlt


def test_main_ohne_spar(tmp_path, monkeypatch):
    geladen = []
    monkeypatch.setattr(sortiment, "LADER", {k: (lambda k=k: (lambda *_: geladen.append(k) or [["1", "X", 1.0, None, None, 0, None, None]]))()
                                             for k in ("billa", "mpreis", "spar")})
    sortiment.main(["--ziel", str(tmp_path / "s.js"), "--ohne-spar"])
    assert geladen == ["billa", "mpreis"]
