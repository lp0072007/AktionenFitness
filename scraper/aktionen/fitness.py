"""Fitness-Auswertung: Welche Angebote lohnen sich für Sportler?

1. Angebot einer Kategorie zuordnen (Stichwörter im Namen). Hat es keine Kategorie, ist es nicht fitnessrelevant.
2. Nährwerte aus der Kategorie (typische Werte pro 100 g, gerundet; echte Produkte weichen ab)
3. Kennzahlen: g Protein pro €, kcal pro €, g Protein pro 100 kcal (Eiweißdichte)

Die Werte sind Richtwerte für den Vergleich und keine Etikettenangaben.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .flugblatt_pdf import FlugblattAngebot
from .models import Naehrwerte


@dataclass(frozen=True)
class Kategorie:
    name: str
    gruppe: str                  # "Protein", "Kohlenhydrate", "Fette", "Extras"
    stichwoerter: tuple[str, ...]  # Regex, auf den kleingeschriebenen Produktnamen
    kcal: float
    protein: float
    kohlenhydrate: float
    fett: float
    gramm_pro_stueck: float | None = None  # für Stückware (Eier)
    ausschluss: tuple[str, ...] = ()
    mit_beschreibung: bool = False  # Stichwörter auch in der Beschreibung suchen (z. B. "in Sonnenblumenöl")

    @property
    def naehrwerte(self) -> Naehrwerte:
        return Naehrwerte(kcal=self.kcal, protein=self.protein, kohlenhydrate=self.kohlenhydrate, fett=self.fett)


# Reihenfolge wichtig: spezifische Kategorien zuerst. Werte pro 100 g (roh bzw. wie verkauft).
# Verarbeitetes Obst/Gemüse (Saft, Marmelade, Chips …) zählt nicht als Obst/Gemüse
_VERARBEITET_OG = (r"saft", r"sirup", r"nektar", r"marmelade", r"konfitüre", r"gummi", r"schnüre",
                                              r"\btee\b", r"essig", r"chips", r"ketchup", r"sauce", r"soße", r"sugo", r"mark\b",
                                              r"pesto", r"gewürz", r"cubes", r"schnaps", r"brand\b", r"cremissimo",
                                              r"sorbet", r"eistee", r"limo", r"lattella", r"molke", r"pfanne", r"rahm",
                                              r"creme", r"laibchen", r"würze", r"fond\b", r"brühe", r"schoko", r"senf",
                                              r"\bsaurer\b", r"\bmix\b.*nüsse", r"gelee", r"getrocknet", r"jogurt|joghurt",
                                              r"kefir", r"müsli", r"wein", r"cider", r"secco", r"zeronic", r"granola", r"shots?\b",
                   r"rulade", r"trü frü", r"nucao", r"krapfen", r"pür+ee", r"glück\b", r"iced tea", r"frucade", r"crème")

KATEGORIEN: tuple[Kategorie, ...] = (
    Kategorie("Proteinpulver", "Protein", (r"\bwhey\b", r"protein[- ]?pulver", r"eiweiß[- ]?pulver", r"proteinshake[- ]?pulver",
                                           r"\bisolat\b", r"casein"), 380, 75, 8, 6, ausschluss=(r"riegel", r"bar\b")),
    Kategorie("Magertopfen", "Protein", (r"magertopfen", r"topfen.*mager"), 67, 12, 4, 0.2),
    Kategorie("Skyr", "Protein", (r"\bskyr\b",), 63, 11, 4, 0.2, ausschluss=(r"drink", r"alternative")),
    Kategorie("Cottage Cheese", "Protein", (r"cottage",), 95, 10.5, 3, 4.5),
    Kategorie("Hühnerbrust", "Protein", (r"hendl-?filet", r"hühner-?brust", r"hähnchen-?brust", r"hühner-?(innen)?filet",
                                          r"maishendl-?filet", r"hendl-?brust", r"hendl-?innenfilet"), 110, 23, 0, 1.5,
              ausschluss=(r"faschiert", r"nugget", r"paniert", r"cordon", r"knusper")),
    Kategorie("Putenbrust", "Protein", (r"putenbrust", r"putenschnitz", r"puteninnenfilet", r"putenfilet",
                                        r"putengeschnetzelt"), 105, 24, 0, 1,
              ausschluss=(r"faschiert", r"wurst", r"schinken", r"aufschnitt")),
    Kategorie("Geflügel-Faschiertes", "Protein", (r"(puten|hendl|geflügel)-?faschiert",), 150, 19, 0, 8),
    Kategorie("Rind mager", "Protein", (r"rindsschnitzel", r"rinderhüfte", r"rindsfilet", r"rinderfilet",
                                        r"tafelspitz", r"beiried"), 120, 22, 0, 3.5),
    Kategorie("Rinder-Faschiertes", "Protein", (r"rind(er|s)?-?faschiert",), 220, 20, 0, 15),
    Kategorie("Thunfisch in Öl", "Protein", (r"thunfisch.*\bin\b[^.·]*öl",), 200, 24, 0, 11,
              ausschluss=(r"salat", r"pizza", r"creme", r"aufstrich"), mit_beschreibung=True),
    Kategorie("Thunfisch", "Protein", (r"thunfisch",), 110, 24, 0, 1,
              ausschluss=(r"salat", r"pizza", r"creme", r"aufstrich")),
    Kategorie("Garnelen", "Protein", (r"garnele", r"shrimp", r"crevette"), 80, 18, 0, 1),
    Kategorie("Lachs", "Protein", (r"(?<!see)lachs(?!forelle)", r"lachsforelle"), 200, 20, 0, 13,
              ausschluss=(r"geräuchert", r"räucher", r"weißburgunder", r"lammlachs")),
    Kategorie("Magerer Fisch", "Protein", (r"dorsch", r"kabeljau", r"seelachs", r"pangasius", r"zander",
                                           r"goldbrasse", r"forelle", r"saibling", r"alaska"), 95, 19, 0, 2,
              ausschluss=(r"stäbchen", r"paniert", r"backfisch", r"knusper")),
    Kategorie("Eier", "Protein", (r"\beier\b",), 140, 12.5, 0.7, 9.5, gramm_pro_stueck=60,
              ausschluss=(r"likör", r"nudel", r"teigwaren", r"eiergold", r"schoko")),
    Kategorie("Eiweißbrot", "Protein", (r"eiweißbrot", r"proteinbrot", r"eiweiß-?brot"), 260, 21, 9, 13),
    Kategorie("Tofu", "Protein", (r"\btofu\b",), 130, 13, 2, 7.5),
    Kategorie("Linsen & Bohnen", "Protein", (r"linsen", r"kichererbsen", r"kidneybohnen", r"weiße bohnen"),
              330, 23, 50, 1.5, ausschluss=(r"chips", r"suppe")),
    Kategorie("Haferflocken", "Kohlenhydrate", (r"haferflocken", r"porridge"), 370, 13.5, 59, 7,
              ausschluss=(r"riegel", r"keks", r"cookie")),
    Kategorie("Reis", "Kohlenhydrate", (r"\breis\b", r"basmati", r"jasmin(reis)?\b", r"-reis\b"), 350, 7.5, 78, 0.6,
              ausschluss=(r"reiswaffel", r"milchreis", r"reisdrink", r"pfanne", r"express", r"mikrowelle")),
    Kategorie("Nudeln", "Kohlenhydrate", (r"\bpasta\b", r"teigwaren", r"spaghetti", r"penne", r"fusilli",
                                          r"nudeln"), 355, 12.5, 71, 1.5,
              ausschluss=(r"noodles", r"fertig", r"suppe", r"instant", r"croissant", r"crepe", r"bolognese",
                          r"carbonara", r"sauce", r"soße", r"pesto", r"salat", r"mehlspeis", r"nussnudel")),
    Kategorie("Erdäpfel", "Kohlenhydrate", (r"erdäpfel", r"kartoffel"), 75, 2, 16, 0.1,
              ausschluss=(r"chips", r"püree", r"rösti", r"pommes", r"salat", r"knödel")),
    Kategorie("Rote-Rüben-Saft", "Kohlenhydrate", (r"rote[- ]?(bete|beete|rüben?)[- ]?(direkt)?saft", r"randensaft",
                                                   r"(direkt)?saft rote[- ]?(bete|beete|rüben?)"), 40, 1, 8.5, 0,
              ausschluss=(r"shot", r"ingwer")),
    Kategorie("Bananen", "Kohlenhydrate", (r"banane",), 90, 1.1, 20, 0.3, ausschluss=(r"chips", r"nikolo", r"schoko",
              r"actimel", r"jo(g)?hurt", r"drink", r"saft", r"smoothie", r"brei", r"bebivita", r"quetsch", r"müsli")),
    Kategorie("Milch", "Protein", (r"\bh?-?milch\b", r"vollmilch", r"magermilch", r"\bh-milch"), 50, 3.4, 4.8, 1.5,
              ausschluss=(r"schoko", r"kakao", r"cacao", r"reis", r"hafer", r"pudding", r"milchreis", r"käse",
                          r"scheiben", r"selektion", r"butter", r"joghurt", r"topfen", r"rahm", r"schlag",
                          r"kuvertüre", r"glasur", r"brötle")),
    Kategorie("Nüsse", "Fette", (r"nusskern", r"mandeln", r"walnüsse", r"cashew", r"haselnüsse"), 620, 18, 12, 54,
              ausschluss=(r"schoko", r"nougat", r"krokant", r"jo(g)?hurt", r"quark", r"topfen", r"skyr", r"müsli")),
    Kategorie("Erdnussbutter", "Fette", (r"erdnussbutter", r"erdnussmus", r"peanut butter"), 600, 25, 14, 50),
    Kategorie("Olivenöl", "Fette", (r"olivenöl",), 820, 0, 0, 91,
              ausschluss=(r"in[^,·]*olivenöl", r"filet", r"makrele", r"thunfisch", r"sardine", r"oliven")),  # "Makrelenfilets in Olivenöl"
    # Zuckerfreier Sirup zum Aufspritzen ("flavour your life", Mautner Markhof 0 %): Geschmack fast ohne Kalorien
    Kategorie("Zero-Sirup", "Extras", (r"\bfyl\b", r"flavou?r your life", r"flav ?drops",
                                        r"(zero|0 ?%|zuckerfrei|ohne zucker)[^,·]*sirup", r"sirup[^,·]*(zero|0 ?%|zuckerfrei|ohne zucker)"),
              3, 0, 0.5, 0),

    # Getränke: Energy Drinks (zuckerfrei zuerst) und Zero-Getränke
    Kategorie("Energy Drink zero", "Getränke", (r"(energy|kong strong|red ?bull|monster|power ?horse|rockstar|\bburn\b|"
                                                 r"flying power|28 black)[^,·]*(zero|sugar ?free|zuckerfrei|ohne zucker|light)",
                                                 r"(zero|sugar ?free|zuckerfrei)[^,·]*(energy|kong strong|red ?bull|monster)"),
              3, 0, 0.5, 0),
    Kategorie("Energy Drink", "Getränke", (r"\benergy\b", r"kong strong", r"red ?bull", r"\bmonster\b", r"power ?horse",
                                            r"rockstar", r"\bburn\b", r"flying power", r"28 black"), 45, 0, 11, 0,
              ausschluss=(r"riegel", r"balls?\b", r"gel\b", r"kaugummi")),
    Kategorie("Zero-Getränk", "Getränke", (r"\bzero\b", r"pepsi max", r"zuckerfrei", r"ohne zucker", r"cola[^,·]*light",
                                            r"light[^,·]*cola"), 1, 0, 0.1, 0,
              ausschluss=(r"krispel", r"wein", r"bier", r"radler", r"sekt", r"\brot\b", r"\bweiß\b", r"kaugummi",
                          r"schokolade", r"bonbon", r"gummi", r"jo(g)?hurt", r"quark", r"topfen", r"skyr", r"pudding")),

    # Joghurt und Kefir (auch mit Frucht; Desserts und Knusper-Varianten nicht)
    Kategorie("Kefir", "Milchprodukte", (r"\bkefir", r"buttermilch"), 55, 3.4, 4, 2.5),
    Kategorie("Griechisches Joghurt", "Milchprodukte", (r"(griech|greek)[^,·]*jo(g)?hurt", r"jo(g)?hurt[^,·]*(griech|greek)"),
              120, 5, 4, 9, ausschluss=(r"cheesecake", r"karamell", r"knusper", r"schoko")),
    Kategorie("Joghurt", "Milchprodukte", (r"jo(g)?hurt",), 70, 3.8, 6, 3.5,
              ausschluss=(r"knusper", r"kitkat", r"schoko", r"cheesecake", r"karamell", r"traum", r"müsli", r"ciambella",
                          r"butter", r"keks")),

    # Obst und Gemüse (frisch und tiefgekühlt). Verarbeitetes (Saft, Sirup, Marmelade, Chips …) nicht.
    Kategorie("Obst", "Obst & Gemüse", (r"(?<!erd)äpfel\b", r"\bapfel\b", r"\bbirne", r"\borangen?\b", r"mandarine",
                                         r"clementine", r"zitrone", r"limette", r"\bkiwi", r"trauben", r"\w*beeren?\b",
                                         r"ribisel", r"ananas", r"\bmango", r"melone", r"granatapfel", r"pfirsich",
                                         r"nektarine", r"marille", r"zwetschke", r"kirsche", r"grapefruit", r"papaya",
                                         r"physalis", r"avocado", r"\bobst\b"), 55, 0.7, 12, 0.3,
              ausschluss=_VERARBEITET_OG),
    Kategorie("Gemüse", "Obst & Gemüse", (r"brokkoli", r"broccoli", r"karfiol", r"blumenkohl", r"karotte", r"möhre", r"paprika",
                                           r"tomate", r"paradeiser", r"gurke", r"zucchini", r"melanzani", r"aubergine",
                                           r"spinat", r"(eis|häuptel|blatt|kopf|eisberg|vogerl|feld|endivien|radicchio)salat",
                                           r"rucola", r"kohlrabi", r"\bkraut\b", r"rotkraut", r"weißkraut", r"zwiebel",
                                           r"knoblauch", r"\blauch\b", r"porree", r"sellerie", r"champignon", r"\bpilze",
                                           r"schwammerl", r"fisolen", r"grüne bohnen", r"\berbsen\b", r"kürbis(?!kern)",
                                           r"süßkartoffel", r"rote rüben?\b", r"radieschen", r"spargel", r"kohlsprossen",
                                           r"rosenkohl", r"pak choi", r"ingwer", r"gemüse"), 25, 1.5, 3.5, 0.3,
              ausschluss=_VERARBEITET_OG + (r"hendl", r"huhn", r"hähnchen", r"kernöl", r"butter\b", r"baguette", r"röst",
                                            r"auflauf", r"suppe", r"chicken", r"filet", r"kräcker|cracker")),
)

# Was nie fitnessrelevant ist, auch wenn ein Stichwort passt
_GLOBAL_AUSSCHLUSS = re.compile(
    # Getränke mit Alkohol, Süßes, Spielzeug
    r"\b(wein|bier|likör|sekt|prosecco|wodka|whisky|schokolade|pralinen|keks|playmobil|lego|spielset)\b"
    # Fertiggerichte, Zubereitungen und Snacks: Nährwerte haben nichts mehr mit dem Grundprodukt zu tun
    r"|\beis\b|eiscreme|speiseeis|vanilleeis|schokoeis|fruchteis|baguette|tascherl|puffer|split|basis für|fix für|pizza|toast|sandwich|wrap\b|burger|nugget"
    r"|knödel|strudel|kuchen|torte|pudding|mousse|dessert|riegel|chips|cracker|smoothie|(?<!energy )drink|shake"
    r"|gratin|kroketten|wedges|lasagne|auflauf|suppe|eintopf|gulasch|risotto|bowl\b|aufstrich"
    r"|(nudel|wurst|hering|herings|makrelen|kartoffel|erdäpfel|thunfisch|eier|fleisch|reis|couscous|bulgur|krabben|"
    r"geflügel|hühner|käse|gurken|schweizer|griechischer|nudel )salat\b|salat nach|salat mit"
    r"|mohnnudeln|germknödel|marillenknödel|palatschinken|schmarrn|chili con|würstchen|bratwurst|curry\b"
)


# Händler-Kategorien (Billa/Penny), deren Produkte nie als Grundnahrungsmittel zählen
_PFAD_AUSSCHLUSS = re.compile(
    r"tiefkühlgerichte|fertiggerichte|pizza|\beis\b|eiscreme|süßes & salziges|knabber|pesto|aromen|glasuren"
    r"|pommes|kartoffelprodukte|trockenfrüchte|snack|dessert|mehlspeise|aufstrich|frischkäse|riegel|trinkmahlzeit|baby"
    r"|kosmetik|pflege|tiernahrung|katze|hund|kontaktlinse|augen|dusch|\bbad\b|shampoo|haar|haut|creme|lotion"
    r"|zahn|mund|deo|parfum|make-up|nagel|rasur|windel|reinig|wasch|putz|spül|shots?\b",
    re.I,
)


def kategorie_fuer(name: str, beschreibung: str = "") -> Kategorie | None:
    n = name.lower()
    if _GLOBAL_AUSSCHLUSS.search(n):
        return None
    for k in KATEGORIEN:
        text = f"{n} {beschreibung.lower()}" if k.mit_beschreibung else n
        if any(re.search(s, text) for s in k.stichwoerter) and not any(re.search(a, n) for a in k.ausschluss):
            return k
    return None


@dataclass
class FitnessTreffer:
    angebot: FlugblattAngebot
    kategorie: Kategorie
    gramm: float | None          # Menge in g/ml für den Preis (bei Stückware über gramm_pro_stueck)

    @property
    def preis(self) -> float:
        return self.angebot.preis

    @property
    def _echte_taugen(self) -> bool:
        """Echte Werte nehmen? Nicht, wenn sie nur "zubereitet" vorliegen und das die Werte stark ändert:
        Reis/Nudeln/Haferflocken nehmen beim Kochen Wasser auf, Sirup wird verdünnt (Gemüse, Fisch: ≈ gleich)."""
        a = self.angebot
        if a.naehrwerte is None:
            return False
        zubereitet = (a.naehrwerte_quelle or "").endswith("(zubereitet)")
        return not (zubereitet and self.kategorie.gruppe in ("Kohlenhydrate", "Extras"))

    @property
    def naehrwerte(self) -> Naehrwerte:
        """Echte Werte des Produkts, wenn bekannt und brauchbar (Händler/Open Food Facts), sonst Richtwert."""
        return self.angebot.naehrwerte if self._echte_taugen else self.kategorie.naehrwerte

    @property
    def naehrwerte_quelle(self) -> str:
        return self.angebot.naehrwerte_quelle if self._echte_taugen else "Richtwert"

    def _pro_euro(self, wert_pro_100: float | None, preis: float | None = None) -> float | None:
        preis = preis if preis is not None else self.preis
        if not self.gramm or not preis or wert_pro_100 is None:
            return None
        return round(wert_pro_100 * self.gramm / 100 / preis, 1)

    @property
    def protein_pro_euro(self) -> float | None:
        return self._pro_euro(self.naehrwerte.protein)

    @property
    def protein_pro_euro_zusatz(self) -> float | None:
        """Mit Zusatzpreis (z. B. Fr/Sa -25%), falls vorhanden."""
        z = self.angebot.zusatzpreis
        return self._pro_euro(self.naehrwerte.protein, z) if z else None

    @property
    def kcal_pro_euro(self) -> float | None:
        return self._pro_euro(self.naehrwerte.kcal)

    @property
    def protein_pro_100kcal(self) -> float:
        """Eiweißdichte: hoch = gut für die Diät."""
        nw = self.naehrwerte
        return round(nw.protein / nw.kcal * 100, 1) if nw.kcal else 0.0


def _gramm(a: FlugblattAngebot, k: Kategorie) -> float | None:
    if a.menge and a.einheit in ("g", "ml"):
        return a.menge
    if a.menge and a.einheit == "stk" and k.gramm_pro_stueck:
        return a.menge * k.gramm_pro_stueck
    if a.pro_kg:
        return 1000.0
    return None


# Wenn der Händler eine Kategorie mitliefert (Billa, Penny): Obst/Gemüse nur aus der Obst-/Gemüse-Abteilung
# (frisch oder tiefgekühlt), Joghurt/Kefir nicht aus Tiefkühl/Mehlspeisen ("Erdbeer-Joghurt-Torte")
_PFAD_PFLICHT = {
    "Obst & Gemüse": re.compile(r"obst|gemüse|salate|kräuter|pilze", re.I),
}
_PFAD_VERBOTEN = {
    "Obst & Gemüse": re.compile(r"getränke|säfte|konserven|kühlwaren|backwaren|brot", re.I),
    "Milchprodukte": re.compile(r"tiefkühl|mehlspeise|backwaren|torte", re.I),
}


# Dasselbe für einzelne Kategorien (nach Name): "Tirol Milch Tiroler Adler" ist Käse, kein Milch-Treffer;
# "Actimel Kids Erdbeere-Banane" steht bei den Milchgetränken, nicht beim Obst
_PFAD_PFLICHT_NAME = {
    "Bananen": re.compile(r"obst", re.I),
}
_PFAD_VERBOTEN_NAME = {
    "Milch": re.compile(r"käse|joghurt|butter|rahm|topfen|dessert|pudding", re.I),
}


def _pfad_passt(k: Kategorie, pfad: str) -> bool:
    if k.gruppe in _PFAD_PFLICHT and not _PFAD_PFLICHT[k.gruppe].search(pfad):
        return False
    if k.name in _PFAD_PFLICHT_NAME and not _PFAD_PFLICHT_NAME[k.name].search(pfad):
        return False
    if k.name in _PFAD_VERBOTEN_NAME and _PFAD_VERBOTEN_NAME[k.name].search(pfad):
        return False
    return not (k.gruppe in _PFAD_VERBOTEN and _PFAD_VERBOTEN[k.gruppe].search(pfad))


def fitness_angebote(angebote: list[FlugblattAngebot]) -> list[FitnessTreffer]:
    treffer = []
    for a in angebote:
        if a.kategorie_pfad and _PFAD_AUSSCHLUSS.search(a.kategorie_pfad):
            continue
        k = kategorie_fuer(a.name, a.beschreibung)
        if k and a.kategorie_pfad and not _pfad_passt(k, a.kategorie_pfad):
            continue
        if k:
            treffer.append(FitnessTreffer(a, k, _gramm(a, k)))
    return treffer


ZIELE = {
    # Sortierung: Protein pro Euro (Standard)
    "protein": lambda t: -(t.protein_pro_euro or 0),
    # Diät: nur eiweißreiche Lebensmittel (>= 8 g Protein pro 100 kcal), dann Protein pro Euro
    "diaet": lambda t: (t.protein_pro_100kcal < 8, -(t.protein_pro_euro or 0)),
    # Aufbau: möglichst viele Kalorien pro Euro
    "aufbau": lambda t: -(t.kcal_pro_euro or 0),
}


def rangliste(treffer: list[FitnessTreffer], ziel: str = "protein") -> list[FitnessTreffer]:
    return sorted(treffer, key=ZIELE[ziel])


# --- Befehlszeile --------------------------------------------------------------

DATEN_ORDNER = __import__("pathlib").Path(__file__).resolve().parents[2] / "data"


def _zeile(i: int, t: FitnessTreffer) -> str:
    a = t.angebot
    menge = f"{t.gramm:g} g" if t.gramm else "?"
    if a.pro_kg and t.gramm == 1000:
        menge = "per kg"
    bedingung = []
    if a.ab_menge:
        bedingung.append(f"ab {a.ab_menge} Stk")
    if t.protein_pro_euro_zusatz:
        bedingung.append(f"Zusatzpreis {a.zusatzpreis:.2f} € = {t.protein_pro_euro_zusatz:g} g/€")
    bedingung += a.aktion
    p = f"{t.protein_pro_euro:5.1f}" if t.protein_pro_euro is not None else "    ?"
    k = f"{t.kcal_pro_euro:5.0f}" if t.kcal_pro_euro is not None else "    ?"
    return (f"{i:3d}. {a.name[:44]:44s} {a.preis:6.2f} € {menge:>8s}  {p} g/€  {k} kcal/€  "
            f"{t.protein_pro_100kcal:4.1f}  S.{a.seite:<3d} {' | '.join(bedingung)}")


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    import pdfplumber

    from .flugblatt_pdf import analysiere_seite
    from .spar_flugblatt import REGIONEN, aktuelles_flugblatt, pdf_herunterladen

    p = argparse.ArgumentParser(prog="python -m aktionen.fitness", description="Fitness-Angebote der Woche bei Spar")
    p.add_argument("--region", default="niederoesterreich", choices=sorted(REGIONEN))
    p.add_argument("--pdf", help="Bereits heruntergeladenes Flugblatt-PDF verwenden")
    p.add_argument("--ziel", default="protein", choices=sorted(ZIELE),
                   help="protein = Protein pro €, diaet = eiweißreich zuerst, aufbau = kcal pro €")
    p.add_argument("--gruppe", choices=["Protein", "Kohlenhydrate", "Fette", "Extras"], help="Nur eine Lebensmittelgruppe")
    args = p.parse_args(argv)

    if args.pdf:
        pfad = args.pdf
    else:
        try:
            fb = aktuelles_flugblatt(args.region)
            print(f"Flugblatt: {fb.flipbook.name} ({fb.flipbook.titel})", file=sys.stderr)
            pfad = pdf_herunterladen(fb, DATEN_ORDNER)
        except Exception as e:  # noqa: BLE001
            print(f"Fehler beim Laden des Flugblatts: {e}", file=sys.stderr)
            return 1

    angebote = []
    with pdfplumber.open(pfad) as pdf:
        for n, seite in enumerate(pdf.pages, start=1):
            woerter = seite.extract_words(use_text_flow=True, extra_attrs=["size", "fontname"])
            angebote += analysiere_seite(woerter, n)

    treffer = fitness_angebote(angebote)
    if args.gruppe:
        treffer = [t for t in treffer if t.kategorie.gruppe == args.gruppe]
    print(f"{len(angebote)} Angebote, davon {len(treffer)} fitnessrelevant\n")
    print(f"{'':5s}{'Produkt':44s} {'Preis':>8s} {'Menge':>8s}  {'Protein':>8s}  {'Energie':>11s}  "
          f"{'P/100kcal':9s} Seite  Aktion")
    for i, t in enumerate(rangliste(treffer, args.ziel), start=1):
        print(_zeile(i, t))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
