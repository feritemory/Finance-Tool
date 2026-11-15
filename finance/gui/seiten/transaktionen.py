"""Seite „Transaktionen": alle Umsätze, Kategorie und Fixkosten direkt ändern."""

from __future__ import annotations

from PySide6.QtCore import (QAbstractTableModel, QModelIndex, QRectF,
                            QSortFilterProxyModel, Qt, QTimer, Signal)
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QHeaderView,
                               QLineEdit, QStyle, QStyledItemDelegate, QTableView)

from ... import service
from ...categories import CATEGORY_NAMES, COLOR_MAP
from .. import theme
from ..widgets import Seite, euro, label

SPALTEN = ["Datum", "Betrag", "Kategorie", "Empfänger", "Verwendungszweck", "Fixkosten"]
DATUM, BETRAG, KATEGORIE, EMPFAENGER, ZWECK, FIX = range(6)
SORTIER = Qt.ItemDataRole.UserRole + 1


class Modell(QAbstractTableModel):
    """Tabellenmodell über der Umsatzliste. Änderungen gehen direkt an den
    Service und werden per Signal gemeldet."""

    geaendert = Signal(str, int)          # (Art der Änderung, mitgeänderte Buchungen)
    fehler = Signal(str)

    def __init__(self):
        super().__init__()
        self.zeilen: list[dict] = []

    def setzen(self, zeilen: list[dict]) -> None:
        self.beginResetModel()
        self.zeilen = zeilen
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):  # noqa: N802
        return 0 if parent.isValid() else len(self.zeilen)

    def columnCount(self, parent=QModelIndex()):  # noqa: N802
        return 0 if parent.isValid() else len(SPALTEN)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                return SPALTEN[section]
            if role == Qt.ItemDataRole.TextAlignmentRole:
                if section == BETRAG:
                    return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return None

    def flags(self, index):
        f = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() == KATEGORIE:
            f |= Qt.ItemFlag.ItemIsEditable
        if index.column() == FIX:
            f |= Qt.ItemFlag.ItemIsUserCheckable
        return f

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        z = self.zeilen[index.row()]
        c = index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            return {DATUM: z["datum"].strftime("%d.%m.%Y"), BETRAG: euro(z["betrag"]),
                    KATEGORIE: z["kategorie"], EMPFAENGER: z["empfaenger"].strip(),
                    ZWECK: z["zweck"], FIX: ""}[c]
        if role == Qt.ItemDataRole.EditRole and c == KATEGORIE:
            return z["kategorie"]
        if role == SORTIER:
            # Nur einfache Werte (Zahl/Text) – Qt kann Python-Tupel nicht
            # vergleichen und würde sonst willkürlich sortieren. Datum + ID als
            # eine Zahl, damit Buchungen vom selben Tag stabil bleiben.
            return {DATUM: z["datum"].toordinal() * 10_000_000 + z["id"],
                    BETRAG: z["betrag"],
                    KATEGORIE: z["kategorie"], EMPFAENGER: z["empfaenger"].lower(),
                    ZWECK: z["zweck"].lower(), FIX: int(z["fixkosten"])}[c]
        if role == Qt.ItemDataRole.CheckStateRole and c == FIX:
            return Qt.CheckState.Checked if z["fixkosten"] else Qt.CheckState.Unchecked
        if role == Qt.ItemDataRole.ForegroundRole and c == BETRAG:
            return QColor(theme.GEFAHR if z["betrag"] < 0 else theme.POSITIV_TEXT)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if c == BETRAG:
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.ToolTipRole and c in (EMPFAENGER, ZWECK):
            return z["empfaenger"].strip() if c == EMPFAENGER else z["zweck"]
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):  # noqa: N802
        z = self.zeilen[index.row()]
        try:
            if index.column() == KATEGORIE and role == Qt.ItemDataRole.EditRole:
                if value == z["kategorie"]:
                    return False
                mit = service.kategorie_setzen(z["id"], value)
                z["kategorie"] = value
                self.dataChanged.emit(index, index)
                self.geaendert.emit("Kategorie gespeichert", mit)
                return True
            if index.column() == FIX and role == Qt.ItemDataRole.CheckStateRole:
                an = Qt.CheckState(value) == Qt.CheckState.Checked
                mit = service.fixkosten_setzen(z["id"], an)
                z["fixkosten"] = an
                self.dataChanged.emit(index, index)
                self.geaendert.emit("Fixkosten-Kennzeichen gespeichert", mit)
                return True
        except Exception as exc:  # noqa: BLE001
            self.fehler.emit(str(exc))
        return False


