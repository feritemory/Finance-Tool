"""Seite „Import": Kontoauszüge einlesen (Datei oder optional per PSD2)."""

from __future__ import annotations

import os

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QFileDialog, QFrame, QHBoxLayout, QLineEdit,
                               QPushButton, QVBoxLayout, QWidget)

from ... import service
from ..widgets import (Aufklapper, Karte, Meldung, Seite, im_hintergrund, label,
                       neu_polieren)

ENDUNGEN = (".csv", ".xml")


class Ablage(QFrame):
    """Fläche, auf die man Dateien ziehen kann."""

    dateien_gewaehlt = Signal(list)

    def __init__(self):
        super().__init__()
        self.setObjectName("Ablage")
        self.setAcceptDrops(True)
        v = QVBoxLayout(self)
        v.setContentsMargins(26, 26, 26, 26)
        v.setSpacing(4)
        zeile = QHBoxLayout()
        zeile.addStretch(1)
        zeile.addWidget(label("<b>Dateien hierher ziehen</b> oder"))
        self.waehlen = QPushButton("auswählen")
        self.waehlen.setObjectName("Link")
        self.waehlen.setCursor(Qt.CursorShape.PointingHandCursor)
        self.waehlen.clicked.connect(self._dialog)
        zeile.addWidget(self.waehlen)
        zeile.addStretch(1)
        v.addLayout(zeile)
        self.liste = label("Keine Datei ausgewählt.", "Hinweis", umbruch=True)
        self.liste.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.liste)

    def _dialog(self) -> None:
        dateien, _ = QFileDialog.getOpenFileNames(
            self, "Kontoauszüge auswählen", os.path.expanduser("~/Downloads"),
            "Kontoauszüge (*.csv *.xml);;Alle Dateien (*)")
        if dateien:
            self.dateien_gewaehlt.emit(dateien)

    def _hover(self, an: bool) -> None:
        self.setProperty("hover", "true" if an else "false")
        neu_polieren(self)

    def dragEnterEvent(self, e):  # noqa: N802
        if any(u.toLocalFile().lower().endswith(ENDUNGEN) for u in e.mimeData().urls()):
            e.acceptProposedAction()
            self._hover(True)

    def dragLeaveEvent(self, _e):  # noqa: N802
        self._hover(False)

    def dropEvent(self, e):  # noqa: N802
        self._hover(False)
        dateien = [u.toLocalFile() for u in e.mimeData().urls()
                   if u.toLocalFile().lower().endswith(ENDUNGEN)]
        if dateien:
            self.dateien_gewaehlt.emit(dateien)


