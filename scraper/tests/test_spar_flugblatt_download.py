from datetime import date
from pathlib import Path

import httpx
import pytest

from aktionen.spar_flugblatt import aktuelles_flugblatt, kandidaten_kw, pdf_herunterladen, pdf_url, viewer_url

FIXTURES = Path(__file__).parent / "fixtures"
VIEWER_HTML = (FIXTURES / "spar_ipaper_viewer.html").read_text(encoding="utf-8")


def test_viewer_url():
    assert viewer_url("niederoesterreich", 47) == "https://flugblatt.interspar.at/niederoesterreich/niederoesterreich_kw47/"
    assert viewer_url("burgenland_sued", 47) == "https://flugblatt.interspar.at/burgenland/burgenland_sued_kw47/"


def test_kandidaten_kw():
    assert kandidaten_kw(date(2026, 11, 20)) == [47, 46, 45, 44]
    assert kandidaten_kw(date(2027, 1, 5), zurueck=1) == [1, 53]  # Jahreswechsel


def fake_client():
    """Simuliert flugblatt.interspar.at (nur KW 47 existiert) und den CDN."""
    def handler(req: httpx.Request) -> httpx.Response:
        url = str(req.url)
        if req.method == "GET" and url.endswith("niederoesterreich_kw47/"):
            return httpx.Response(200, text=VIEWER_HTML)
        if req.method == "POST" and url.endswith("niederoesterreich_kw47/GetPDF.ashx"):
            assert req.content == b"pageNumbers="
            return httpx.Response(302, headers={"location": "https://cdn.ipaper.io/x/Download.pdf?token=abc"})
        if req.method == "GET" and url.startswith("https://cdn.ipaper.io/x/Download.pdf"):
            return httpx.Response(200, content=b"%PDF-1.7 test")
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_aktuelles_flugblatt_findet_vorwoche():
    fb = aktuelles_flugblatt("niederoesterreich", heute=date(2026, 11, 27), client=fake_client())  # KW 48
    assert fb.kw == 47
    assert fb.flipbook.gueltig == (date(2026, 11, 19), date(2026, 12, 2))


def test_kein_flugblatt():
    with pytest.raises(LookupError):
        aktuelles_flugblatt("wien", heute=date(2026, 11, 20), client=fake_client())


def test_pdf_url_und_download(tmp_path):
    c = fake_client()
    assert pdf_url(viewer_url("niederoesterreich", 47), c).startswith("https://cdn.ipaper.io/")
    fb = aktuelles_flugblatt("niederoesterreich", heute=date(2026, 11, 20), client=c)
    pfad = pdf_herunterladen(fb, tmp_path, c)
    assert pfad.name == "spar_niederoesterreich_kw47.pdf"
    assert pfad.read_bytes().startswith(b"%PDF")
