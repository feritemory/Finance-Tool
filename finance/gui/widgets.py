"""Wiederverwendbare Bausteine der Oberfläche."""

from __future__ import annotations

import traceback
from typing import Callable

from PySide6.QtCore import (QObject, QRunnable, Qt, QThreadPool, QTimer, Signal,
                            Slot)
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QPushButton, QScrollArea, QSizePolicy, QToolButton,
                               QVBoxLayout, QWidget)

# ---------------------------------------------------------------------------
# Formatierung
# ---------------------------------------------------------------------------


def euro(v: float, nk: int = 2) -> str:
    s = f"{v:,.{nk}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} €"


def euro_kurz(v: float) -> str:
    return euro(v, 0)


def neu_polieren(w: QWidget) -> None:
    """Stylesheet nach Änderung einer dynamischen Eigenschaft neu anwenden."""
    w.style().unpolish(w)
    w.style().polish(w)


def label(text: str = "", name: str | None = None, umbruch: bool = False) -> QLabel:
    lb = QLabel(text)
    if name:
        lb.setObjectName(name)
    if umbruch:
        lb.setWordWrap(True)
    lb.setTextFormat(Qt.TextFormat.RichText if "<" in text else Qt.TextFormat.AutoText)
    return lb


# ---------------------------------------------------------------------------
# Seitengerüst
# ---------------------------------------------------------------------------


class Seite(QScrollArea):
    """Scrollbare Seite mit Überschrift und Untertitel im Notion-Raster."""

    def __init__(self, titel: str, untertitel: str):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        aussen = QWidget()
        aussen.setObjectName("Inhalt")
        reihe = QHBoxLayout(aussen)
        reihe.setContentsMargins(44, 34, 44, 60)

        self.inhalt = QWidget()
        self.inhalt.setObjectName("Inhalt")
        self.inhalt.setMaximumWidth(1180)
        self.layout_ = QVBoxLayout(self.inhalt)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.layout_.setSpacing(0)
        reihe.addWidget(self.inhalt, 1)
        reihe.addStretch(0)

        self.layout_.addWidget(label(titel, "H1"))
        self.layout_.addSpacing(4)
        self.untertitel = label(untertitel, "Lead", umbruch=True)
        self.layout_.addWidget(self.untertitel)
        self.layout_.addSpacing(22)
        self.setWidget(aussen)
        self._veraltet = True

    def hinzufuegen(self, w: QWidget, abstand_oben: int = 0, dehnen: int = 0) -> QWidget:
        if abstand_oben:
            self.layout_.addSpacing(abstand_oben)
        self.layout_.addWidget(w, dehnen)
        return w

    def abschliessen(self) -> None:
        self.layout_.addStretch(1)

    # Daten neu laden – von Unterklassen überschrieben
    def aktualisieren(self) -> None:  # pragma: no cover
        pass

    def als_veraltet_markieren(self) -> None:
        self._veraltet = True
        if self.isVisible():
            self.aktualisieren_wenn_noetig()

    def aktualisieren_wenn_noetig(self) -> None:
        if self._veraltet:
            self._veraltet = False
            self.aktualisieren()

    def showEvent(self, e):  # noqa: N802
        super().showEvent(e)
        self.aktualisieren_wenn_noetig()


class Karte(QFrame):
    """Umrandete Karte mit Titelzeile; rechts optional ein Bedienelement."""

    def __init__(self, titel: str = "", rechts: QWidget | None = None):
        super().__init__()
        self.setObjectName("Karte")
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(20, 18, 20, 18)
        self.v.setSpacing(10)
        if titel or rechts:
            kopf = QHBoxLayout()
            kopf.setSpacing(16)
            self.titel = label(titel, "KarteTitel")
            kopf.addWidget(self.titel)
            kopf.addStretch(1)
            if rechts is not None:
                kopf.addWidget(rechts)
            self.v.addLayout(kopf)

    def add(self, w: QWidget, stretch: int = 0) -> QWidget:
        self.v.addWidget(w, stretch)
        return w


class Kpi(QFrame):
    def __init__(self, name: str = ""):
        super().__init__()
        self.setObjectName("Kpi")
        v = QVBoxLayout(self)
        v.setContentsMargins(15, 13, 15, 13)
        v.setSpacing(5)
        self.name = label(name, "KpiName")
        self.wert = label("–", "KpiWert")
        v.addWidget(self.name)
        v.addWidget(self.wert)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def setzen(self, name: str, wert: float, negativ_rot: bool = False) -> None:
        self.name.setText(name)
        self.wert.setText(euro(wert))
        self.wert.setProperty("negativ", "true" if negativ_rot and wert < 0 else "false")
        neu_polieren(self.wert)


class KpiReihe(QWidget):
    """Reihe aus gleich breiten Kennzahl-Kacheln."""

    def __init__(self, anzahl: int):
        super().__init__()
        g = QGridLayout(self)
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(10)
        self.kacheln = [Kpi() for _ in range(anzahl)]
        for i, k in enumerate(self.kacheln):
            g.addWidget(k, 0, i)
            g.setColumnStretch(i, 1)

    def setzen(self, werte: list[tuple]) -> None:
        for kachel, (name, wert, *rest) in zip(self.kacheln, werte):
            kachel.setzen(name, wert, bool(rest and rest[0]))


