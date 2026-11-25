"""Echte Nährwerte: Billa-Produktdetail, MPreis-Suche, Open Food Facts (echte Antworten vom 25.11.2026, gekürzt)."""

import json
from datetime import date, timedelta
from pathlib import Path

import httpx

from aktionen import naehrwerte as N
from aktionen.fitness import fitness_angebote
from aktionen.flugblatt_pdf import FlugblattAngebot
from aktionen.models import Naehrwerte

FIX = Path(__file__).parent / "fixtures"
lade = lambda name: json.loads((FIX / name).read_text(encoding="utf-8"))


def test_billa_produktdetail():
    nw, zubereitet = N.aus_billa(lade("billa_produkt_naehrwerte.json"))  # Ja! Natürlich Butterkäse Scheiben
    assert not zubereitet
    assert (nw.kcal, nw.protein, nw.kohlenhydrate, nw.fett, nw.zucker) == (381, 25, 0.5, 31, 0.5)


def test_mpreis_aus_suche():
    d = lade("mpreis_naehrwerte.json")  # Buko mit Skyr: "&nbsp;&nbsp;- davon …" sind Unterzeilen
    nw, zubereitet = N.aus_mpreis(d["mixins"]["markantAttributes"]["data"]["nutrient"])
    assert not zubereitet
    assert (nw.kcal, nw.protein, nw.kohlenhydrate, nw.fett, nw.zucker) == (127, 10, 3.6, 9, 3.6)


def test_open_food_facts():
    nw = N.aus_off(lade("off_4002566003118.json"))  # Lidl "Joghurt" (EAN von der Produktseite)
    assert (nw.kcal, nw.protein, nw.kohlenhydrate, nw.fett) == (73, 4.6, 4.9, 3.5)
    assert N.aus_off({"status": 0}) is None


def test_ean_aus_lidl_seite():
    seite = '<script type="application/ld+json">{"@type":"Product","sku":"11328282","gtin13":["4002566003118"]}</script>'
    assert N.ean_aus_lidl_seite(seite) == "4002566003118"
    assert N.ean_aus_lidl_seite("<html></html>") is None


def test_plausibilitaet():
    assert N.plausibel(Naehrwerte(kcal=127, protein=10, kohlenhydrate=3.6, fett=9))
    assert not N.plausibel(Naehrwerte(kcal=127, protein=100, kohlenhydrate=50, fett=9))   # Summe > 100 g
    assert not N.plausibel(Naehrwerte(kcal=12, protein=10, kohlenhydrate=3.6, fett=9))    # kcal passt nicht (kJ verwechselt?)
    assert not N.plausibel(Naehrwerte(kcal=1581, protein=25, kohlenhydrate=0.5, fett=31))  # kJ statt kcal
    assert not N.plausibel(Naehrwerte(kcal=None, protein=10))
    assert N.plausibel(Naehrwerte(kcal=0, protein=0, kohlenhydrate=0, fett=0))           # Mineralwasser


def test_fitness_nutzt_echte_werte():
    a = FlugblattAngebot(seite=0, name="Billa Skyr Natur", preis=1.0, menge=500, einheit="g")
    richtwert = fitness_angebote([a])[0]
    assert richtwert.naehrwerte_quelle == "Richtwert" and richtwert.naehrwerte.protein == 11
    a.naehrwerte, a.naehrwerte_quelle = Naehrwerte(kcal=60, protein=12, kohlenhydrate=4, fett=0.2), "Etikett"
    echt = fitness_angebote([a])[0]
    assert echt.naehrwerte_quelle == "Etikett"
    assert echt.protein_pro_euro == 60.0  # 12 g × 500 g / 100 / 1 €
    assert echt.protein_pro_100kcal == 20.0


def test_abrufer_holt_einmal_und_merkt_sich(tmp_path):
    anfragen = []

    def antwort(request):
        anfragen.append(str(request.url))
        if "billa" in request.url.host:
            return httpx.Response(200, json=lade("billa_produkt_naehrwerte.json"))
        if "lidl" in request.url.host:
            return httpx.Response(200, text='{"gtin13":["4002566003118"]}')
        if "openfoodfacts" in request.url.host:
            return httpx.Response(200, json=lade("off_4002566003118.json"))
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(antwort))
    speicher = N.Speicher(tmp_path / "nw.json")
    abrufer = N.Abrufer(speicher, heute=date(2026, 11, 25), pause=0, haendler=client, off=client)
    billa = FlugblattAngebot(seite=0, name="Butterkäse", preis=2.0, produkt_id="00-256463")
    lidl = FlugblattAngebot(seite=0, name="Joghurt", preis=1.89, produkt_id="11328282", url="https://www.lidl.at/p/joghurt/p11328282")
    N.anreichern("billa", [billa], abrufer)
    N.anreichern("lidl", [lidl], abrufer)
    assert (billa.naehrwerte.protein, billa.naehrwerte_quelle) == (25, "Etikett")
    assert (lidl.naehrwerte.protein, lidl.naehrwerte_quelle, lidl.ean) == (4.6, "Open Food Facts", "4002566003118")
    assert len(anfragen) == 3  # Billa-Detail, Lidl-Seite, Open Food Facts
    speicher.speichern()

    # Zweiter Lauf: alles aus dem Speicher, keine Anfrage
    anfragen.clear()
    abrufer2 = N.Abrufer(N.Speicher(tmp_path / "nw.json"), heute=date(2026, 11, 26), pause=0, haendler=client, off=client)
    billa2 = FlugblattAngebot(seite=0, name="Butterkäse", preis=2.0, produkt_id="00-256463")
    N.anreichern("billa", [billa2], abrufer2)
    assert anfragen == [] and billa2.naehrwerte.protein == 25


