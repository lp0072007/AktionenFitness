from aktionen import verlauf


def test_schluessel_spar_stabil_ueber_wochen():
    a = {"id": "spar-wien-4-12", "kette": "spar", "name": "Schärdinger Bergbauern Joghurt", "menge": 180, "einheit": "g"}
    b = {"id": "spar-wien-7-33", "kette": "spar", "name": "Schärdinger  Bergbauern-Joghurt", "menge": 180.0, "einheit": "g"}
    assert verlauf.schluessel(a) == verlauf.schluessel(b) == "spar:schardinger bergbauern joghurt:180g"
    assert verlauf.schluessel({"id": "billa-00-89414", "kette": "billa", "name": "x"}) == "billa-00-89414"


def test_speichern_und_fuer_website():
    conn = verlauf.oeffnen(":memory:")
    skyr = {"id": "billa-1", "kette": "billa", "name": "Skyr", "preis": 1.29, "normalpreis": 1.79}
    verlauf.speichern(conn, [skyr], "2026-11-07")
    verlauf.speichern(conn, [{**skyr, "preis": 0.99}], "2026-11-14")
    verlauf.speichern(conn, [{**skyr, "preis": 1.19}], "2026-11-21")
    verlauf.speichern(conn, [{**skyr, "preis": 1.09}], "2026-11-21")  # gleicher Tag überschreibt
    einmalig = {"id": "penny-9", "kette": "penny", "name": "Topfen", "preis": 0.5}
    verlauf.speichern(conn, [einmalig], "2026-11-21")
    w = verlauf.fuer_website(conn, ["billa-1", "penny-9", "gibt-es-nicht"], "2026-11-21")
    assert w["preise"]["billa-1"] == [["2026-11-07", 1.29, 1.79], ["2026-11-14", 0.99, 1.79], ["2026-11-21", 1.09, 1.79]]
    assert "penny-9" not in w["preise"]  # nur ein Eintrag: noch kein Verlauf


def test_sql_injection_im_suchbegriff_ist_harmlos(tmp_path, capsys):
    db = tmp_path / "v.db"
    conn = verlauf.oeffnen(db)
    verlauf.speichern(conn, [{"id": "x", "kette": "billa", "name": "Milch", "preis": 1.0}], "2026-11-21")
    conn.close()
    verlauf.main(["'; DROP TABLE preise; --", "--db", str(db)])  # Suchbegriff mit SQL wird nur als Text gesucht
    verlauf.main(["Milch", "--db", str(db)])
    assert "Milch" in capsys.readouterr().out  # Tabelle und Daten sind noch da
