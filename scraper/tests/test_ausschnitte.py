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


def _mit_name(name, name_bbox, preis_bbox=None):
    a = FlugblattAngebot(seite=1, name=name, preis=1.0, bbox=name_bbox, name_bbox=name_bbox, preis_bbox=preis_bbox)
    return a


def test_foto_neben_dem_text_wird_gefunden():
    # Text rechts, Foto links daneben auf gleicher Höhe (typisch bei Spar)
    a = _mit_name("Olivenöl", (300, 400, 420, 420), (300, 430, 380, 470))
    foto = Rechteck(150, 360, 290, 480)
    r = ausschnitt_bereich(a, [foto], 800, 1000, [a])
    assert r.x0 <= 150 and r.x1 >= 420


def test_fremder_name_bleibt_draussen_und_fremdes_foto_wird_nicht_genommen():
    a = _mit_name("Wodka", (300, 400, 400, 415))
    b = _mit_name("Mineralwasser", (430, 400, 540, 415))
    foto_b = Rechteck(420, 300, 560, 395)  # über dem Nachbarn
    r = ausschnitt_bereich(a, [foto_b], 800, 1000, [a, b])
    assert r.x1 < 430 + 2  # Name des Nachbarn nicht im Ausschnitt


def test_weit_entfernte_beschreibung_zaehlt_nicht():
    # bbox reicht durch falsche Zuordnung bis weit nach unten; Anker ist der Name
    a = FlugblattAngebot(seite=1, name="Traktor", preis=1.0, bbox=(100, 300, 300, 600),
                         name_bbox=(100, 300, 300, 315), preis_bbox=(220, 250, 300, 290))
    r = ausschnitt_bereich(a, [], 800, 1000, [a])
    assert r.bottom < 400
