#!/usr/bin/env bash
# Startet das Finance-Tool. Legt beim ersten Aufruf eine virtuelle Umgebung an
# und installiert die Abhängigkeiten.
set -e
cd "$(dirname "$0")"

# Python-Interpreter finden
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "[FEHLER] Kein Python 3 gefunden. Bitte von https://www.python.org installieren." >&2
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "Erstelle virtuelle Umgebung ..."
  "$PY" -m venv .venv
fi

if [ ! -f ".venv/.installed" ]; then
  echo "Installiere Abhängigkeiten ... (kann beim ersten Mal einige Minuten dauern)"
  ./.venv/bin/python -m pip install --upgrade pip
  ./.venv/bin/python -m pip install -r requirements.txt
  touch .venv/.installed
fi

echo "Starte Finance-Tool im Browser ..."
exec ./.venv/bin/python -m streamlit run app.py
