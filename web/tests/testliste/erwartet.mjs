// Testliste: typische Einkaufslisten-Einträge und was der Abgleich finden muss (muss) bzw. nicht finden darf (nicht).
// Grundlage: eingefrorene echte Aktionen (angebote.json, KW 47/2026), damit die Tests nicht jede Woche brechen.
// Neue Fälle einfach unten ergänzen – am besten jeden Fehltreffer, der beim Einkaufen auffällt.

export const FAELLE = [
  // Milchprodukte
  { eingabe: "Milch", muss: ["penny-78-100272", "penny-78-115430", "penny-78-343836", "spar-niederoesterreich-17-137"],
    nicht: ["penny-78-593309", "penny-78-939490", "penny-78-80002", "penny-78-613298", "lidl-11305149", "billa-00-23598", "billa-00-899623", "billa-00-435152"] },
  { eingabe: "Vollmilch", muss: ["penny-78-100272", "spar-niederoesterreich-17-137", "penny-78-343836"], nicht: ["spar-niederoesterreich-12-88", "billa-00-423198"] },
  { eingabe: "Skyr", muss: ["billa-00-388559"] },
  { eingabe: "Magertopfen", muss: ["lidl-11369787", "penny-78-28984"], nicht: ["lidl-11265504", "billa-00-293184", "billa-00-273266", "billa-00-967996"] },
  { eingabe: "Topfen", muss: ["penny-78-28984"], nicht: ["billa-00-802976", "billa-00-737131", "billa-00-578649"] },
  { eingabe: "Hüttenkäse", muss: ["penny-78-599028", "spar-niederoesterreich-14-102"], nicht: ["billa-00-874884"] },
  { eingabe: "Joghurt", muss: ["spar-niederoesterreich-12-90", "penny-78-100999"], nicht: ["hofer-271052001", "billa-00-775192", "billa-00-575094", "hofer-758858"] },
  { eingabe: "Naturjoghurt", muss: ["penny-78-100999", "penny-78-441383"] },
  { eingabe: "Eier", muss: ["penny-78-339761", "billa-00-968705"], nicht: ["penny-78-502104", "penny-78-514865", "billa-00-590334", "hofer-743339002"] },
  { eingabe: "Butter", muss: ["lidl-11305418", "penny-78-343284"], nicht: ["penny-78-289573", "lidl-11372144", "billa-00-733272", "penny-78-398946", "billa-00-866693"] },
  { eingabe: "Mozzarella", muss: ["lidl-11372884", "penny-78-113277"], nicht: ["billa-00-412820", "billa-00-498351", "billa-00-372579"] },
  { eingabe: "Gouda", muss: ["billa-00-438578"] },
  { eingabe: "Schlagobers", muss: ["penny-78-521795"], nicht: ["billa-00-805714", "penny-78-535351"] },

  // Fleisch, Fisch
  { eingabe: "Hendlfilet", muss: ["spar-niederoesterreich-10-71", "penny-78-540702", "penny-78-544689", "lidl-11374291"],
    nicht: ["penny-78-616589", "billa-00-958365", "spar-niederoesterreich-10-69"] },
  { eingabe: "Hühnerbrust", muss: ["hofer-724949"] },
  { eingabe: "Putenbrust", muss: ["penny-78-538358", "lidl-11499551"], nicht: ["billa-00-593375", "billa-00-412694"] },
  { eingabe: "Faschiertes", muss: ["penny-78-504763", "billa-00-871614", "spar-niederoesterreich-8-48"], nicht: ["billa-00-11080", "billa-00-383238"] },
  { eingabe: "Rindfleisch", muss: ["penny-78-544603", "spar-niederoesterreich-9-58"], nicht: ["billa-00-311158", "billa-00-384027", "billa-00-6494"] },
  { eingabe: "Lachs", muss: ["spar-niederoesterreich-11-80", "lidl-11004222", "billa-00-764922", "billa-00-878884"],
    nicht: ["billa-00-718311", "billa-00-261657", "billa-00-433917", "billa-00-874889", "billa-00-789336", "lidl-11461116"] },
  { eingabe: "Thunfisch", muss: ["billa-00-749981", "spar-niederoesterreich-11-81", "lidl-11007054", "lidl-11000792"],
    nicht: ["billa-00-693126", "billa-00-864947"] },
  { eingabe: "Thunfisch in Öl", muss: ["hofer-300704", "billa-00-749965"], nicht: ["billa-00-749981"] },
  { eingabe: "Garnelen", muss: ["lidl-11003485", "billa-00-507295"] },
  { eingabe: "Schinken", muss: ["penny-78-278319", "lidl-11118022"], nicht: ["billa-00-416251", "billa-00-693125", "billa-00-798405"] },

  // Kohlenhydrate
  { eingabe: "Reis", muss: ["spar-niederoesterreich-8-41", "hofer-304291", "billa-00-721830"],
    nicht: ["billa-00-435152", "billa-00-467735", "billa-00-44763", "billa-00-614971", "penny-78-283112"] },
  { eingabe: "Basmatireis", muss: ["spar-niederoesterreich-8-41", "hofer-281508006"] },
  { eingabe: "Nudeln", muss: ["penny-78-110665", "hofer-108993", "hofer-108995", "billa-00-924097"],
    nicht: ["lidl-11685394", "billa-00-3046", "billa-00-776522", "billa-00-9365", "billa-00-750719"] },
  { eingabe: "Spaghetti", muss: ["hofer-108993", "billa-00-924097"], nicht: ["hofer-108995", "hofer-7407931588161431579098", "billa-00-750719"] },
  { eingabe: "Brot", muss: ["penny-78-116773", "spar-niederoesterreich-17-133"], nicht: ["billa-00-796990", "billa-00-401399", "penny-78-626061"] },
  { eingabe: "Semmeln", muss: ["billa-00-890740", "spar-niederoesterreich-17-136"], nicht: ["billa-00-730157", "lidl-11371562"] },
  { eingabe: "Erdäpfel", muss: ["penny-78-426945"], nicht: ["billa-00-737917", "billa-00-703668", "spar-niederoesterreich-20-157"] },
  { eingabe: "Kartoffeln", muss: ["penny-78-804458"] },
  { eingabe: "Haferflocken", muss: [], nicht: ["billa-00-780582", "billa-00-735130"] },

  // Obst, Gemüse
  { eingabe: "Bananen", muss: ["lidl-11150766"], nicht: ["hofer-109274", "billa-00-272364", "billa-00-747818"] },
  { eingabe: "Äpfel", muss: ["lidl-11150818", "penny-78-804413"],
    nicht: ["penny-78-426945", "penny-78-804458", "penny-78-418270", "hofer-493952008", "billa-00-667911", "billa-00-10351", "billa-00-332"] },
  { eingabe: "Himbeeren", muss: ["spar-niederoesterreich-8-52", "billa-00-380087"],
    nicht: ["billa-00-646295", "billa-00-443418", "billa-00-743439", "billa-00-277799", "billa-00-775938"] },
  { eingabe: "Brokkoli", muss: ["lidl-11151157", "billa-00-504077", "billa-00-721548"], nicht: ["billa-00-30388", "billa-00-702640", "billa-00-777934"] },
  { eingabe: "Karotten", muss: ["billa-00-501323"], nicht: ["billa-00-719416"] },
  { eingabe: "Tomaten", muss: ["penny-78-425782"], nicht: ["billa-00-782277", "billa-00-906363", "billa-00-345074"] },
  { eingabe: "Paprika", muss: ["penny-78-663062"], nicht: ["billa-00-885468", "billa-00-288652", "hofer-588307002", "billa-00-746119"] },
  { eingabe: "Gurke", muss: ["penny-78-368603"] },
  { eingabe: "Zwiebeln", muss: ["penny-78-817910"], nicht: ["billa-00-774452", "billa-00-885470", "billa-00-407536"] },
  { eingabe: "Salat", muss: ["penny-78-409218", "billa-00-89743"], nicht: ["billa-00-433917", "billa-00-385014", "billa-00-899647"] },

  // Nüsse, Öl, Getränke, Extras
  { eingabe: "Mandeln", muss: ["penny-78-514450", "billa-00-495103"], nicht: ["billa-00-742533", "billa-00-780559", "billa-00-477890", "billa-00-701152"] },
  { eingabe: "Nüsse", muss: ["hofer-496381", "spar-niederoesterreich-8-45"], nicht: ["hofer-107026", "penny-78-12012", "billa-00-603043", "penny-78-480329"] },
  { eingabe: "Olivenöl", muss: ["penny-78-455753", "billa-00-865820"] },
  { eingabe: "Mineralwasser", muss: ["penny-78-552661", "lidl-11678220"], nicht: ["hofer-715630", "billa-00-280617"] },
  { eingabe: "Cola Zero", muss: ["billa-00-770212", "hofer-637337002"], nicht: ["billa-00-770211", "billa-00-717744", "hofer-493952009"] },
  { eingabe: "Zero Sirup", muss: ["spar-niederoesterreich-17-142", "billa-00-646295"], nicht: ["billa-00-618535", "billa-00-257588"] },
  { eingabe: "Kaffee", muss: ["penny-78-748037", "billa-00-424921"], nicht: ["penny-78-80002", "billa-00-22553"] },
  { eingabe: "Proteinriegel", muss: ["billa-00-874984", "billa-00-278754"], nicht: ["penny-78-708861", "penny-78-100272", "billa-00-879823"] },
  { eingabe: "Linsen", muss: ["billa-00-594652"], nicht: ["billa-00-902698"] },

  // Mengen, Synonyme, Schreibweisen
  { eingabe: "2x Hendlbrust 500g", muss: ["spar-niederoesterreich-10-71"] },
  { eingabe: "Frische Eier (10er)", muss: ["penny-78-339761"] },
  { eingabe: "Faschiertes 1kg", muss: ["penny-78-504763"] },
  { eingabe: "Broccoli", muss: ["billa-00-504077"] },
  { eingabe: "Zahnpasta", muss: ["lidl-11685394"], nicht: ["penny-78-110665"] },
];
