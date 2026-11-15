"""Dateipfade des installierten Programms.

Ein installiertes Windows-Programm darf nicht in seinen eigenen Ordner
schreiben (der liegt unter Programme bzw. %LOCALAPPDATA%\\Programs und wird
bei Updates ersetzt). Daher gilt:

* **Benutzerdaten** (Datenbank, ML-Modell, bearbeitbare Regeln) liegen in
  ``%APPDATA%\\Finance-Tool`` – sie überleben Updates und Deinstallation.
* **Mitgelieferte Dateien** (Standard-Regeln, Symbol) liegen im
  Programmordner bzw. bei der PyInstaller-Fassung im entpackten Bundle.

Für Tests lässt sich der Datenordner über die Umgebungsvariable
``FINANCE_TOOL_DATA`` umlenken.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

APP_NAME = "Finance-Tool"


def resource_dir() -> Path:
    """Ordner mit den mitgelieferten Dateien (config/, assets/)."""
    if getattr(sys, "frozen", False):            # PyInstaller-Programm
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    """Ordner für Benutzerdaten – wird bei Bedarf angelegt."""
    override = os.environ.get("FINANCE_TOOL_DATA")
    if override:
        pfad = Path(override)
    elif sys.platform == "win32":
        basis = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        pfad = Path(basis) / APP_NAME
    elif sys.platform == "darwin":
        pfad = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        basis = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        pfad = Path(basis) / "finance-tool"
    pfad.mkdir(parents=True, exist_ok=True)
    return pfad


def db_path() -> Path:
    return data_dir() / "finance.db"


def model_path() -> Path:
    return data_dir() / "model.pkl"


def default_rules_path() -> Path:
    return resource_dir() / "config" / "rules.yaml"


def rules_path() -> Path:
    """Bearbeitbare Regeldatei des Benutzers.

    Beim ersten Zugriff wird die mitgelieferte Standarddatei in den
    Datenordner kopiert – so kann man sie anpassen, ohne dass ein Update sie
    wieder überschreibt.
    """
    ziel = data_dir() / "rules.yaml"
    if not ziel.exists():
        quelle = default_rules_path()
        if quelle.exists():
            shutil.copyfile(quelle, ziel)
        else:                                     # Notfall: leere Regeln
            ziel.write_text("{}\n", encoding="utf-8")
    return ziel


def icon_path(name: str = "icon.png") -> Path:
    return resource_dir() / "assets" / name