class Segment(QFrame):
    """Segment-Umschalter (z. B. Täglich | Monatlich | Jährlich)."""

    geaendert = Signal(str)

    def __init__(self, optionen: list[tuple[str, str]], aktiv: str):
        super().__init__()
        self.setObjectName("Segment")
        h = QHBoxLayout(self)
        h.setContentsMargins(2, 2, 2, 2)
        h.setSpacing(0)
        self.knoepfe: dict[str, QPushButton] = {}
        for schluessel, text in optionen:
            b = QPushButton(text)
            b.setObjectName("SegmentKnopf")
            b.setCheckable(True)
            b.setChecked(schluessel == aktiv)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=schluessel: self._waehlen(k))
            h.addWidget(b)
            self.knoepfe[schluessel] = b
        self.wert = aktiv

    def _waehlen(self, k: str) -> None:
        for s, b in self.knoepfe.items():
            b.setChecked(s == k)
        if k != self.wert:
            self.wert = k
            self.geaendert.emit(k)


class Aufklapper(QWidget):
    """Text-Knopf mit Pfeil, der einen Inhaltsbereich ein-/ausblendet."""

    def __init__(self, titel: str, inhalt: QWidget):
        super().__init__()
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        self.knopf = QToolButton()
        self.knopf.setObjectName("Aufklapp")
        self.knopf.setText(f"▸  {titel}")
        self.knopf.setCheckable(True)
        self.knopf.setCursor(Qt.CursorShape.PointingHandCursor)
        self._titel = titel
        self.inhalt = inhalt
        inhalt.setVisible(False)
        self.knopf.toggled.connect(self._umschalten)
        v.addWidget(self.knopf, 0, Qt.AlignmentFlag.AlignLeft)
        v.addWidget(inhalt)

    def _umschalten(self, an: bool) -> None:
        self.knopf.setText(f"{'▾' if an else '▸'}  {self._titel}")
        self.inhalt.setVisible(an)


class Meldung(QFrame):
    """Farbig markierte Ergebnisbox (erfolg / warn / fehler)."""

    def __init__(self, art: str, text: str, diagnose: str = ""):
        super().__init__()
        self.setObjectName("Meldung")
        self.setProperty("art", art)
        v = QVBoxLayout(self)
        v.setContentsMargins(13, 10, 13, 10)
        v.addWidget(label(text, umbruch=True))
        if diagnose:
            d = label(diagnose, "Diagnose", umbruch=True)
            d.setTextFormat(Qt.TextFormat.PlainText)
            d.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            v.addWidget(d)


class Toast(QLabel):
    """Kurzmeldung unten rechts, verschwindet nach einigen Sekunden."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setWordWrap(True)
        self.setMaximumWidth(460)
        self.hide()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        parent.installEventFilter(self)

    def zeigen(self, text: str, fehler: bool = False, ms: int = 5200) -> None:
        self.setText(text)
        self.setProperty("fehler", "true" if fehler else "false")
        neu_polieren(self)
        self.adjustSize()
        self._platzieren()
        self.show()
        self.raise_()
        self._timer.start(ms)

    def _platzieren(self) -> None:
        p = self.parentWidget()
        self.move(p.width() - self.width() - 24, p.height() - self.height() - 24)

    def eventFilter(self, obj, ev):  # noqa: N802
        if obj is self.parentWidget() and ev.type() == ev.Type.Resize and self.isVisible():
            self._platzieren()
        return False


# ---------------------------------------------------------------------------
# Hintergrund-Ausführung
# ---------------------------------------------------------------------------


class _Signale(QObject):
    fertig = Signal(object)
    fehler = Signal(str)


class _Auftrag(QRunnable):
    def __init__(self, fn: Callable, *args):
        super().__init__()
        self.fn, self.args = fn, args
        self.signale = _Signale()

    @Slot()
    def run(self):
        try:
            erg = self.fn(*self.args)
        except Exception as exc:  # noqa: BLE001 – Fehler an die Oberfläche melden
            traceback.print_exc()
            self.signale.fehler.emit(str(exc) or exc.__class__.__name__)
        else:
            self.signale.fertig.emit(erg)


_laufend: set[_Auftrag] = set()


def im_hintergrund(fn: Callable, *args, fertig: Callable | None = None,
                   fehler: Callable | None = None, knopf: QPushButton | None = None,
                   arbeitstext: str = "Arbeite …") -> None:
    """Führt ``fn`` in einem Hintergrund-Thread aus, damit das Fenster bedienbar
    bleibt. ``knopf`` wird währenddessen gesperrt und beschriftet."""
    auftrag = _Auftrag(fn, *args)
    alt = knopf.text() if knopf else ""
    if knopf:
        knopf.setEnabled(False)
        knopf.setText(arbeitstext)

    def ende():
        _laufend.discard(auftrag)
        if knopf:
            knopf.setEnabled(True)
            knopf.setText(alt)

    def ok(erg):
        ende()
        if fertig:
            fertig(erg)

    def nok(text):
        ende()
        if fehler:
            fehler(text)

    auftrag.signale.fertig.connect(ok)
    auftrag.signale.fehler.connect(nok)
    _laufend.add(auftrag)
    QThreadPool.globalInstance().start(auftrag)


def warte_auf_hintergrund(timeout_ms: int = 60000) -> bool:
    """Für Tests/Selbsttest: wartet, bis alle Hintergrundaufträge fertig sind."""
    from PySide6.QtCore import QCoreApplication, QElapsedTimer
    t = QElapsedTimer()
    t.start()
    while _laufend and t.elapsed() < timeout_ms:
        QThreadPool.globalInstance().waitForDone(50)
        QCoreApplication.processEvents()
    QCoreApplication.processEvents()
    return not _laufend
