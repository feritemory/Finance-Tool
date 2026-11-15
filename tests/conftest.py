import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Qt ohne Bildschirm betreiben (CI, Server).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def datenordner(tmp_path, monkeypatch):
    """Jeder Test bekommt einen eigenen, leeren Datenordner."""
    monkeypatch.setenv("FINANCE_TOOL_DATA", str(tmp_path / "daten"))
    yield tmp_path / "daten"


@pytest.fixture
def consors_csv(tmp_path):
    import consors_beispiel
    return consors_beispiel.schreibe(tmp_path / "Umsatzuebersicht_000000000.csv")
