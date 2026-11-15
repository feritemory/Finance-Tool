# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller-Bauanleitung für das Finance-Tool.

Ergebnis: Ordner ``Finance-Tool/`` mit ``Finance-Tool.exe`` (Ordner-Modus statt
Einzeldatei: startet schneller und löst seltener Fehlalarme von
Virenscannern aus). Der Installer (installer.iss) packt diesen Ordner.

Aufruf (aus dem Projektordner):  pyinstaller packaging/finance-tool.spec
"""

import re
import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent                      # noqa: F821
VERSION = re.search(r'__version__ = "(.+?)"',
                    (ROOT / "finance" / "__init__.py").read_text(encoding="utf-8")).group(1)

daten = [(str(ROOT / "config" / "rules.yaml"), "config")]
for datei in ("icon.png", "icon.ico", "chevron.png", "chevron@2x.png"):
    daten.append((str(ROOT / "assets" / datei), "assets"))

# Nicht benötigte Teile weglassen: spart Platz und Startzeit.
weglassen = [
    "tkinter", "matplotlib", "IPython", "jupyter", "notebook", "pytest",
    "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets",
    "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtXml", "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets", "PySide6.QtDBus", "PySide6.QtConcurrent",
    "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtUiTools",
    "PySide6.QtPrintSupport", "PySide6.QtSvgWidgets",
    # alte Web-Oberflächen – gehören nicht ins Programm
    "flask", "streamlit", "plotly", "webview",
]

a = Analysis(  # noqa: F821
    [str(ROOT / "Finance-Tool.pyw")],
    pathex=[str(ROOT)],
    datas=daten,
    hiddenimports=[],
    excludes=weglassen,
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821

versionsinfo = None
if sys.platform == "win32":
    from PyInstaller.utils.win32.versioninfo import (FixedFileInfo, StringFileInfo,
                                                     StringStruct, StringTable,
                                                     VarFileInfo, VarStruct,
                                                     VSVersionInfo)
    zahlen = tuple(int(x) for x in (VERSION.split(".") + ["0", "0", "0"])[:4])
    versionsinfo = VSVersionInfo(
        ffi=FixedFileInfo(filevers=zahlen, prodvers=zahlen),
        kids=[
            StringFileInfo([StringTable("040704b0", [
                StringStruct("CompanyName", "Finance-Tool"),
                StringStruct("FileDescription", "Finance-Tool – Einnahmen & Ausgaben"),
                StringStruct("FileVersion", VERSION),
                StringStruct("ProductName", "Finance-Tool"),
                StringStruct("ProductVersion", VERSION),
                StringStruct("OriginalFilename", "Finance-Tool.exe"),
            ])]),
            VarFileInfo([VarStruct("Translation", [0x0407, 1200])]),
        ],
    )

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Finance-Tool",
    icon=str(ROOT / "assets" / "icon.ico"),
    version=versionsinfo,
    console=False,              # Fensterprogramm, kein schwarzes Konsolenfenster
    upx=False,                  # UPX-gepackte Dateien lösen oft Virenscanner-Fehlalarme aus
)
coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    upx=False,
    name="Finance-Tool",
)
