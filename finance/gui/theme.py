"""Design-Token und Qt-Stylesheet im Stil von Notion.

Viel Weissraum, feine Rahmen, ruhige Typografie, kaum Schatten – identisch
zu den Werten der bisherigen Oberfläche.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette

INK = "#37352f"          # Haupttext
INK_SOFT = "#787774"     # Sekundärtext
INK_FAINT = "#9b9a97"    # Tertiärtext / Achsen
LINE = "#e9e9e7"         # Rahmen / Raster
LINE_SOFT = "#f1f1ef"
SURFACE = "#ffffff"
SURFACE_2 = "#f7f7f5"    # Seitenleiste, Kacheln
SURFACE_3 = "#efeeec"    # Hover / aktiver Navigationspunkt
AKZENT = "#2a78d6"
GUT = "#1baf7a"
WARN = "#eb6834"
GEFAHR = "#e34948"
POSITIV_TEXT = "#1a7f56"

# Systemschrift wie Notion: unter Windows Segoe UI.
SCHRIFTEN = ["Segoe UI", "Inter", "Helvetica Neue", "Arial", "DejaVu Sans"]


def app_font(px: int = 14) -> QFont:
    f = QFont()
    f.setFamilies(SCHRIFTEN)
    f.setPixelSize(px)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return f


def palette() -> QPalette:
    """Helle Palette erzwingen – auch wenn Windows im Dunkelmodus läuft,
    damit Dialoge und Ausklapplisten zum hellen Notion-Look passen."""
    p = QPalette()
    farben = {
        QPalette.ColorRole.Window: SURFACE,
        QPalette.ColorRole.WindowText: INK,
        QPalette.ColorRole.Base: SURFACE,
        QPalette.ColorRole.AlternateBase: SURFACE_2,
        QPalette.ColorRole.Text: INK,
        QPalette.ColorRole.Button: SURFACE,
        QPalette.ColorRole.ButtonText: INK,
        QPalette.ColorRole.Highlight: "#d3e5fa",
        QPalette.ColorRole.HighlightedText: INK,
        QPalette.ColorRole.ToolTipBase: SURFACE,
        QPalette.ColorRole.ToolTipText: INK,
        QPalette.ColorRole.PlaceholderText: INK_FAINT,
        QPalette.ColorRole.Link: AKZENT,
    }
    for rolle, farbe in farben.items():
        p.setColor(rolle, QColor(farbe))
    return p


STYLESHEET = f"""
* {{ outline: none; }}
QWidget {{ color: {INK}; font-size: 14px; }}
QMainWindow, QWidget#Inhalt, QScrollArea, QScrollArea > QWidget > QWidget {{
    background: {SURFACE};
}}

/* ---------------- Seitenleiste ---------------- */
QFrame#Seitenleiste {{
    background: {SURFACE_2};
    border: none;
    border-right: 1px solid {LINE};
}}
QLabel#Marke {{ font-size: 15px; font-weight: 650; padding: 0 8px; }}
QPushButton#Nav {{
    text-align: left; border: none; border-radius: 6px;
    padding: 7px 8px; color: {INK_SOFT}; background: transparent;
    font-size: 14px;
}}
QPushButton#Nav:hover {{ background: {SURFACE_3}; color: {INK}; }}
QPushButton#Nav:checked {{ background: {SURFACE_3}; color: {INK}; font-weight: 600; }}
QFrame#Trenner {{ background: {LINE}; max-height: 1px; min-height: 1px; border: none; }}
QLabel#Abschnitt {{
    color: {INK_FAINT}; font-size: 11px; font-weight: 650; padding: 0 8px;
}}
QLabel#Feldname {{ color: {INK_SOFT}; font-size: 12px; padding: 0 8px; }}
QLabel#Fuss {{ color: {INK_FAINT}; font-size: 12px; padding: 0 8px; }}

/* ---------------- Typografie ---------------- */
QLabel#H1 {{ font-size: 30px; font-weight: 680; }}
QLabel#Lead {{ color: {INK_SOFT}; font-size: 14px; }}
QLabel#Hinweis {{ color: {INK_SOFT}; font-size: 13px; }}
QLabel#KpiLabel {{ color: {INK_FAINT}; font-size: 11px; font-weight: 650; }}
QLabel#KarteTitel {{ font-size: 15px; font-weight: 600; }}
QLabel#Leer {{ color: {INK_FAINT}; font-size: 13px; padding: 20px 0; }}

/* ---------------- Kacheln & Karten ---------------- */
QFrame#Kpi {{
    background: {SURFACE_2}; border: 1px solid {LINE}; border-radius: 8px;
}}
QLabel#KpiName {{ color: {INK_SOFT}; font-size: 12.5px; background: transparent; }}
QLabel#KpiWert {{ font-size: 22px; font-weight: 620; background: transparent; }}
QLabel#KpiWert[negativ="true"] {{ color: {GEFAHR}; }}
QFrame#Karte {{
    background: {SURFACE}; border: 1px solid {LINE}; border-radius: 8px;
}}
QFrame#Karte QLabel {{ background: transparent; }}
QFrame#LeerKarte {{ border: 1px solid {LINE}; border-radius: 8px; }}

