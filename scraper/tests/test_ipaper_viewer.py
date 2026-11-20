from datetime import date
from pathlib import Path

import pytest

from aktionen.stores.ipaper import parse_viewer_html, static_settings

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def flipbook():
    return parse_viewer_html((FIXTURES / "spar_ipaper_viewer.html").read_text(encoding="utf-8"))


def test_grunddaten(flipbook):
    assert flipbook.name == "261112-1-Online-Flugblatt Niederoesterreich KW 47"
    # Titel ist genauer als validFrom der Spar-API (17.11.): Aktionen starten am Donnerstag
    assert flipbook.gueltig == (date(2026, 11, 19), date(2026, 12, 2))


def test_seitentexte(flipbook):
    assert len(flipbook.seitentexte) == 3
    cottage = flipbook.seitentexte[2]
    assert "NÖM PRO Cottage Cheese" in cottage
    assert "ab 2 Becher je 1 19" in cottage  # Preis "1,19" ist im Text als "1 19" zerlegt


def test_urls_mit_token(flipbook):
    assert flipbook.enrichment_urls[0].endswith("expires=1795248117")
    assert "&token_ignore_params=true" in flipbook.enrichment_urls[0]  # & korrekt dekodiert
    url = flipbook.seitenbild_url(13, zoom=True)
    assert url.startswith("https://cdn.ipaper.io/iPaper/Papers/fe9329db-0a2c-4b9d-8659-3b30f6e27bf7/Pages/13/Zoom.jpg?token=")


def test_kein_ipaper_html():
    with pytest.raises(ValueError):
        static_settings("<html></html>")