def test_nichts_gefunden_wird_spaeter_neu_versucht(tmp_path):
    speicher = N.Speicher(tmp_path / "nw.json")
    speicher.setzen("lidl:1", None, None, None, date(2026, 10, 1))
    assert speicher.holen("lidl:1", date(2026, 10, 15)) is not None          # innerhalb 30 Tage: nicht neu fragen
    assert speicher.holen("lidl:1", date(2026, 10, 1) + timedelta(days=31)) is None  # danach wieder versuchen


def test_penny_und_hofer_ohne_abfrage():
    a = FlugblattAngebot(seite=0, name="Skyr", preis=1.0, produkt_id="x")
    abrufer = N.Abrufer(N.Speicher(Path("/nicht/vorhanden.json")), pause=0,
                        haendler=httpx.Client(transport=httpx.MockTransport(lambda r: (_ for _ in ()).throw(AssertionError("keine Anfrage erwartet")))))
    N.anreichern("penny", [a], abrufer)
    N.anreichern("hofer", [a], abrufer)
    assert a.naehrwerte is None


def test_zubereitete_werte_markiert():
    # Ben's Original 10 Minuten Reis (25.11.2026): Billa und MPreis nennen nur "zubereitet" (gekocht, 155 kcal)
    zubereitet = {"additionalInformation": [{"foodInformation": {"nutritionInfos": [{"label": "100 Gramm",
        "preparationGrade": "Zubereitet", "relationValue": 100.0, "nutrients": [
            {"name": "Energie", "value": 155, "unit": {"symbol": "kcal"}}, {"name": "Eiweiß", "value": 3.3, "unit": {"symbol": "g"}},
            {"name": "Kohlenhydrate", "value": 33, "unit": {"symbol": "g"}}, {"name": "Fett", "value": 0.5, "unit": {"symbol": "g"}}]}]}}]}
    nw, ist_zubereitet = N.aus_billa(zubereitet)
    assert ist_zubereitet and nw.kcal == 155
    mpreis = {"nutrientHeader": {"1": {"energyKcal": 155, "nutrientBasisQuantity": 100, "preparationState": "PreparedNormed",
              "nutrientContent": {"0": {"nutrientType": "Eiweiß", "quantityContained": 3.3}}},
              "2": {"energyKcal": 355, "nutrientBasisQuantity": 100, "preparationState": "UnpreparedNormed",
              "nutrientContent": {"0": {"nutrientType": "Eiweiß", "quantityContained": 7.5}}}}}
    nw, ist_zubereitet = N.aus_mpreis(mpreis)
    assert (nw.kcal, ist_zubereitet) == (355, False)  # unzubereitet hat Vorrang

    # Reis nur zubereitet -> Fitness nimmt den Richtwert; TK-Gemüse zubereitet -> echte Werte
    reis = FlugblattAngebot(seite=0, name="Bens Original Langkorn-Reis", preis=2.0, menge=500, einheit="g",
                            naehrwerte=Naehrwerte(kcal=155, protein=3.3, kohlenhydrate=33, fett=0.5),
                            naehrwerte_quelle="Etikett (zubereitet)")
    t = fitness_angebote([reis])[0]
    assert (t.naehrwerte_quelle, t.naehrwerte.kcal) == ("Richtwert", 350)
    brokkoli = FlugblattAngebot(seite=0, name="Iglo Brokkoli", preis=2.0, menge=450, einheit="g",
                                naehrwerte=Naehrwerte(kcal=34, protein=3.5, kohlenhydrate=2.5, fett=0.6),
                                naehrwerte_quelle="Etikett (zubereitet)")
    t = fitness_angebote([brokkoli])[0]
    assert (t.naehrwerte_quelle, t.naehrwerte.kcal) == ("Etikett (zubereitet)", 34)


def test_alte_speicher_version_wird_neu_geholt(tmp_path):
    speicher = N.Speicher(tmp_path / "nw.json")
    speicher.daten["billa:1"] = {"nw": {"kcal": 155, "protein": 3.3}, "quelle": "Etikett", "datum": "2026-11-25"}  # ohne "v"
    assert speicher.holen("billa:1", date(2026, 11, 26)) is None