class KategorieAuswahl(QStyledItemDelegate):
    """Kategorie-Zelle: farbiger Punkt + Pfeil; Klick öffnet eine Auswahlliste,
    die Wahl wird sofort gespeichert."""

    def paint(self, p, option, index):
        self.initStyleOption(option, index)
        stil = option.widget.style() if option.widget else None
        option.text = ""
        if stil:
            stil.drawControl(QStyle.ControlElement.CE_ItemViewItem, option, p, option.widget)
        r = QRectF(option.rect).adjusted(10, 0, -10, 0)
        name = index.data(Qt.ItemDataRole.DisplayRole) or ""
        p.save()
        p.setRenderHint(p.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(COLOR_MAP.get(name, theme.INK_FAINT)))
        p.drawRoundedRect(QRectF(r.left(), r.center().y() - 4.5, 9, 9), 3, 3)
        p.setPen(QColor(theme.INK))
        text_r = r.adjusted(16, 0, -16, 0)
        p.drawText(text_r, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   option.fontMetrics.elidedText(name, Qt.TextElideMode.ElideRight,
                                                 int(text_r.width())))
        p.setPen(QColor(theme.INK_FAINT))
        p.drawText(r, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, "▾")
        p.restore()

    def createEditor(self, parent, option, index):  # noqa: N802
        box = QComboBox(parent)
        box.addItems(CATEGORY_NAMES)
        box.setMaxVisibleItems(len(CATEGORY_NAMES))
        box.activated.connect(lambda _i, b=box: (self.commitData.emit(b),
                                                 self.closeEditor.emit(b)))
        return box

    def setEditorData(self, editor, index):  # noqa: N802
        editor.setCurrentText(index.data(Qt.ItemDataRole.EditRole))
        QTimer.singleShot(0, editor.showPopup)        # Liste sofort aufklappen

    def setModelData(self, editor, model, index):  # noqa: N802
        model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)


class Transaktionen(Seite):
    def __init__(self, zustand):
        super().__init__(
            "Transaktionen",
            "Änderungen gelten für <b>alle Buchungen desselben Empfängers</b> und wirken "
            "sofort in allen Bereichen. Kategorie per Klick ändern, Spaltenköpfe sortieren.")
        self.zustand = zustand

        self.suche = QLineEdit()
        self.suche.setPlaceholderText("Suche nach Empfänger oder Verwendungszweck …")
        self.suche.setClearButtonEnabled(True)
        self._such_timer = QTimer(self, singleShot=True, interval=250)
        self._such_timer.timeout.connect(self.aktualisieren)
        self.suche.textChanged.connect(lambda _t: self._such_timer.start())
        self.hinzufuegen(self.suche)

        self.modell = Modell()
        self.modell.geaendert.connect(self._nach_aenderung)
        self.modell.fehler.connect(lambda t: zustand.melden(f"Fehler: {t}", True))
        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.modell)
        self.proxy.setSortRole(SORTIER)

        t = QTableView()
        t.setModel(self.proxy)
        t.setItemDelegateForColumn(KATEGORIE, KategorieAuswahl(t))
        t.setSortingEnabled(True)
        t.sortByColumn(DATUM, Qt.SortOrder.DescendingOrder)
        t.verticalHeader().setVisible(False)
        t.verticalHeader().setDefaultSectionSize(36)
        t.setShowGrid(False)
        t.setWordWrap(False)
        t.setMouseTracking(True)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        t.setEditTriggers(QAbstractItemView.EditTrigger.SelectedClicked
                          | QAbstractItemView.EditTrigger.CurrentChanged
                          | QAbstractItemView.EditTrigger.DoubleClicked)
        t.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        t.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        kopf = t.horizontalHeader()
        kopf.setHighlightSections(False)
        kopf.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for spalte, breite in ((DATUM, 104), (BETRAG, 112), (KATEGORIE, 250),
                               (EMPFAENGER, 250), (FIX, 86)):
            t.setColumnWidth(spalte, breite)
        kopf.setSectionResizeMode(ZWECK, QHeaderView.ResizeMode.Stretch)
        t.setMinimumHeight(420)
        self.tabelle = t
        self.hinzufuegen(t, 12, dehnen=1)           # Tabelle füllt die Fensterhöhe

        self.info = label("", "Hinweis")
        self.hinzufuegen(self.info, 8)

        zustand.daten_geaendert.connect(self.als_veraltet_markieren)
        zustand.filter_geaendert.connect(self.als_veraltet_markieren)

    def aktualisieren(self) -> None:
        pos = self.tabelle.verticalScrollBar().value()
        zeilen = service.transaktionen(self.zustand.filter, self.suche.text())
        self.modell.setzen(zeilen)
        self.tabelle.verticalScrollBar().setValue(pos)
        self.info.setText(f"{len(zeilen)} Transaktionen angezeigt." if zeilen else
                          "Keine Transaktionen gefunden.")

    def _nach_aenderung(self, text: str, mit: int) -> None:
        if mit:
            text += (f". {mit} weitere Buchung{'en' if mit != 1 else ''} desselben "
                     "Empfängers automatisch mit angepasst.")
        else:
            text += "."
        self.zustand.melden(text)
        # Alle Seiten (auch diese – wegen der mitgeänderten Zeilen) neu laden.
        # Bewusst verzögert: Wir stecken hier noch mitten im Schließen der
        # Auswahlliste bzw. im Klick auf das Häkchen. Das Modell jetzt
        # zurückzusetzen, würde der Tabelle den Editor unter den Füßen wegziehen.
        QTimer.singleShot(0, self.zustand.daten_geaendert.emit)
