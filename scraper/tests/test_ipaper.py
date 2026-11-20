import json
from pathlib import Path

from aktionen.stores.ipaper import produkt_links

FIXTURES = Path(__file__).parent / "fixtures"


def test_produkt_links_aus_enrichments():
    data = json.loads((FIXTURES / "spar_ipaper_enrichments.json").read_text(encoding="utf-8"))
    links = produkt_links(data)
    nummern = [l.produkt_nr for l in links]
    # Produktlinks inkl. Menü-Einträge, ohne Kampagnen-, Such-, Rezept- und Popup-Links
    assert nummern == ["2020004779311", "2020003753749", "323345", "2020002665784", "2020004331199", "2020006073363"]

    erster = links[0]
    assert erster.seite == 2  # pageIndex 1
    assert erster.position == (0.352, 0.345, 0.623, 0.306)

    gluehwein = next(l for l in links if l.produkt_nr == "2020002665784")
    assert gluehwein.name == "Dockner Glühwein rot"
    assert gluehwein.position is None
