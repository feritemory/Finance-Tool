#!/usr/bin/env bash
# Startet das Finance-Tool als Desktop-Programm (macOS/Linux).
# Unter macOS laesst sich diese Datei direkt per Doppelklick starten.
set -e
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "[FEHLER] Kein Python 3 gefunden. Bitte von https://www.python.org installieren." >&2
  read -rp "Zum Schliessen Eingabetaste druecken." _
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "Erstelle virtuelle Umgebung ..."
  "$PY" -m venv .venv
fi

if [ ! -f ".venv/.desktop_bereit" ]; then
  echo "Installiere Abhängigkeiten ... (kann beim ersten Mal einige Minuten dauern)"
  ./.venv/bin/python -m pip install --upgrade pip
  ./.venv/bin/python -m pip install -r requirements.txt
  echo "Richte natives Fenster ein ..."
  ./.venv/bin/python -m pip install pywebview || \
    echo "Hinweis: Kein natives Fenster verfügbar – das Programm öffnet sich im Browser."
  touch .venv/.desktop_bereit
fi

echo "Starte Finance-Tool ..."
exec ./.venv/bin/python desktop.py
