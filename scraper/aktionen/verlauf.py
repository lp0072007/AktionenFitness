"""Preisverlauf: bei jedem Export die Preise aller Aktionen speichern und für die Website aufbereiten.

Speicher: SQLite-Datei data/preisverlauf.db (nicht im Git). Eine Zeile pro Produkt und Tag.
Website:  web/data/verlauf.js -> window.VERLAUF = {stand, preise: {schluessel: [[datum, preis, normalpreis], ...]}}

    python -m aktionen.verlauf skyr          # Verlauf aller Produkte mit "skyr" im Namen
    python -m aktionen.verlauf --statistik   # wie viele Produkte, Tage, Zeilen

Alle Abfragen mit Platzhaltern (?), nie Text zusammensetzen (SQL-Injection).
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import unicodedata
from datetime import date, timedelta
from pathlib import Path

from .fitness import DATEN_ORDNER

DB_PFAD = DATEN_ORDNER / "preisverlauf.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS preise (
    schluessel  TEXT NOT NULL,   -- Produkt: Händler-ID (billa-00-89414) oder bei Spar "spar:name:menge"
    datum       TEXT NOT NULL,   -- Tag des Exports, ISO (2026-11-21)
    kette       TEXT NOT NULL,
    name        TEXT NOT NULL,
    preis       REAL NOT NULL,   -- Aktionspreis (dm: Dauerpreis)
    normalpreis REAL,
    menge       REAL,
    einheit     TEXT,
    PRIMARY KEY (schluessel, datum)
);
CREATE INDEX IF NOT EXISTS preise_name ON preise(name);
"""


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def schluessel(d: dict) -> str:
    """Stabiler Schlüssel über Wochen hinweg.

    Lidl, Hofer, Penny, Billa, dm haben eigene Produkt-IDs. Spar-Flugblatt-IDs (Seite/Position) ändern sich jede
    Woche, deshalb dort Name + Menge.
    """
    if d.get("kette") == "spar":
        menge = f"{d['menge']:g}{d.get('einheit') or ''}" if d.get("menge") else ""
        return f"spar:{_norm(d['name'])}:{menge}"
    return d["id"]


def oeffnen(pfad: Path | str = DB_PFAD) -> sqlite3.Connection:
    if str(pfad) != ":memory:":
        Path(pfad).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(pfad))
    conn.executescript(_SCHEMA)
    return conn


def speichern(conn: sqlite3.Connection, angebote: list[dict], datum: str) -> int:
    """Preise eines Exports speichern. Mehrere Exporte am selben Tag überschreiben sich."""
    zeilen = []
    for d in angebote:
        if d.get("preis") is None or not d.get("name"):
            continue
        zeilen.append((schluessel(d), datum, d["kette"], d["name"], float(d["preis"]), d.get("normalpreis"),
                       d.get("menge"), d.get("einheit")))
    with conn:
        conn.executemany(
            "INSERT OR REPLACE INTO preise (schluessel, datum, kette, name, preis, normalpreis, menge, einheit) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", zeilen)
    return len(zeilen)


def fuer_website(conn: sqlite3.Connection, schluessel_liste: list[str], heute: str, wochen: int = 26) -> dict:
    """Verlauf der aktuellen Produkte (letzte `wochen` Wochen), nur wenn es mehr als einen Eintrag gibt."""
    seit = (date.fromisoformat(heute) - timedelta(weeks=wochen)).isoformat()
    gesucht = sorted(set(schluessel_liste))
    preise: dict[str, list] = {}
    for i in range(0, len(gesucht), 500):  # SQLite: begrenzte Anzahl Platzhalter pro Abfrage
        teil = gesucht[i:i + 500]
        platzhalter = ",".join("?" * len(teil))
        for s, datum, preis, normal in conn.execute(
                f"SELECT schluessel, datum, preis, normalpreis FROM preise "
                f"WHERE datum >= ? AND schluessel IN ({platzhalter}) ORDER BY datum", (seit, *teil)):
            preise.setdefault(s, []).append([datum, preis] + ([normal] if normal else []))
    return {"stand": heute, "preise": {s: v for s, v in preise.items() if len(v) > 1}}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m aktionen.verlauf")
    p.add_argument("suche", nargs="?", help="Teil des Produktnamens")
    p.add_argument("--statistik", action="store_true")
    p.add_argument("--db", default=str(DB_PFAD))
    args = p.parse_args(argv)
    conn = oeffnen(args.db)
    if args.statistik or not args.suche:
        produkte, tage, zeilen = conn.execute(
            "SELECT COUNT(DISTINCT schluessel), COUNT(DISTINCT datum), COUNT(*) FROM preise").fetchone()
        print(f"{args.db}: {produkte} Produkte, {tage} Tage, {zeilen} Preise")
        return 0
    aktuell = None
    for s, kette, name, datum, preis, normal in conn.execute(
            "SELECT schluessel, kette, name, datum, preis, normalpreis FROM preise "
            "WHERE name LIKE ? ORDER BY schluessel, datum", (f"%{args.suche}%",)):
        if s != aktuell:
            print(f"\n{kette:6} {name}")
            aktuell = s
        print(f"         {datum}  {preis:7.2f} €" + (f"  (statt {normal:.2f})" if normal else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
