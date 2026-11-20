import io

from aktionen.fortschritt import Fortschritt, Gesamt


def test_fortschritt_ohne_konsole_nur_abschlusszeile():
    aus = io.StringIO()
    f = Fortschritt("Seiten lesen", 25, ausgabe=aus)
    for i in range(25):
        f.weiter()
    assert aus.getvalue() == ""                 # keine Zwischenstände in Dateien/Tests
    f.fertig("193 Angebote")
    zeile = aus.getvalue()
    assert "100 %" in zeile and "25/25" in zeile and "193 Angebote" in zeile


def test_megabyte_anzeige():
    aus = io.StringIO()
    f = Fortschritt("PDF laden", 22_100_000, einheit="MB", ausgabe=aus)
    f.setze(22_100_000)
    f.fertig()
    assert "22,1/22,1 MB" in aus.getvalue()


def test_gesamt_kopfzeilen():
    aus = io.StringIO()
    g = Gesamt([2.5, 1, 1], ausgabe=aus)
    g.schritt("Spar Wien")
    g.schritt("Lidl")
    g.ende()
    text = aus.getvalue()
    assert "[1/3] Spar Wien" in text and "[2/3] Lidl" in text and "noch ~" in text and "Fertig in" in text
