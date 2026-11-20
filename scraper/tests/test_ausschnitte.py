from aktionen.ausschnitte import Rechteck, ausschnitt_bereich
from aktionen.flugblatt_pdf import FlugblattAngebot

SEITE = (828.0, 984.0)


def angebot(bbox, name="X"):
    return FlugblattAngebot(seite=1, name=name, preis=1.0, bbox=bbox)


def test_foto_ueber_dem_text_wird_mitgenommen():
    a = angebot((552, 837, 800, 960))                       # Text + Preis (wie Cottage Cheese)
    foto = Rechteck(560, 640, 790, 830)                     # Produktfoto direkt darüber
    r = ausschnitt_bereich(a, [foto], *SEITE)
    assert r.top <= 640 and r.bottom >= 960


def test_foto_unter_dem_text_und_hintergrund_werden_ignoriert():
    a = angebot((286, 648, 528, 727))                       # Gorgonzola
    darunter = Rechteck(419, 725, 535, 831)                 # Mozzarella-Foto darunter
    hintergrund = Rechteck(0, 0, 828, 984)
    r = ausschnitt_bereich(a, [darunter, hintergrund], *SEITE)
    assert r.bottom < 740 and r.x0 > 270


def test_obergrenze_durch_angebot_darueber():
    oben = angebot((552, 400, 800, 500), "oben")
    a = angebot((552, 700, 800, 780))
    foto = Rechteck(560, 450, 790, 690)                     # ragt in das obere Angebot hinein
    r = ausschnitt_bereich(a, [foto], *SEITE, andere=[oben, a])
    assert r.top >= 500 - 6


def test_ohne_bbox():
    assert ausschnitt_bereich(angebot(None), [], *SEITE) is None


def test_maximal_230_punkte_ueber_dem_text():
    a = angebot((552, 837, 800, 960))
    r = ausschnitt_bereich(a, [Rechteck(560, 500, 790, 830)], *SEITE)
    assert r.top == 837 - 230 - 6
