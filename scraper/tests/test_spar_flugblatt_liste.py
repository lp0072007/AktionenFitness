"""Tests für die Spar-Flugblatt-Liste (/api/ipaper/leaflets)."""

import json
from datetime import date
from pathlib import Path

from aktionen.stores.spar import SparStore, parse_flugblatt

FIXTURES = Path(__file__).parent / "fixtures"


def lade(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_flugblatt_liste():
    fb = SparStore().flugblaetter(lade("spar_flugblaetter.json"))
    assert len(fb) == 5
    noe = fb[0]
    assert noe.id == "niederoesterreich/niederoesterreich_kw47"
    assert noe.region == "niederoesterreich"
    assert noe.woche == "KW 47"
    assert noe.ist_regional


def test_datum_in_oesterreichischer_zeit():
    noe = SparStore().flugblaetter(lade("spar_flugblaetter.json"))[0]
    # validFrom 2026-11-16T23:00Z = 17.11. 00:00 in Wien
    assert noe.gueltig_ab == date(2026, 11, 17)
    # validTo 2026-12-02T23:00Z = 03.12. 00:00 in Wien, exklusiv -> letzter Tag 02.12.
    assert noe.gueltig_bis == date(2026, 12, 2)
    assert noe.gueltig_am(date(2026, 11, 20))
    assert not noe.gueltig_am(date(2026, 12, 3))


def test_ueberregionale_folder():
    fb = SparStore().flugblaetter(lade("spar_flugblaetter.json"))
    sonder = [f for f in fb if not f.ist_regional]
    assert {f.gruppe for f in sonder} == {"sonderfolder", "weinwelt"}


def test_einzelnes_flugblatt_mit_viewer_url():
    f = parse_flugblatt(lade("spar_flugblatt_noe.json"))
    assert f.viewer_url == "https://flugblatt.interspar.at/niederoesterreich/niederoesterreich_kw47/"
