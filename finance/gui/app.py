"""Programmstart des Finance-Tools.

    Finance-Tool.exe                       normal starten
    Finance-Tool.exe --selbsttest BERICHT  automatischer Funktionstest (CI)
"""

from __future__ import annotations

import os
import sys
import tempfile
import traceback
from pathlib import Path


def _windows_vorbereiten() -> None:
    """Eigenes Taskleisten-Symbol statt des Python-Symbols."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FinanceTool.Desktop")
        except Exception:  # noqa: BLE001
            pass


def _anwendung(argv):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from .. import paths
    from . import theme

    app = QApplication.instance() or QApplication(argv)
    app.setApplicationName("Finance-Tool")
    app.setOrganizationName("Finance-Tool")
    app.setStyle("Fusion")                     # einheitliche Basis für das Stylesheet
    try:                                       # Qt ≥ 6.8: Windows-Dunkelmodus ignorieren
        app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    except AttributeError:
        pass
    app.setPalette(theme.palette())
    app.setFont(theme.app_font())
    app.setStyleSheet(theme.stylesheet())
    icon = paths.icon_path("icon.png")
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))
    return app


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    if "--selbsttest" in argv:
        i = argv.index("--selbsttest")
        bericht = argv[i + 1] if len(argv) > i + 1 else "selbsttest.txt"
        return selbsttest(bericht)

    _windows_vorbereiten()
    app = _anwendung(argv)

    from PySide6.QtCore import QLockFile
    from PySide6.QtWidgets import QMessageBox

    from .. import paths
    from .hauptfenster import Hauptfenster

    # Nur eine Instanz gleichzeitig: beide würden sonst dieselbe Datenbank ändern.
    sperre = QLockFile(str(paths.data_dir() / "finance-tool.lock"))
    sperre.setStaleLockTime(0)
    if not sperre.tryLock(100):
        QMessageBox.information(None, "Finance-Tool",
                                "Das Finance-Tool ist bereits geöffnet.")
        return 0

    fenster = Hauptfenster()
    fenster.show()
    code = app.exec()
    sperre.unlock()
    return code


# ---------------------------------------------------------------------------
# Selbsttest – prüft das fertig gebaute Programm ohne Benutzereingaben
# ---------------------------------------------------------------------------

def selbsttest(bericht_pfad: str) -> int:
    """Startet das Programm mit einem leeren Testdatenordner, spielt die
    wichtigsten Abläufe durch und schreibt einen Bericht. Rückgabe 0 = ok."""
    zeilen: list[str] = []
    ok = True

    def pruefe(name: str, bedingung: bool, info: str = "") -> None:
        nonlocal ok
        ok &= bool(bedingung)
        zeilen.append(f"[{'OK ' if bedingung else 'FEHLER'}] {name}{' – ' + info if info else ''}")

    tmp = Path(tempfile.mkdtemp(prefix="finance-selbsttest-"))
    os.environ["FINANCE_TOOL_DATA"] = str(tmp / "daten")
    try:
        app = _anwendung([sys.argv[0]])
        from PySide6.QtCore import QCoreApplication

        from .. import paths, service, storage
        from .hauptfenster import NAVIGATION, Hauptfenster
        from .widgets import warte_auf_hintergrund

        pruefe("Datenordner umgelenkt", paths.data_dir() == tmp / "daten", str(paths.data_dir()))
        pruefe("Standardregeln mitgeliefert", paths.default_rules_path().exists(),
               str(paths.default_rules_path()))
        pruefe("Symbol mitgeliefert", paths.icon_path("icon.png").exists())

        fenster = Hauptfenster()
        fenster.resize(1360, 900)
        fenster.show()
        QCoreApplication.processEvents()
        pruefe("Leerzustand", fenster.seiten["uebersicht"].leer.isVisible())

        pruefe("Demo-Daten laden", "geladen" in service.demo_laden())
        fenster.zustand.daten_geaendert.emit()
        for schluessel, *_r in NAVIGATION:
            fenster.zeige(schluessel)
            QCoreApplication.processEvents()
        ueb = fenster.seiten["uebersicht"]
        fenster.zeige("uebersicht")
        QCoreApplication.processEvents()
        pruefe("Übersicht zeigt Kennzahlen", ueb.inhalt_box.isVisible()
               and ueb.kpi_summe.kacheln[0].wert.text() != "–",
               ueb.kpi_summe.kacheln[0].wert.text())

        tx = fenster.seiten["transaktionen"]
        anzahl = tx.modell.rowCount()
        pruefe("Transaktionen geladen", anzahl > 50, f"{anzahl} Zeilen")

        export = tmp / "export.csv"
        n = service.exportieren(str(export))
        erg = service.importieren([str(export)])
        pruefe("Export → Import (Parser im fertigen Programm)",
               erg.gelesen == n and erg.neu == 0 and not erg.fehler,
               f"{erg.gelesen} gelesen, {erg.duplikate} Duplikate")

        meldung = service.modell_trainieren(0.6)
        pruefe("ML-Modell trainieren (scikit-learn eingebunden)",
               paths.model_path().exists(), meldung)

        fix = service.fixkosten(service.Filter())
        pruefe("Fixkosten erkannt", fix["summe_fixkosten"] > 0,
               f"{fix['summe_fixkosten']:.2f} €/Monat")

        bild = Path(bericht_pfad).with_suffix(".png")
        fenster.zeige("uebersicht")
        QCoreApplication.processEvents()
        pruefe("Bildschirmfoto", fenster.grab().save(str(bild)), str(bild))

        pruefe("Hintergrundaufträge beendet", warte_auf_hintergrund(5000))
        pruefe("Datenbank vorhanden", storage.count() > 0, f"{storage.count()} Umsätze")
        fenster.close()
        app.processEvents()
    except Exception:  # noqa: BLE001
        ok = False
        zeilen.append("[FEHLER] Ausnahme:\n" + traceback.format_exc())

    zeilen.append("ERGEBNIS: " + ("BESTANDEN" if ok else "FEHLGESCHLAGEN"))
    Path(bericht_pfad).write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
