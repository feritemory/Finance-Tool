"""Gemeinsamer Zustand aller Seiten: Filter und Änderungs-Benachrichtigung."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from .. import service


class Zustand(QObject):
    #: Umsätze, Kategorien oder Fixkosten-Kennzeichen haben sich geändert.
    daten_geaendert = Signal()
    #: Jahr/Monat/Kategorie in der Seitenleiste wurde umgestellt.
    filter_geaendert = Signal()
    #: Kurzmeldung anzeigen (Text, ist_fehler).
    meldung = Signal(str, bool)

    def __init__(self):
        super().__init__()
        self.filter = service.Filter()

    def melden(self, text: str, fehler: bool = False) -> None:
        self.meldung.emit(text, fehler)
