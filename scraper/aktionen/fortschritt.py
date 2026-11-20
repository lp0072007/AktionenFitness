"""Fortschrittsanzeige für die Konsole, z. B.

    [2/8] Spar Wien
      PDF laden      ██████████░░░░░░░░░░  52 %  11,4/22,1 MB  noch ~4 s
      Seiten         ████████████████████ 100 %  25/25          fertig in 18 s

Die Zeile wird an Ort und Stelle aktualisiert (\\r). Ist die Ausgabe keine Konsole (z. B. in Tests oder
bei Umleitung in eine Datei), wird nur die Abschlusszeile geschrieben.
"""

from __future__ import annotations

import sys
import time

BREITE = 20


def _zeit(sekunden: float) -> str:
    sekunden = max(0, round(sekunden))
    return f"{sekunden // 60} min {sekunden % 60:02d} s" if sekunden >= 60 else f"{sekunden} s"


class Fortschritt:
    def __init__(self, titel: str, gesamt: float | None = None, einheit: str = "", ausgabe=None):
        self.titel = titel
        self.gesamt = gesamt
        self.einheit = einheit
        self.stand = 0.0
        self.start = time.time()
        self.ausgabe = ausgabe or sys.stderr
        self.konsole = getattr(self.ausgabe, "isatty", lambda: False)()
        self._letzte = 0.0

    def _zahl(self, x: float) -> str:
        if self.einheit == "MB":
            return f"{x / 1e6:.1f}".replace(".", ",")
        return f"{x:.0f}"

    def _zeile(self, fertig: bool = False) -> str:
        vergangen = time.time() - self.start
        if self.gesamt:
            anteil = min(1.0, self.stand / self.gesamt)
            balken = "█" * round(anteil * BREITE) + "░" * (BREITE - round(anteil * BREITE))
            menge = f"{self._zahl(self.stand)}/{self._zahl(self.gesamt)}{(' ' + self.einheit) if self.einheit else ''}"
            if fertig:
                rest = f"fertig in {_zeit(vergangen)}"
            elif anteil > 0.02 and vergangen > 0.5:
                rest = f"noch ~{_zeit(vergangen / anteil - vergangen)}"
            else:
                rest = ""
            return f"    {self.titel:<14s} {balken} {anteil * 100:3.0f} %  {menge:<16s} {rest}"
        if fertig and not self.stand:
            return f"    {self.titel:<14s} –"
        menge = f"{self._zahl(self.stand)}{(' ' + self.einheit) if self.einheit else ''}"
        return f"    {self.titel:<14s} {menge}  {'fertig in ' + _zeit(vergangen) if fertig else _zeit(vergangen)}"

    def setze(self, stand: float, gesamt: float | None = None) -> None:
        self.stand = stand
        if gesamt is not None:
            self.gesamt = gesamt
        jetzt = time.time()
        if self.konsole and jetzt - self._letzte > 0.1:  # höchstens 10x pro Sekunde neu zeichnen
            self._letzte = jetzt
            self.ausgabe.write("\r" + self._zeile().ljust(100))
            self.ausgabe.flush()

    def weiter(self, schritte: float = 1, gesamt: float | None = None) -> None:
        self.setze(self.stand + schritte, gesamt)

    def fertig(self, zusatz: str = "") -> None:
        if self.gesamt:
            self.stand = max(self.stand, self.gesamt) if self.stand >= self.gesamt * 0.99 else self.stand
        zeile = self._zeile(fertig=True) + (f"  {zusatz}" if zusatz else "")
        self.ausgabe.write(("\r" if self.konsole else "") + zeile.ljust(100) + "\n")
        self.ausgabe.flush()


class Gesamt:
    """Kopfzeilen '[2/8] Spar Wien' und Gesamtdauer am Ende.

    gewichte: geschätzter Aufwand pro Schritt (z. B. Spar 2,5, andere Ketten 1). Die Restzeit wird aus der bisherigen
    Zeit pro Gewichtseinheit hochgerechnet.
    """

    def __init__(self, gewichte: list[float], ausgabe=None):
        self.gewichte = gewichte
        self.schritte = len(gewichte)
        self.nr = 0
        self.start = time.time()
        self.ausgabe = ausgabe or sys.stderr

    def schritt(self, titel: str) -> None:
        self.nr += 1
        vergangen = time.time() - self.start
        schaetzung = ""
        erledigt = sum(self.gewichte[: self.nr - 1])
        if self.nr > 1 and erledigt:
            rest = vergangen / erledigt * sum(self.gewichte[self.nr - 1:])
            schaetzung = f"   (bisher {_zeit(vergangen)}, noch ~{_zeit(rest)})"
        self.ausgabe.write(f"\n[{self.nr}/{self.schritte}] {titel}{schaetzung}\n")
        self.ausgabe.flush()

    def ende(self) -> None:
        self.ausgabe.write(f"\nFertig in {_zeit(time.time() - self.start)}.\n")
        self.ausgabe.flush()
