"""Diagramme, direkt mit QPainter gezeichnet – keine Diagramm-Bibliothek nötig.

Gestaltung wie in der bisherigen Oberfläche: dünne Marken, abgerundete
Balkenenden an der Grundlinie, 2-px-Flächenspalt zwischen Balken, feines
waagerechtes Raster, Legende oben; Zahlen nur dort direkt am Balken, wo sie
lesbar bleiben – alles Weitere zeigt der Tooltip beim Überfahren.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QToolTip, QWidget

from . import theme
from .widgets import euro, euro_kurz

ZAHL = lambda v: f"{v:,.0f}".replace(",", ".")  # noqa: E731


def _schrittweite(spanne: float, anzahl: int) -> float:
    roh = spanne / max(anzahl, 1)
    if roh <= 0:
        return 1.0
    gr = 10 ** math.floor(math.log10(roh))
    for m in (1, 2, 2.5, 5, 10):
        if m * gr >= roh:
            return m * gr
    return 10 * gr


def schritte(maximum: float, anzahl: int = 5) -> list[float]:
    """Runde Achsenwerte von 0 bis über das Maximum."""
    if maximum <= 0:
        return [0.0]
    s = _schrittweite(maximum, anzahl)
    n = math.ceil(maximum / s - 1e-9)
    return [i * s for i in range(n + 1)]


def schritte_bereich(minimum: float, maximum: float, anzahl: int = 4) -> list[float]:
    """Runde Achsenwerte über einen Bereich, der negativ sein darf (mit 0)."""
    if minimum == maximum:
        minimum, maximum = min(0.0, minimum), max(0.0, maximum or 1.0)
    s = _schrittweite(maximum - minimum, anzahl)
    von, bis = math.floor(minimum / s) * s, math.ceil(maximum / s) * s
    n = round((bis - von) / s)
    return [round(von + i * s, 6) for i in range(n + 1)]


def balkenpfad(r: QRectF, radius: float = 4, waagerecht: bool = False) -> QPainterPath:
    """Rechteck mit abgerundetem Ende (oben bzw. rechts), Grundlinie bleibt eckig."""
    p = QPainterPath()
    x, y, b, h = r.x(), r.y(), r.width(), r.height()
    if waagerecht:
        rr = min(radius, b, h / 2)
        p.moveTo(x, y)
        p.lineTo(x + b - rr, y)
        p.quadTo(x + b, y, x + b, y + rr)
        p.lineTo(x + b, y + h - rr)
        p.quadTo(x + b, y + h, x + b - rr, y + h)
        p.lineTo(x, y + h)
    else:
        rr = min(radius, h, b / 2)
        p.moveTo(x, y + h)
        p.lineTo(x, y + rr)
        p.quadTo(x, y, x + rr, y)
        p.lineTo(x + b - rr, y)
        p.quadTo(x + b, y, x + b, y + rr)
        p.lineTo(x + b, y + h)
    p.closeSubpath()
    return p


class Diagramm(QWidget):
    """Basisklasse: Treffer-Flächen für Tooltips, Legende, Leerzustand."""

    HOEHE = 380

    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(self.HOEHE)
        self._treffer: list[tuple[QPainterPath, str]] = []
        self._leer = True
        self._legende: list[tuple[str, str]] = []

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(640, self.height())

    # --- Schrift ---------------------------------------------------------
    def _schrift(self, px: float = 11, gewicht: int = 400) -> QFont:
        f = theme.app_font()
        f.setPixelSize(round(px))
        f.setWeight(QFont.Weight(gewicht))
        return f

    # --- Tooltip ---------------------------------------------------------
    def _treffer_fuer(self, pfad: QPainterPath, html: str) -> None:
        self._treffer.append((pfad, html))

    def mouseMoveEvent(self, e):  # noqa: N802
        pos = e.position()
        for pfad, html in reversed(self._treffer):
            if pfad.contains(pos):
                QToolTip.showText(e.globalPosition().toPoint(), html, self)
                return
        QToolTip.hideText()

    def leaveEvent(self, e):  # noqa: N802
        QToolTip.hideText()
        super().leaveEvent(e)

    # --- Zeichnen --------------------------------------------------------
    def paintEvent(self, _e):  # noqa: N802
        self._treffer.clear()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        r = QRectF(self.rect())
        if self._leer:
            p.setPen(QColor(theme.INK_FAINT))
            p.setFont(self._schrift(13))
            p.drawText(r.adjusted(0, 10, 0, 0),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                       "Keine Daten im Zeitraum.")
        else:
            oben = self._legende_zeichnen(p, r) if self._legende else 0
            self.zeichnen(p, r.adjusted(0, oben, 0, 0))
        p.end()

    def zeichnen(self, p: QPainter, r: QRectF) -> None:  # pragma: no cover
        raise NotImplementedError

    def _legende_zeichnen(self, p: QPainter, r: QRectF) -> float:
        """Legende als umbrechende Zeile(n) oben; Rückgabe: belegte Höhe."""
        p.setFont(self._schrift(12.5))
        fm = QFontMetrics(p.font())
        x, y, zeile = r.x(), r.y() + 2, 18
        for name, farbe in self._legende:
            breite = 9 + 6 + fm.horizontalAdvance(name) + 14
            if x + breite > r.right() and x > r.x():
                x, y = r.x(), y + zeile
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(farbe))
            p.drawRoundedRect(QRectF(x, y + 4, 9, 9), 3, 3)
            p.setPen(QColor(theme.INK_SOFT))
            p.drawText(QRectF(x + 15, y, breite, zeile),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, name)
            x += breite
        return (y - r.y()) + zeile + 12

    def _raster(self, p: QPainter, plot: QRectF, werte: list[float], y_von) -> None:
        p.setFont(self._schrift(11))
        for v in werte:
            y = y_von(v)
            p.setPen(QPen(QColor("#d8d7d4" if abs(v) < 1e-9 else theme.LINE), 1))
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            p.setPen(QColor(theme.INK_FAINT))
            p.drawText(QRectF(0, y - 8, plot.left() - 8, 16),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, ZAHL(v))

    def _x_beschriftung(self, p: QPainter, mitte: float, unten: float, text: str,
                        max_breite: float) -> None:
        p.setFont(self._schrift(11))
        p.setPen(QColor(theme.INK_FAINT))
        fm = QFontMetrics(p.font())
        breite = fm.horizontalAdvance(text)
        if breite > max_breite + 6:
            return                                   # zu eng: lieber weglassen
        # Am Rand nicht abschneiden: Beschriftung in die Fläche hineinschieben.
        links = min(max(mitte - breite / 2, 0), self.width() - breite - 1)
        p.drawText(QRectF(links, unten, breite + 1, 18),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, text)


# ---------------------------------------------------------------------------


class GruppierteBalken(Diagramm):
    """Mehrere Reihen nebeneinander, alle positiv auf einer Achse."""

    HOEHE = 400

    def setzen(self, perioden: list[str], serien: list[dict], beschriften: bool) -> None:
        self.perioden, self.serien, self.beschriften = perioden, serien, beschriften
        self._leer = not perioden
        self._legende = [(s["name"], s["farbe"]) for s in serien]
        self.update()

    def zeichnen(self, p: QPainter, r: QRectF) -> None:
        plot = QRectF(r.left() + 62, r.top() + 14, r.width() - 74, r.height() - 44)
        maximum = max([max(s["werte"] or [0]) for s in self.serien] + [1])
        ticks = schritte(maximum)
        obergrenze = max(ticks[-1], maximum)
        y_von = lambda v: plot.bottom() - v / obergrenze * plot.height()  # noqa: E731
        self._raster(p, plot, ticks, y_von)

        n = len(self.perioden)
        gruppe = plot.width() / n
        innen = gruppe * 0.72
        balken = max(innen / len(self.serien) - 2, 2)
        p.setFont(self._schrift(10))
        fm = QFontMetrics(p.font())
        for i, periode in enumerate(self.perioden):
            start = plot.left() + i * gruppe + (gruppe - innen) / 2
            for j, s in enumerate(self.serien):
                wert = s["werte"][i] if i < len(s["werte"]) else 0.0
                x = start + j * (balken + 2)
                h = wert / obergrenze * plot.height()
                if h > 0.4:
                    pfad = balkenpfad(QRectF(x, y_von(wert), balken, h), 4)
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QColor(s["farbe"]))
                    p.drawPath(pfad)
                    self._treffer_fuer(pfad, f"<b>{s['name']}</b><br>{periode}<br>{euro(wert)}")
                if self.beschriften and wert > 0:
                    text = euro_kurz(wert)
                    if fm.horizontalAdvance(text) <= balken + gruppe * 0.12:
                        p.setPen(QColor(theme.INK_SOFT))
                        p.drawText(QRectF(x - 30, y_von(wert) - 17, balken + 60, 14),
                                   Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                                   text)
                        p.setFont(self._schrift(10))
            self._x_beschriftung(p, plot.left() + i * gruppe + gruppe / 2,
                                 plot.bottom() + 8, periode, gruppe)


class Linie(Diagramm):
    """Liniendiagramm mit Null-Linie; erlaubt negative Werte (Saldo)."""

    HOEHE = 300

    def setzen(self, perioden: list[str], werte: list[float], farbe: str = theme.INK) -> None:
        self.perioden, self.werte, self.farbe = perioden, werte, farbe
        self._leer = not perioden
        self.update()

    def zeichnen(self, p: QPainter, r: QRectF) -> None:
        plot = QRectF(r.left() + 66, r.top() + 12, r.width() - 80, r.height() - 42)
        ticks = schritte_bereich(min([0.0] + self.werte), max([0.0] + self.werte))
        lo, hi = ticks[0], ticks[-1]
        spanne = (hi - lo) or 1.0
        y_von = lambda v: plot.bottom() - (v - lo) / spanne * plot.height()  # noqa: E731
        self._raster(p, plot, ticks, y_von)

        n = len(self.perioden)
        x_von = (lambda i: plot.center().x()) if n == 1 else \
            (lambda i: plot.left() + i / (n - 1) * plot.width())
        pfad = QPainterPath(QPointF(x_von(0), y_von(self.werte[0])))
        for i, v in enumerate(self.werte[1:], start=1):
            pfad.lineTo(x_von(i), y_von(v))
        p.setPen(QPen(QColor(self.farbe), 2, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(pfad)

        abstand = plot.width() / max(n - 1, 1)
        for i, v in enumerate(self.werte):
            punkt = QPointF(x_von(i), y_von(v))
            p.setPen(QPen(QColor(theme.SURFACE), 2))
            p.setBrush(QColor(self.farbe))
            p.drawEllipse(punkt, 4.5, 4.5)
            ziel = QPainterPath()
            ziel.addEllipse(punkt, 11, 11)                # großzügige Trefferfläche
            self._treffer_fuer(ziel, f"{self.perioden[i]}<br><b>{euro(v)}</b>")
            if n <= 14:
                self._x_beschriftung(p, punkt.x(), plot.bottom() + 8,
                                     self.perioden[i], abstand)


class BalkenWaagerecht(Diagramm):
    """Rangfolge als waagerechte Balken mit direkter Beschriftung."""

    ZEILE = 30

    def setzen(self, zeilen: list[dict], gesamt: float = 0.0) -> None:
        self.zeilen, self.gesamt = zeilen, gesamt
        self._leer = not zeilen
        self.setFixedHeight(max(len(zeilen) * self.ZEILE + 16, 80))
        self.update()

    def zeichnen(self, p: QPainter, r: QRectF) -> None:
        label_b = min(max(r.width() * 0.34, 120), 300)
        links = r.left() + label_b + 10
        breite = r.width() - label_b - 90
        maximum = max([z["wert"] for z in self.zeilen] + [1])
        fm_label = QFontMetrics(self._schrift(12))
        for i, z in enumerate(self.zeilen):
            y = r.top() + 8 + i * self.ZEILE
            p.setFont(self._schrift(12))
            p.setPen(QColor(theme.INK_SOFT))
            text = fm_label.elidedText(z["label"], Qt.TextElideMode.ElideRight, int(label_b))
            p.drawText(QRectF(r.left(), y, label_b, 26),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, text)
            b = max(z["wert"] / maximum * breite, 2)
            pfad = balkenpfad(QRectF(links, y + 4, b, 18), 4, waagerecht=True)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(z["farbe"]))
            p.drawPath(pfad)
            anteil = f" · {z['wert'] / self.gesamt * 100:.1f} %" if self.gesamt else ""
            zusatz = f"<br>{z['zusatz']}" if z.get("zusatz") else ""
            treffer = QPainterPath()
            treffer.addRect(QRectF(r.left(), y, r.width(), 26))
            self._treffer_fuer(treffer, f"<b>{z['label']}</b><br>{euro(z['wert'])}{anteil}{zusatz}")
            p.setFont(self._schrift(11.5))
            p.setPen(QColor(theme.INK_SOFT))
            p.drawText(QRectF(links + b + 8, y, 120, 26),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       euro_kurz(z["wert"]))


class Gestapelt(Diagramm):
    """Gestapelte Balken: Anteile der Kategorien je Zeitraum."""

    HOEHE = 380

    def setzen(self, perioden: list[str], kategorien: list[str],
               werte: dict[str, list[float]], farben: dict[str, str]) -> None:
        self.perioden, self.kategorien, self.werte, self.farben = \
            perioden, kategorien, werte, farben
        self._leer = not perioden or not kategorien
        self._legende = [(k, farben.get(k, theme.INK_FAINT)) for k in kategorien]
        self.update()

    def zeichnen(self, p: QPainter, r: QRectF) -> None:
        plot = QRectF(r.left() + 62, r.top() + 12, r.width() - 74, r.height() - 42)
        summen = [sum(self.werte[k][i] for k in self.kategorien)
                  for i in range(len(self.perioden))]
        maximum = max(summen + [1])
        ticks = schritte(maximum)
        obergrenze = max(ticks[-1], maximum)
        y_von = lambda v: plot.bottom() - v / obergrenze * plot.height()  # noqa: E731
        self._raster(p, plot, ticks, y_von)

        gruppe = plot.width() / len(self.perioden)
        balken = min(gruppe * 0.62, 64)
        for i, periode in enumerate(self.perioden):
            x = plot.left() + i * gruppe + (gruppe - balken) / 2
            unten = 0.0
            for k in self.kategorien:
                v = self.werte[k][i]
                if v <= 0:
                    continue
                h = v / obergrenze * plot.height()
                seg = QRectF(x, y_von(unten + v), balken, max(h - 2, 1))  # 2-px-Spalt
                pfad = QPainterPath()
                pfad.addRoundedRect(seg, 2, 2)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(self.farben.get(k, theme.INK_FAINT)))
                p.drawPath(pfad)
                self._treffer_fuer(pfad, f"<b>{k}</b><br>{periode}<br>{euro(v)}")
                unten += v
            self._x_beschriftung(p, x + balken / 2, plot.bottom() + 8, periode, gruppe)
