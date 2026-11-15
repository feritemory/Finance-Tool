"""Seite „Einstellungen": Kategorisierung steuern, Daten verwalten."""

from __future__ import annotations

import os

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QFileDialog, QGridLayout, QHBoxLayout, QMessageBox,
                               QPushButton, QSlider, QWidget)

from ... import __version__, paths, service
from ...ml import DEFAULT_THRESHOLD
from ..widgets import Karte, Seite, im_hintergrund, label


def _knopf(text: str, art: str = "") -> QPushButton:
    b = QPushButton(text)
    if art:
        b.setObjectName(art)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def _reihe(*knoepfe) -> QHBoxLayout:
    h = QHBoxLayout()
    h.setSpacing(8)
    for k in knoepfe:
        h.addWidget(k)
    h.addStretch(1)
    return h


class Einstellungen(Seite):
    def __init__(self, zustand):
        super().__init__("Einstellungen", "Kategorisierung steuern und Daten verwalten.")
        self.zustand = zustand

        # --- ML ------------------------------------------------------------
        k = Karte("Selbstlernende Kategorisierung")
        self.ml_status = k.add(label("", "Hinweis", umbruch=True))
        schwelle = QHBoxLayout()
        schwelle.addWidget(label("Mindest-Sicherheit für automatische Zuordnung:", "Hinweis"))
        self.regler = QSlider(Qt.Orientation.Horizontal)
        self.regler.setRange(8, 18)                     # ×5 % → 40 … 90 %
        self.regler.setValue(round(DEFAULT_THRESHOLD * 100 / 5))
        self.regler.setFixedWidth(200)
        self.regler_wert = label("", "Hinweis")
        self.regler.valueChanged.connect(lambda v: self.regler_wert.setText(f"{v * 5} %"))
        self.regler.valueChanged.emit(self.regler.value())
        schwelle.addWidget(self.regler)
        schwelle.addWidget(self.regler_wert)
        schwelle.addStretch(1)
        k.v.addLayout(schwelle)
        self.b_trainieren = _knopf("Modell trainieren && anwenden", "Primaer")
        self.b_trainieren.clicked.connect(self._trainieren)
        self.b_modell_weg = _knopf("Modell löschen")
        self.b_modell_weg.clicked.connect(
            lambda: self._aktion(service.modell_loeschen, self.b_modell_weg))
        k.v.addLayout(_reihe(self.b_trainieren, self.b_modell_weg))
        self.hinzufuegen(k)

        raster = QGridLayout()
        raster.setHorizontalSpacing(20)
        raster.setContentsMargins(0, 20, 0, 0)

        # --- Regeln & Gelerntes ------------------------------------------
        k = Karte("Regeln & Gelerntes")
        self.regel_status = k.add(label("", "Hinweis", umbruch=True))
        b1 = _knopf("Regeln neu anwenden")
        b1.clicked.connect(lambda: self._aktion(service.neu_kategorisieren, b1))
        b2 = _knopf("Regeldatei bearbeiten")
        b2.setToolTip("Öffnet die Stichwort-Regeln im Standard-Editor. Nach dem "
                      "Speichern „Regeln neu anwenden“ klicken.")
        b2.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(paths.rules_path()))))
        b3 = _knopf("Gelernte Regeln löschen")
        b3.clicked.connect(lambda: self._aktion(
            service.gelernte_loeschen, b3,
            "Alle aus deinen Korrekturen gelernten Händler-Regeln löschen?"))
        b4 = _knopf("Fixkosten-Entscheidungen zurücksetzen")
        b4.clicked.connect(lambda: self._aktion(
            service.fixkosten_zuruecksetzen, b4,
            "Alle manuell gesetzten Fixkosten-Häkchen verwerfen? Danach entscheidet "
            "wieder allein die automatische Erkennung."))
        k.v.addLayout(_reihe(b1, b2))
        k.v.addLayout(_reihe(b3))
        k.v.addLayout(_reihe(b4))
        k.v.addStretch(1)
        raster.addWidget(k, 0, 0)

        # --- Daten ------------------------------------------------------------
        k = Karte("Daten")
        self.daten_status = k.add(label("", "Hinweis", umbruch=True))
        d1 = _knopf("Demo-Daten laden")
        d1.clicked.connect(lambda: self._aktion(service.demo_laden, d1))
        d2 = _knopf("Demo-Daten entfernen")
        d2.clicked.connect(lambda: self._aktion(service.demo_entfernen, d2))
        d3 = _knopf("Als CSV exportieren …")
        d3.clicked.connect(self._exportieren)
        d4 = _knopf("Datenbank übernehmen …")
        d4.setToolTip("Übernimmt Umsätze, gelernte Regeln und Fixkosten-Entscheidungen "
                      "aus einer früheren Version (Datei finance.db).")
        d4.clicked.connect(self._uebernehmen)
        d5 = _knopf("Datenordner öffnen")
        d5.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(paths.data_dir()))))
        d6 = _knopf("Alle Daten löschen", "Gefahr")
        d6.clicked.connect(lambda: self._aktion(
            service.alles_loeschen, d6,
            "Wirklich ALLE gespeicherten Umsätze unwiderruflich löschen?", gefahr=True))
        k.v.addLayout(_reihe(d1, d2))
        k.v.addLayout(_reihe(d3, d4))
        k.v.addLayout(_reihe(d5, d6))
        k.v.addStretch(1)
        raster.addWidget(k, 0, 1)
        raster.setColumnStretch(0, 1)
        raster.setColumnStretch(1, 1)
        box = QWidget()
        box.setLayout(raster)
        self.hinzufuegen(box)

        self.ueber = label("", "Hinweis", umbruch=True)
        self.ueber.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.hinzufuegen(self.ueber, 22)
        self.abschliessen()

        zustand.daten_geaendert.connect(self.als_veraltet_markieren)

    # ------------------------------------------------------------------
    def aktualisieren(self) -> None:
        m = service.meta()
        if not m["ml_verfuegbar"]:
            self.ml_status.setText("Das Modul für maschinelles Lernen ist nicht verfügbar – "
                                   "die Kategorisierung arbeitet rein regelbasiert.")
            self.b_trainieren.setEnabled(False)
        else:
            self.ml_status.setText(
                "Das Modell lernt aus deinen bereits kategorisierten Ausgaben und ordnet "
                "ähnliche neue Buchungen automatisch zu. Status: "
                f"<b>{'trainiert' if m['ml_trainiert'] else 'noch nicht trainiert'}</b>. "
                "Alles bleibt lokal auf deinem Rechner.")
        self.b_modell_weg.setEnabled(m["ml_trainiert"])
        self.regel_status.setText(
            f"Gelernte Händler-Regeln: <b>{m['gelernte_regeln']}</b> · "
            f"Manuelle Fixkosten-Entscheidungen: <b>{m['manuelle_fixkosten']}</b>")
        self.daten_status.setText(
            f"Gespeicherte Umsätze: <b>{m['anzahl']}</b> · davon Demo-Daten: "
            f"<b>{m['demo_anzahl']}</b>")
        self.ueber.setText(f"Finance-Tool {__version__} · Daten liegen in "
                           f"<code>{m['datenordner']}</code>")

    # ------------------------------------------------------------------
    def _fragen(self, frage: str, gefahr: bool = False) -> bool:
        box = QMessageBox(self)
        box.setWindowTitle("Finance-Tool")
        box.setIcon(QMessageBox.Icon.Warning if gefahr else QMessageBox.Icon.Question)
        box.setText(frage)
        ja = box.addButton("Löschen" if gefahr else "Ja", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Abbrechen", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        return box.clickedButton() is ja

    def _aktion(self, fn, knopf, frage: str = "", gefahr: bool = False) -> None:
        if frage and not self._fragen(frage, gefahr):
            return
        im_hintergrund(fn, knopf=knopf, fertig=self._fertig,
                       fehler=lambda t: self.zustand.melden(t, True))

    def _fertig(self, meldung: str) -> None:
        self.zustand.melden(meldung)
        self.zustand.daten_geaendert.emit()

    def _trainieren(self) -> None:
        im_hintergrund(service.modell_trainieren, self.regler.value() * 5 / 100,
                       knopf=self.b_trainieren, arbeitstext="Trainiere …",
                       fertig=self._fertig, fehler=lambda t: self.zustand.melden(t, True))

    def _exportieren(self) -> None:
        ziel, _ = QFileDialog.getSaveFileName(
            self, "Umsätze exportieren",
            os.path.join(os.path.expanduser("~"), "Documents", "umsaetze_export.csv"),
            "CSV für Excel (*.csv)")
        if not ziel:
            return
        try:
            n = service.exportieren(ziel)
            self.zustand.melden(f"{n} Umsätze exportiert nach {os.path.basename(ziel)}.")
        except Exception as exc:  # noqa: BLE001
            self.zustand.melden(f"Export fehlgeschlagen: {exc}", True)

    def _uebernehmen(self) -> None:
        quelle, _ = QFileDialog.getOpenFileName(
            self, "Datenbank der früheren Version wählen (finance.db)",
            os.path.expanduser("~/Desktop"), "Finance-Tool-Datenbank (finance.db *.db)")
        if not quelle:
            return
        if not self._fragen("Die gewählte Datenbank ersetzt die aktuellen Daten. Die "
                            "bisherige Datenbank wird vorher gesichert. Fortfahren?"):
            return
        im_hintergrund(service.datenbank_uebernehmen, quelle, fertig=self._fertig,
                       fehler=lambda t: self.zustand.melden(t, True))
