"""Sparsamer Lauf (python -m aktionen.export --alt …): nur Geändertes neu laden, Ausfälle mit altem Stand überbrücken.

Die Händler werden hier nachgebildet (kein Netz): aktuelles_flugblatt, region_exportieren, kette_exportieren.
"""

import json
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from aktionen import export


def flugblatt(name):
    return SimpleNamespace(flipbook=SimpleNamespace(name=name))


def region(name_flugblatt, n=3):
    return {"region": "wien", "name": "Wien", "flugblatt": name_flugblatt, "anzahl_angebote": n,
            "angebote": [{"id": f"spar-{i}", "kette": "spar", "name": f"Skyr {i}", "preis": 1.0} for i in range(n)],
            "alle": [{"id": f"spar-{i}", "kette": "spar", "name": f"Skyr {i}", "preis": 1.0} for i in range(n)]}


def kette(k, n=2):
    eintraege = [{"id": f"{k}-{i}", "kette": k, "name": f"Topfen {i}", "preis": 0.99} for i in range(n)]
    return {"anzahl_angebote": n, "angebote": eintraege, "alle": [] if k == "dm" else eintraege}


@pytest.fixture
def umgebung(tmp_path, monkeypatch):
    """Nachgebildete Händler; zählt, was wirklich geladen wurde."""
    aufrufe = {"region": 0, "ketten": []}
    zustand = {"flugblatt": "Wien KW 48", "fehler": set(), "leer": set()}
    monkeypatch.setattr(export, "aktuelles_flugblatt", lambda r: flugblatt(zustand["flugblatt"]))

    def region_exportieren(r, pdf, bilder, alle_bilder=True, fb=None):
        aufrufe["region"] += 1
        return region(fb.flipbook.name)

    def kette_exportieren(k, bilder):
        aufrufe["ketten"].append(k)
        if k in zustand["fehler"]:
            raise RuntimeError("429 Too Many Requests")
        return kette(k, 0 if k in zustand["leer"] else 2)

    monkeypatch.setattr(export, "region_exportieren", region_exportieren)
    monkeypatch.setattr(export, "kette_exportieren", kette_exportieren)
    ziel = tmp_path / "angebote.json"

    def lauf(*extra):
        aufrufe["region"], aufrufe["ketten"] = 0, []
        export.main(["--region", "wien", "--ziel", str(ziel), "--ohne-bilder", "--ohne-verlauf", *extra])
        return json.loads(ziel.read_text(encoding="utf-8"))

    return SimpleNamespace(lauf=lauf, aufrufe=aufrufe, zustand=zustand, ordner=tmp_path, ziel=ziel)


def test_erster_lauf_laedt_alles(umgebung):
    d = umgebung.lauf("--sparsam")  # noch kein alter Stand -> alles laden
    assert umgebung.aufrufe["region"] == 1
    assert set(umgebung.aufrufe["ketten"]) == set(export.WEITERE_KETTEN)
    assert d["regionen"][0]["stand"] == d["erstellt"] and d["billa"]["stand"] == d["erstellt"]


def test_gleiches_flugblatt_wird_uebernommen(umgebung):
    umgebung.lauf()
    d = umgebung.lauf("--sparsam")
    assert umgebung.aufrufe["region"] == 0  # kein PDF
    assert d["regionen"][0]["uebernommen"] and d["regionen"][0]["flugblatt"] == "Wien KW 48"
    aktionen = (umgebung.ordner / "aktionen.js").read_text(encoding="utf-8")
    assert '"wien"' in aktionen and "Skyr 0" in aktionen  # alle Aktionen der Region bleiben für den Abgleich


def test_neues_flugblatt_wird_geladen(umgebung):
    umgebung.lauf()
    umgebung.zustand["flugblatt"] = "Wien KW 49"
    d = umgebung.lauf("--sparsam")
    assert umgebung.aufrufe["region"] == 1
    assert d["regionen"][0]["flugblatt"] == "Wien KW 49" and not d["regionen"][0].get("uebernommen")


def test_dm_nur_einmal_pro_woche(umgebung):
    umgebung.lauf()
    umgebung.lauf("--sparsam")
    assert "dm" not in umgebung.aufrufe["ketten"] and "billa" in umgebung.aufrufe["ketten"]
    # Stand künstlich 8 Tage alt machen -> dm wird wieder geladen
    d = json.loads(umgebung.ziel.read_text(encoding="utf-8"))
    d["dm"]["stand"] = (datetime.now() - timedelta(days=8)).isoformat(timespec="minutes")
    umgebung.ziel.write_text(json.dumps(d), encoding="utf-8")
    umgebung.lauf("--sparsam")
    assert "dm" in umgebung.aufrufe["ketten"]


def test_ausfall_behaelt_letzten_stand(umgebung, capsys):
    umgebung.lauf()
    umgebung.zustand["fehler"].add("penny")
    umgebung.zustand["leer"].add("lidl")
    d = umgebung.lauf("--sparsam")
    assert d["penny"]["uebernommen"] and len(d["penny"]["angebote"]) == 2
    assert d["lidl"]["uebernommen"] and len(d["lidl"]["angebote"]) == 2  # 0 Angebote gilt als Ausfall
    fehler = capsys.readouterr().err
    assert "Penny: 429" in fehler and "Lidl: 0 Angebote" in fehler
    aktionen = (umgebung.ordner / "aktionen.js").read_text(encoding="utf-8")
    assert "penny-0" in aktionen  # auch im Einkaufslisten-Abgleich weiter vorhanden


def test_ohne_sparsam_wie_bisher(umgebung):
    umgebung.lauf()
    umgebung.zustand["fehler"].add("penny")
    d = umgebung.lauf()  # ohne --sparsam: alles neu, Ausfall bleibt leer
    assert umgebung.aufrufe["region"] == 1 and d["penny"] is None


def test_warnung_in_github_actions(monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    export.warnung("Billa: 0 Angebote")
    assert "::warning::Billa: 0 Angebote" in capsys.readouterr().out
