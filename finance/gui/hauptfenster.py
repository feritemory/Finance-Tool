"""Hauptfenster: Seitenleiste mit Navigation und Filtern, rechts die Seiten."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QFrame, QHBoxLayout,
                               QMainWindow, QPushButton, QStackedWidget,
                               QVBoxLayout, QWidget)

from .. import paths, service
from ..categories import CATEGORY_NAMES
from .seiten.einstellungen import Einstellungen
from .seiten.fixkosten import Fixkosten
from .seiten.importieren import Importieren
from .seiten.transaktionen import Transaktionen
from .seiten.uebersicht import Uebersicht
from .widgets import Toast, label
from .zustand import Zustand

NAVIGATION = [
    ("uebersicht", "▤", "Übersicht"),
    ("fixkosten", "↻", "Fixkosten"),
    ("transaktionen", "≡", "Transaktionen"),
    ("import", "↓", "Import"),
    ("einstellungen", "⚙", "Einstellungen"),
]


class Hauptfenster(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Finance-Tool")
        icon = paths.icon_path("icon.png")
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))
        self.resize(1360, 900)
        self.setMinimumSize(1000, 680)

        self.zustand = Zustand()
        zentral = QWidget()
        h = QHBoxLayout(zentral)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        h.addWidget(self._seitenleiste())

        self.stapel = QStackedWidget()
        self.seiten = {
            "uebersicht": Uebersicht(self.zustand),
            "fixkosten": Fixkosten(self.zustand),
            "transaktionen": Transaktionen(self.zustand),
            "import": Importieren(self.zustand),
            "einstellungen": Einstellungen(self.zustand),
        }
        for s in self.seiten.values():
            self.stapel.addWidget(s)
        h.addWidget(self.stapel, 1)
        self.setCentralWidget(zentral)

        self.toast = Toast(zentral)
        self.zustand.meldung.connect(self.toast.zeigen)
        self.zustand.daten_geaendert.connect(self._stammdaten_laden)
        self._stammdaten_laden()

        # Strg+1 … Strg+5 wechseln die Seiten
        for i, (schluessel, *_r) in enumerate(NAVIGATION, start=1):
            QShortcut(QKeySequence(f"Ctrl+{i}"), self,
                      activated=lambda s=schluessel: self.zeige(s))

    # ------------------------------------------------------------------
    def _seitenleiste(self) -> QFrame:
        leiste = QFrame()
        leiste.setObjectName("Seitenleiste")
        leiste.setFixedWidth(250)
        v = QVBoxLayout(leiste)
        v.setContentsMargins(12, 18, 12, 14)
        v.setSpacing(1)

        marke = label('<span style="color:#2a78d6">◧</span>&nbsp; Finance-Tool', "Marke")
        v.addWidget(marke)
        v.addSpacing(16)

        self.nav = QButtonGroup(self)
        self.nav.setExclusive(True)
        self.nav_knoepfe: dict[str, QPushButton] = {}
        for schluessel, symbol, text in NAVIGATION:
            b = QPushButton(f"  {symbol}    {text}")
            b.setObjectName("Nav")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, s=schluessel: self.zeige(s))
            self.nav.addButton(b)
            self.nav_knoepfe[schluessel] = b
            v.addWidget(b)
        self.nav_knoepfe["uebersicht"].setChecked(True)

        v.addSpacing(16)
        trenner = QFrame()
        trenner.setObjectName("Trenner")
        v.addWidget(trenner)
        v.addSpacing(14)
        v.addWidget(label("FILTER", "Abschnitt"))
        v.addSpacing(8)

        self.f_jahr, self.f_monat, self.f_kategorie = QComboBox(), QComboBox(), QComboBox()
        for name, box in (("Jahr", self.f_jahr), ("Monat", self.f_monat),
                          ("Kategorie", self.f_kategorie)):
            v.addWidget(label(name, "Feldname"))
            v.addSpacing(4)
            rahmen = QHBoxLayout()
            rahmen.setContentsMargins(8, 0, 8, 0)
            rahmen.addWidget(box)
            v.addLayout(rahmen)
            v.addSpacing(10)
        self.f_kategorie.addItem("Alle Kategorien", "")
        for k in CATEGORY_NAMES:
            self.f_kategorie.addItem(k, k)
        self.f_jahr.currentIndexChanged.connect(self._jahr_geaendert)
        self.f_monat.currentIndexChanged.connect(self._filter_geaendert)
        self.f_kategorie.currentIndexChanged.connect(self._filter_geaendert)

        v.addStretch(1)
        trenner2 = QFrame()
        trenner2.setObjectName("Trenner")
        v.addWidget(trenner2)
        v.addSpacing(10)
        self.fuss = label("", "Fuss", umbruch=True)
        v.addWidget(self.fuss)
        self._sperre = False
        return leiste

    # ------------------------------------------------------------------
    def zeige(self, schluessel: str) -> None:
        self.nav_knoepfe[schluessel].setChecked(True)
        self.stapel.setCurrentWidget(self.seiten[schluessel])

    def _stammdaten_laden(self) -> None:
        m = service.meta()
        self.fuss.setText(f"Datenbestand: {m['anzahl']} Umsätze<br>"
                          f"Zeitraum: {m['von']} – {m['bis']}" if m["anzahl"]
                          else "Noch keine Umsätze.")
        self._monate = m["monate"]
        self._sperre = True
        alt = self.zustand.filter.jahr
        self.f_jahr.clear()
        self.f_jahr.addItem("Alle Jahre", "alle")
        for j in m["jahre"]:
            self.f_jahr.addItem(j, j)
        i = self.f_jahr.findData(alt)
        self.f_jahr.setCurrentIndex(i if i >= 0 else 0)
        self._monate_fuellen()
        self._sperre = False
        self._filter_uebernehmen()

    def _monate_fuellen(self) -> None:
        jahr = self.f_jahr.currentData() or "alle"
        alt = self.zustand.filter.monat
        self.f_monat.clear()
        self.f_monat.addItem("Alle Monate", "alle")
        for mo in self._monate:
            if jahr == "alle" or mo.startswith(jahr):
                j, m = mo.split("-")
                self.f_monat.addItem(f"{m}/{j}", mo)
        i = self.f_monat.findData(alt)
        self.f_monat.setCurrentIndex(i if i >= 0 else 0)

    def _jahr_geaendert(self) -> None:
        if self._sperre:
            return
        self._sperre = True
        self._monate_fuellen()
        self._sperre = False
        self._filter_geaendert()

    def _filter_geaendert(self) -> None:
        if not self._sperre:
            self._filter_uebernehmen()

    def _filter_uebernehmen(self) -> None:
        """Auswahl der Seitenleiste in den Filter übernehmen; nur bei echter
        Änderung die Seiten benachrichtigen (z. B. wenn nach einem Löschen der
        gewählte Monat nicht mehr existiert)."""
        f = self.zustand.filter
        neu = (self.f_jahr.currentData() or "alle", self.f_monat.currentData() or "alle",
               self.f_kategorie.currentData() or "")
        if neu != (f.jahr, f.monat, f.kategorie):
            f.jahr, f.monat, f.kategorie = neu
            self.zustand.filter_geaendert.emit()