class Importieren(Seite):
    def __init__(self, zustand):
        super().__init__("Import", "Kontoumsätze aus CSV- oder CAMT-Dateien einlesen.")
        self.zustand = zustand
        self.dateien: list[str] = []

        k = Karte("So exportierst du bei der Consorsbank")
        k.add(label(
            "1. Im Online-Banking unter <b>Umsätze</b> den Zeitraum wählen.<br>"
            "2. Export als <b>CSV</b> (oder CAMT/XML) herunterladen.<br>"
            "3. Datei hier hinzufügen – Kategorien werden automatisch zugeordnet.",
            "Hinweis", umbruch=True))
        k.add(label("Duplikate werden automatisch erkannt – überlappende Zeiträume "
                    "kannst du gefahrlos erneut laden. Vorgemerkte Umsätze werden "
                    "erst übernommen, wenn sie endgültig gebucht sind.",
                    "Hinweis", umbruch=True))
        self.ablage = k.add(Ablage())
        self.ablage.dateien_gewaehlt.connect(self._dateien_setzen)
        zeile = QHBoxLayout()
        self.knopf = QPushButton("Importieren")
        self.knopf.setObjectName("Primaer")
        self.knopf.setEnabled(False)
        self.knopf.clicked.connect(self._importieren)
        zeile.addWidget(self.knopf)
        zeile.addStretch(1)
        k.v.addLayout(zeile)
        self.ergebnis_platz = QVBoxLayout()
        k.v.addLayout(self.ergebnis_platz)
        self.hinzufuegen(k)

        self.hinzufuegen(self._psd2_karte(), 20)
        self.abschliessen()

    # --- Dateiimport ------------------------------------------------------
    def _dateien_setzen(self, dateien: list[str]) -> None:
        self.dateien = dateien
        self.ablage.liste.setText(", ".join(os.path.basename(d) for d in dateien)
                                  if dateien else "Keine Datei ausgewählt.")
        self.knopf.setEnabled(bool(dateien))

    def _ergebnis(self, w: QWidget | None) -> None:
        while self.ergebnis_platz.count():
            alt = self.ergebnis_platz.takeAt(0).widget()
            if alt:
                alt.deleteLater()
        if w:
            self.ergebnis_platz.addWidget(w)

    def _importieren(self) -> None:
        im_hintergrund(service.importieren, list(self.dateien),
                       fertig=self._import_fertig,
                       fehler=lambda t: self._ergebnis(Meldung("fehler", f"Import fehlgeschlagen: {t}")),
                       knopf=self.knopf, arbeitstext="Importiere …")

    def _import_fertig(self, erg: service.ImportErgebnis) -> None:
        diagnose = "\n".join(erg.diagnose)
        if erg.fehler:
            m = Meldung("fehler", "<br>".join(erg.fehler), diagnose)
        elif erg.gelesen == 0:
            m = Meldung("warn", "<b>Es konnten 0 Umsätze gelesen werden.</b> Vermutlich "
                        "weicht das Spaltenformat ab – die Diagnose hilft weiter.", diagnose)
        else:
            m = Meldung("erfolg", f"<b>{erg.neu} neue Umsätze importiert</b>, "
                        f"{erg.duplikate} Duplikate übersprungen.", diagnose)
        self._ergebnis(m)
        self._dateien_setzen([])
        self.zustand.daten_geaendert.emit()

    # --- PSD2 (optional) --------------------------------------------------
    def _psd2_karte(self) -> QWidget:
        k = Karte("Automatischer Kontoabruf (PSD2) – optional")
        inhalt = QWidget()
        v = QVBoxLayout(inhalt)
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(label(
            "Über die kostenlose Schnittstelle <b>GoCardless Bank Account Data</b> "
            "lassen sich Umsätze direkt von der Consorsbank abrufen. Dafür brauchst "
            "du ein kostenloses Konto bei GoCardless (Secret ID und Secret Key). "
            "Die Freigabe gilt jeweils 90 Tage.", "Hinweis", umbruch=True))
        felder = QHBoxLayout()
        self.psd2_id = QLineEdit()
        self.psd2_id.setPlaceholderText("Secret ID")
        self.psd2_key = QLineEdit()
        self.psd2_key.setPlaceholderText("Secret Key")
        self.psd2_key.setEchoMode(QLineEdit.EchoMode.Password)
        felder.addWidget(self.psd2_id)
        felder.addWidget(self.psd2_key)
        v.addLayout(felder)
        knoepfe = QHBoxLayout()
        self.psd2_link = QPushButton("1) Bank-Login öffnen")
        self.psd2_link.clicked.connect(self._psd2_login)
        self.psd2_abruf = QPushButton("2) Umsätze abrufen")
        self.psd2_abruf.setEnabled(False)
        self.psd2_abruf.clicked.connect(self._psd2_abrufen)
        knoepfe.addWidget(self.psd2_link)
        knoepfe.addWidget(self.psd2_abruf)
        knoepfe.addStretch(1)
        v.addLayout(knoepfe)
        k.add(Aufklapper("Einrichten", inhalt))
        self._anfrage_id = ""
        return k

    def _client(self):
        from ...banking.gocardless import GoCardlessClient
        return GoCardlessClient(self.psd2_id.text().strip() or None,
                                self.psd2_key.text().strip() or None)

    def _psd2_login(self) -> None:
        def los():
            return self._client().create_requisition()

        def fertig(req):
            self._anfrage_id = req["id"]
            self.psd2_abruf.setEnabled(True)
            QDesktopServices.openUrl(QUrl(req["link"]))
            self.zustand.melden("Bank-Login im Browser geöffnet. Nach der Freigabe "
                                "„Umsätze abrufen“ klicken.")

        im_hintergrund(los, fertig=fertig, knopf=self.psd2_link,
                       fehler=lambda t: self.zustand.melden(f"PSD2: {t}", True))

    def _psd2_abrufen(self) -> None:
        anfrage = self._anfrage_id

        def los():
            c = self._client()
            konten = c.list_accounts(anfrage)
            if not konten:
                raise RuntimeError("Noch kein Konto freigegeben – Bank-Login abgeschlossen?")
            return sum(service.psd2_import(c.get_transactions(k)) for k in konten)

        def fertig(n):
            self.zustand.melden(f"{n} Umsätze per PSD2 abgerufen und importiert.")
            self.zustand.daten_geaendert.emit()

        im_hintergrund(los, fertig=fertig, knopf=self.psd2_abruf,
                       fehler=lambda t: self.zustand.melden(f"PSD2: {t}", True))
