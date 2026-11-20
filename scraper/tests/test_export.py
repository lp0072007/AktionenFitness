import json
from pathlib import Path

from aktionen.export import treffer_als_dict
from aktionen.fitness import fitness_angebote
from aktionen.flugblatt_pdf import analysiere_seite

FIXTURES = Path(__file__).parent / "fixtures"


def test_treffer_als_dict_fuer_website():
    w = json.loads((FIXTURES / "spar_pdf_noe_kw47_s14.json").read_text(encoding="utf-8"))["woerter"]
    (t,) = fitness_angebote(analysiere_seite(w, 14))
    d = treffer_als_dict(t, "spar", "niederoesterreich", 0)
    assert d["id"] == "spar-niederoesterreich-14-0"
    assert d["name"].startswith("NÖM PRO Cottage Cheese")
    assert (d["preis"], d["normalpreis"], d["ab_menge"], d["gramm"]) == (1.19, 1.99, 2, 215)
    assert d["kategorie"] == "Cottage Cheese" and d["gruppe"] == "Protein"
    assert d["protein_pro_euro"] == 19.0
    json.dumps(d)  # muss serialisierbar sein
