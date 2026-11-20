# Konzept

## Kernidee

Aktionen sammeln gibt es schon (Marktguru, wogibtswas.at). Unser Unterschied:
**„Welches Angebot bringt mir diese Woche am meisten für mein Fitnessziel?“**

Zentrale Kennzahl: **Gramm Protein pro Euro**, dazu kcal/€ und Rabatt in %.

## Zielgruppen-Filter

| Ziel | Fokus |
|---|---|
| Diät / Cut | viel Protein, wenig kcal (Topfen, Skyr, Hühnerbrust, Thunfisch) |
| Aufbau / Bulk | viel kcal + Protein pro € (Haferflocken, Nudeln, Reis, Erdnussbutter, Vollmilch) |
| Ausdauer | Kohlenhydrate (Reis, Nudeln, Bananen, Haferflocken) |

## Kategorien

- Proteinquellen: Milchprodukte, Fleisch, Fisch, Eier, Hülsenfrüchte, Tofu
- Kohlenhydrate: Haferflocken, Reis, Nudeln, Kartoffeln, Brot
- Fette: Nüsse, Erdnussbutter, Olivenöl
- Supplements: Whey, Kreatin, Proteinriegel
- Getränke: Proteindrinks, Iso

## Datenmodell (vereinfacht)

- **Produkt**: Kette, Produktnummer, Name, Marke, Menge + Einheit, EAN, Kategorie
- **Angebot**: Produkt, Normalpreis, Aktionspreis, gültig von/bis, Aktionstext („-25 %“, „1+1“)
- **Nährwerte**: kcal, Protein, KH, Fett pro 100 g, Quelle (Open Food Facts / manuell)

## Roadmap

### Phase 1: Daten (jetzt)
- [ ] Spar: Endpunkt finden, Scraper, Tests
- [ ] Billa
- [ ] Lidl, Hofer
- [ ] Speichern in SQLite (später Postgres)

### Phase 2: Fitness-Logik
- [ ] Klassifikation „fitnessrelevant?“ (zuerst Keyword-Regeln, später KI)
- [ ] Nährwerte über Open Food Facts (EAN) + manuelle Basisliste
- [ ] Kennzahlen: Protein/€, kcal/€, Fit-Score

### Phase 3: Website
- [ ] Angebotsliste mit Filter (Kette, Kategorie, Ziel) und Sortierung
- [ ] Einkaufsliste (localStorage), gruppiert nach Laden, Makro-Summe
- [ ] Mobil-optimiert

### Phase 4: Später
- [ ] Automatischer Wochenlauf (GitHub Actions / Cron)
- [ ] Login, Listen teilen, Favoriten-Alarm
- [ ] Preisverlauf, Essensplan
- [ ] Kleinere Ketten: Penny, MPreis, ADEG, Unimarkt (ADEG ggf. nur als PDF → KI-Auswertung)
- [ ] Vor dem öffentlichen Start: Nutzungsbedingungen der Ketten prüfen
