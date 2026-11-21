# Sicherheit und Datenschutz

Die Website ist **statisch**: HTML, CSS, JavaScript und Datendateien, kein Server-Code, keine Datenbank, keine
Anmeldung. Dadurch fallen viele typische Angriffe weg.

| Risiko | Stand |
|---|---|
| SQL-Injection | Nicht möglich: es gibt keine Datenbank und keinen Server, der Eingaben verarbeitet. Die Python-Scraper laufen nur lokal. Falls später ein Backend mit SQLite kommt (Phase 1): nur Platzhalter-Abfragen (`cursor.execute("… WHERE id = ?", (id,))`), nie Text zusammenbauen. |
| Cross-Site-Scripting (XSS) | Eingaben und Daten von Händlern werden nur als Text eingefügt (`textContent`, `createElement`), nie als HTML (`innerHTML`). Zusätzlich verbietet die **Content-Security-Policy** fremde und eingebettete Skripte. |
| Schädliche Links in Daten | `Einkaufsliste.sichereUrl()` lässt für Links und Bilder nur `https:`, `http:` und relative Pfade zu, kein `javascript:`. |
| Fremde Seiten über Links | Alle externen Links mit `rel="noopener noreferrer"`. |
| Weitergabe der Herkunft | `<meta name="referrer" content="no-referrer">`: Händler-Server sehen nicht, von welcher Seite die Bildanfrage kommt. |
| Gespeicherte Daten | Nur im `localStorage` des Browsers (Liste, Einstellungen). Kaputte oder manipulierte Werte werden abgefangen (`try/catch`), nichts wird ausgeführt. |
| Geheimnisse | Keine API-Schlüssel oder Passwörter im Code. |

## Content-Security-Policy

In jeder HTML-Seite als `<meta>`:

```
default-src 'none'; script-src 'self' file:; style-src 'self' file:;
img-src 'self' file: https: data:; connect-src 'self'; base-uri 'none'; object-src 'none'
```

`file:` ist nur dabei, damit die Seite auch per Doppelklick (ohne Server) funktioniert.

## Beim Veröffentlichen

- `impressum.html` und `datenschutz.html`: Platzhalter in [eckigen Klammern] ausfüllen, Abschnitt „Hosting“ anpassen.
- HTTPS verwenden (GitHub Pages: „Enforce HTTPS“).
- Optional über den Hoster zusätzlich setzen (geht nicht per `<meta>`): `X-Frame-Options: DENY` bzw.
  `frame-ancestors 'none'`, `X-Content-Type-Options: nosniff`. GitHub Pages erlaubt keine eigenen Header, z. B.
  Netlify oder Cloudflare Pages schon (`_headers`-Datei).