/* ---------------- Segment-Umschalter ---------------- */
QFrame#Segment {{
    background: {SURFACE_2}; border: 1px solid {LINE}; border-radius: 7px;
}}
QPushButton#SegmentKnopf {{
    border: none; background: transparent; color: {INK_SOFT};
    padding: 4px 11px; border-radius: 5px; font-size: 13px;
}}
QPushButton#SegmentKnopf:checked {{
    background: {SURFACE}; color: {INK}; font-weight: 600;
    border: 1px solid {LINE};
}}

/* ---------------- Schaltflächen ---------------- */
QPushButton {{
    background: {SURFACE}; color: {INK}; border: 1px solid {LINE};
    border-radius: 6px; padding: 7px 13px; font-size: 13.5px; font-weight: 500;
}}
QPushButton:hover {{ background: {SURFACE_2}; border-color: #dcdbd8; }}
QPushButton:pressed {{ background: {SURFACE_3}; }}
QPushButton:disabled {{ color: {INK_FAINT}; background: {SURFACE}; }}
QPushButton#Primaer {{ background: {INK}; color: #ffffff; border-color: {INK}; }}
QPushButton#Primaer:hover {{ background: #4a483f; border-color: #4a483f; }}
QPushButton#Primaer:disabled {{ background: #b9b8b4; border-color: #b9b8b4; color: #ffffff; }}
QPushButton#Gefahr {{ color: {GEFAHR}; }}
QPushButton#Gefahr:hover {{ background: #fdf0f0; border-color: #f3cccc; }}
QPushButton#Link {{
    border: none; background: transparent; color: {AKZENT};
    text-decoration: underline; padding: 0; font-size: 14px;
}}
QToolButton#Aufklapp {{
    border: none; background: transparent; color: {INK_SOFT}; font-size: 13px;
    padding: 4px 0;
}}
QToolButton#Aufklapp:hover {{ color: {INK}; }}

/* ---------------- Eingabefelder ---------------- */
QLineEdit, QComboBox {{
    background: {SURFACE}; border: 1px solid {LINE}; border-radius: 6px;
    padding: 6px 8px; font-size: 13.5px; selection-background-color: #d3e5fa;
}}
QLineEdit:focus, QComboBox:focus {{ border-color: {AKZENT}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{ image: url(@CHEVRON@); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE}; border: 1px solid {LINE}; border-radius: 6px;
    selection-background-color: {SURFACE_3}; selection-color: {INK}; padding: 4px;
}}
QSlider::groove:horizontal {{ height: 4px; background: {LINE}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {AKZENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: {AKZENT}; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px;
}}

/* ---------------- Tabellen ---------------- */
QTableView {{
    background: {SURFACE}; border: 1px solid {LINE}; border-radius: 8px;
    gridline-color: transparent; selection-background-color: #e8f1fc;
    selection-color: {INK}; font-size: 13.5px;
}}
QTableView::item {{ padding: 0 10px; border-bottom: 1px solid {LINE_SOFT}; }}
QTableView::item:hover {{ background: {SURFACE_2}; }}
QHeaderView::section {{
    background: {SURFACE}; color: {INK_SOFT}; font-size: 12px; font-weight: 600;
    border: none; border-bottom: 1px solid {LINE}; padding: 8px 10px;
}}
QTableCornerButton::section {{ background: {SURFACE}; border: none; }}

/* ---------------- Bildlaufleisten (schmal) ---------------- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #d9d8d5; border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #c4c3bf; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #d9d8d5; border-radius: 3px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ---------------- Meldungen ---------------- */
QFrame#Meldung {{ border: 1px solid {LINE}; border-radius: 6px; }}
QFrame#Meldung[art="erfolg"] {{ border-left: 3px solid {GUT}; background: #f2fbf7; }}
QFrame#Meldung[art="warn"]   {{ border-left: 3px solid {WARN}; background: #fef6f2; }}
QFrame#Meldung[art="fehler"] {{ border-left: 3px solid {GEFAHR}; background: #fdf2f2; }}
QFrame#Meldung QLabel {{ background: transparent; }}
QLabel#Diagnose {{
    color: {INK_SOFT}; font-size: 12px;
    font-family: "Cascadia Mono", "Consolas", "DejaVu Sans Mono", monospace;
}}
QLabel#Toast {{
    background: {INK}; color: #ffffff; border-radius: 7px;
    padding: 11px 16px; font-size: 13.5px;
}}
QLabel#Toast[fehler="true"] {{ background: {GEFAHR}; }}

QFrame#Ablage {{
    border: 2px dashed {LINE}; border-radius: 8px; background: {SURFACE};
}}
QFrame#Ablage[hover="true"] {{ border-color: {AKZENT}; background: #f5f9fe; }}

QToolTip {{
    background: {SURFACE}; color: {INK}; border: 1px solid {LINE};
    padding: 6px 9px; font-size: 12.5px;
}}
QMessageBox QLabel {{ font-size: 14px; }}
"""


def stylesheet() -> str:
    """Stylesheet mit eingesetzten Pfaden zu den mitgelieferten Grafiken.

    Qt erwartet in ``url()`` Schrägstriche – auch unter Windows.
    """
    from ..paths import icon_path
    return STYLESHEET.replace("@CHEVRON@", icon_path("chevron.png").as_posix())
