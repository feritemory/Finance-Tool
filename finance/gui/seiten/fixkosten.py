"""Seite „Fixkosten": wiederkehrende Zahlungen und feste Sparbeträge."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

from ... import service
from ...categories import COLOR_MAP
from .. import theme
from ..charts import BalkenWaagerecht
from ..widgets import Karte, KpiReihe, Seite, euro, label

SPALTEN = ["Empfänger (erkannt)", "Kategorie", "Rhythmus", "Je Zahlung",
           "≈ pro Monat", "Quelle"]


def _tabelle() -> QTableWidget:
    t = QTableWidget(0, len(SPALTEN))
    t.setHorizontalHeaderLabels(SPALTEN)
    t.verticalHeader().setVisible(False)
    t.verticalHeader().setDefaultSectionSize(34)
    t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    t.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
    t.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    kopf = t.horizontalHeader()
    kopf.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    kopf.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    kopf.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    for i in range(2, len(SPALTEN)):
        kopf.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
    t.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    return t


def _fuellen(t: QTableWidget, zeilen: list[dict]) -> None:
    t.setRowCount(len(zeilen))
    rechts = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    for i, z in enumerate(zeilen):
        werte = [z["empfaenger"], z["kategorie"], z["rhythmus"], euro(z["je_zahlung"]),
                 euro(z["monatsbetrag"]),
                 "manuell gesetzt" if z["manuell"] else "automatisch erkannt"]
        for j, w in enumerate(werte):
            item = QTableWidgetItem(w)
            if j == 0:
                farbe = QColor(COLOR_MAP.get(z["kategorie"], theme.INK_FAINT))
                item.setData(Qt.ItemDataRole.DecorationRole, farbe)
            if j in (3, 4):
                item.setTextAlignment(rechts)
            if j == 5:
                item.setForeground(QColor("#1c5cab" if z["manuell"] else theme.INK_SOFT))
            t.setItem(i, j, item)
    # Tabelle so hoch wie ihr Inhalt – die Seite scrollt als Ganzes.
    t.setFixedHeight(t.horizontalHeader().height() + 34 * len(zeilen) + 4)


class Fixkosten(Seite):
    def __init__(self, zustand):
        super().__init__("Fixkosten",
                         "Wiederkehrende Zahlungen, automatisch erkannt – von dir korrigierbar.")
        self.zustand = zustand

        self.kpi = KpiReihe(2)
        self.hinzufuegen(self.kpi)

        k = Karte("Fixkosten pro Monat")
        self.diagramm = k.add(BalkenWaagerecht())
        self.leer = k.add(label("Keine wiederkehrenden Fixkosten erkannt.", "Leer"))
        self.tabelle = k.add(_tabelle())
        self.hinzufuegen(k, 20)

        self.k_sparen = Karte("Feste Sparbeträge")
        self.t_sparen = self.k_sparen.add(_tabelle())
        self.hinzufuegen(self.k_sparen, 20)

        self.hinzufuegen(label(
            "Erkannt werden Empfänger mit wiederkehrendem, konstantem Betrag; häufig "
            "besuchte Händler (z. B. Supermärkte) werden bewusst ausgeschlossen. "
            "Zahlungen, die nur alle paar Monate anfallen (z. B. die "
            "BAföG-Rückzahlung), werden auf einen Monatsbetrag umgerechnet.<br>"
            "<b>Stimmt etwas nicht?</b> Setze oder entferne unter <b>Transaktionen</b> "
            "das Häkchen <b>Fixkosten</b> – das gilt für alle Buchungen dieses "
            "Empfängers und übersteuert die Automatik dauerhaft.",
            "Hinweis", umbruch=True), 14)
        self.abschliessen()

        zustand.daten_geaendert.connect(self.als_veraltet_markieren)
        zustand.filter_geaendert.connect(self.als_veraltet_markieren)

    def aktualisieren(self) -> None:
        d = service.fixkosten(self.zustand.filter)
        self.kpi.setzen([("Fixkosten pro Monat", d["summe_fixkosten"]),
                         ("Festes Sparen pro Monat", d["summe_sparen"])])
        fx = d["fixkosten"]
        self.leer.setVisible(not fx)
        self.diagramm.setVisible(bool(fx))
        self.tabelle.setVisible(bool(fx))
        if fx:
            zeilen = [{"label": z["empfaenger"], "wert": z["monatsbetrag"],
                       "farbe": COLOR_MAP.get(z["kategorie"], theme.INK_FAINT),
                       "zusatz": f"{z['kategorie']} · {z['rhythmus']}"} for z in fx]
            self.diagramm.setzen(zeilen)
            _fuellen(self.tabelle, fx)
        self.k_sparen.setVisible(bool(d["sparen"]))
        if d["sparen"]:
            _fuellen(self.t_sparen, d["sparen"])
