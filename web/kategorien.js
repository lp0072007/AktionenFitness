// Einheitliche Produkt-Kategorien für alle Märkte (Auswahl "Kategorie" auf der Startseite).
//
// Die Märkte liefern ganz verschiedene Kategorien ("Kühlwaren > Milchprodukte", "Lebensmittel > Milch & Eier > Joghurt"),
// Spar, Lidl und Hofer gar keine. Daher: eigene Gruppen, erkannt an
//   1. der Kategorie des Markts bzw. der Fitness-Gruppe – vom genauesten Teil ("Joghurt") zum allgemeinsten ("Lebensmittel"),
//   2. sonst am Produktnamen.
//
//   Kategorien.von(angebot) -> "milch" | "fleisch" | … | "sonstiges"
//   Kategorien.LISTE        -> [{ id, name }] in Anzeige-Reihenfolge
//
// Läuft auch in Node (Tests: tests/kategorien.test.mjs).

(function (global) {
  "use strict";

  const LISTE = [
    { id: "obst", name: "Obst & Gemüse" },
    { id: "milch", name: "Milchprodukte & Eier" },
    { id: "fleisch", name: "Fleisch, Wurst & Fisch" },
    { id: "brot", name: "Brot & Gebäck" },
    { id: "vorrat", name: "Nudeln, Reis & Vorrat" },
    { id: "fertig", name: "Fertiggerichte" },
    { id: "tk", name: "Tiefgefroren" },
    { id: "suess", name: "Süßes & Snacks" },
    { id: "getraenke", name: "Getränke" },
    { id: "kaffee", name: "Kaffee & Tee" },
    { id: "alkohol", name: "Bier, Wein & Spirituosen" },
    { id: "drogerie", name: "Drogerie & Haushalt" },
    { id: "sonstiges", name: "Sonstiges" },
  ];

  // Reihenfolge zählt: die erste passende Regel gewinnt (z. B. "Erdnussbutter" ist Vorrat, nicht Milch).
  const REGELN = [
    ["milch", /joghurtgetränk|milchgetränk|milchmix|trinkjoghurt/],
    ["vorrat", /nussbutter|erdnuss|nussmus|mandelmus|kokosmilch|balsamico|essig|suppennudel/],
    ["suess", /katzenzungen|adventkalender|weihnachtsmann|weihnachtsmänner|nikolo|krampus|lindt|lindor|merci|ferrero|kinder|raffaello|mozartkugel|toblerone|twix|snickers|oreo|bounty|kitkat|ritter sport|mon ch[eé]ri|schaumbecher|zuckerl|duplo|bueno|schwedenbomben|schofrulade|linzer augen|loacker|happy hippo|hanuta|knoppers|ovomaltine/],
    ["kaffee", /dallmayr|prodomo|tchibo|jacobs|nescaf|lavazza|meinl|caffè|café-kapseln|kaffeekapseln/],
    ["drogerie", /badesalz|vogel|meisenknödel|playmobil|lego|spielzeug|drogerie|haushalt|kosmetik|körperpflege|pflege\b|waschmittel|weichspüler|spülmittel|spültabs|reiniger|shampoo|duschgel|zahnpasta|zahncreme|toilettenpapier|küchenrolle|taschentücher|windeln|deo\b|deodorant|tierbedarf|tiernahrung|katzen|hunde|futter|batterie/],
    ["alkohol", /\bbier|bier\b|radler|wein\b|weißwein|rotwein|rosé|sekt|prosecco|champagner|schaumwein|spirituosen|likör|schnaps|vodka|wodka|whisk|\bgin\b|\brum\b|aperol|weinbrand|bargetränk|cider|spritzer|frizzante|riesling|veltliner|zweigelt|blaufränkisch|chardonnay|merlot|cabernet|sauvignon|muskateller|glühwein|punsch|lager|pils|märzen|wieselburger|gösser|stiegl|ottakringer|zipfer|kozel|puntigamer|cognac|averna|barbera|chianti|primitivo/],
    ["getraenke", /alkoholfrei|limonade|\blimo|mineralwasser|wasser\b|säfte|saft\b|nektar|sirup|eistee|ice ?tea|energy|cola\b|cola[\s-]|almdudler|fanta|sprite|pepsi|red bull|schweppes|getränk|smoothie/],
    ["kaffee", /kaffee|espresso|cappuccino|kakao|(?<!eis)tee\b|tees\b|kräutertee|früchtetee|kaffeekapseln/],
    ["fleisch", /fleisch|wurst|würst|schinken|speck|salami|leberkäs|faschiert|schnitzel|kotelett|steak|hendl|huhn|hühner|hähnchen|chicken|geflügel|pute|truthahn|\brind|rinder|rinds|schwein|kalb|lamm|fisch|lachs|thunfisch|forelle|garnelen|shrimps|meeresfrüchte|kabeljau|seelachs|makrele|sardine|dorsch|scholle|sardellen|pangasius|matjes|hering|filet|aufschnitt|pancetta|prosciutto|tafelspitz|ente|cevapcici|kebab|gyros/],
    ["milch", /milch|joghurt|jogurt|skyr|kefir|topfen|quark|käse|cheese|mozzarella|feta|butter(?!nuss)|rahm|sahne|obers|eier\b|^eier|\bei\b|liptauer|cheddar|burrata|stracciatella|gouda|emmentaler|camembert|molkerei|desserts?\b|pudding/],
    ["fertig", /fertiggericht|schnelle küche|dosengericht|suppe|eintopf|pizza|lasagne|knödel|tortellini|ravioli|gnocchi|nuggets|frühlingsrolle/],
    ["suess", /süß|schoko|praline|bonbon|gummi|fruchtgummi|lakritz|kekse?\b|biskotten|waffel|riegel|chips|knabber|salzstangen|popcorn|cracker|(^|[^r])eis\b|eiscreme|stanitzel|stanizl|torte|krapfen|lebkuchen|marzipan|manner|milka|haribo|nutella/],
    ["brot", /brot|gebäck|semmel|weckerl|toast|baguette|croissant|kipferl|cronut|donut|brioche|kuchen|striezel|bäckerei|backwaren/],
    ["obst", /obst|gemüse|salat|frucht|früchte|apfel|äpfel|birne|banane|orange|mandarine|clementine|zitrone|trauben|beeren|kiwi|ananas|mango|melone|avocado|tomate|paradeiser|gurke|paprika|karotte|zwiebel|knoblauch|erdäpfel|kartoffel|brokkoli|karfiol|zucchini|kürbis|pilze|champignon|kraut\b|spinat|lauch|radieschen|oliven(?!öl)|rote rüben|maroni/],
    ["vorrat", /vorrat|grundnahrung|teigwaren|nudel|pasta|spaghetti|penne|fusilli|\breis|reis\b|risotto|mehl|zucker|grieß|getreide|haferflocken|müsli|cerealien|cornflakes|konserve|öl\b|öle\b|olivenöl|essig|sauce|soße|sugo|pesto|ketchup|mayonnaise|mayonaise|senf|kren|gewürz|salz\b|pfeffer|kräuter|backen|backmischung|hefe|honig|marmelade|konfitüre|aufstrich|nüsse|nuss\b|mandeln|linsen|bohnen|kichererbsen|mais\b|asia|internationale|kochzutaten|basisprodukte|fixprodukte|dressing/],
  ];
  // Teile der Markt-Kategorie, die nichts über die Gruppe sagen (dann zählt der nächst allgemeinere Teil oder der Name)
  const ALLGEMEIN = /^(lebensmittel|kühlwaren|rein pflanzlich.*|neu im online shop|aktion.*|angebote?)$/;

  // Iglo und Frosta sind nur Tiefkühlware; Lidl schreibt "In der Tiefkühltruhe" in die Beschreibung
  const TIEFGEFROREN = /\biglo\b|\bfrosta\b|tiefkühl|tiefgekühlt|tiefgefroren/i;

  function regelFuer(text) {
    const t = text.toLowerCase();
    for (const [id, muster] of REGELN) if (muster.test(t)) return id;
    return null;
  }

  function von(a) {
    const pfad = (a.kategorie ?? "").split(">").map((s) => s.trim()).filter(Boolean);
    // Tiefkühl-Abteilung schlägt alles (Eis, Gemüse, Pizza aus der Tiefkühltruhe)
    if (pfad.some((s) => /tiefkühl|tiefgekühlt/i.test(s))) return "tk";
    // Ohne Tiefkühl-Abteilung (Fitness-Gruppen, Lidl, Hofer, Spar): Marke oder Hinweis im Text
    if (TIEFGEFROREN.test(`${a.name ?? ""} ${a.beschreibung ?? ""}`)) return "tk";
    for (const teil of pfad.reverse()) {
      if (ALLGEMEIN.test(teil.toLowerCase())) continue;
      const id = regelFuer(teil);
      if (id) return id;
    }
    return regelFuer(a.name ?? "") ?? "sonstiges";
  }

  const NAME = Object.fromEntries(LISTE.map((k) => [k.id, k.name]));
  const api = { LISTE, NAME, von };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else global.Kategorien = api;
})(typeof window !== "undefined" ? window : globalThis);
