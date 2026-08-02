#!/usr/bin/env bash
# Startet die OPTIONALE Streamlit-Oberfläche im Browser.
# Das eigentliche Desktop-Programm startest du mit ./Finance-Tool.command
set -e
cd "$(dirname "$0")"

UMGEBUNG="${XDG_DATA_HOME:-$HOME/.local/share}/finance-tool/venv-streamlit"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "[FEHLER] Kein Python 3 gefunden. Bitte von https://www.python.org installieren." >&2
  exit 1
fi

if [ ! -x "$UMGEBUNG/bin/python" ]; then
  echo "Erstelle Arbeitsumgebung unter: $UMGEBUNG"
  "$PY" -m venv "$UMGEBUNG"
fi

if [ ! -f "$UMGEBUNG/.bereit" ]; then
  echo "Installiere Abhängigkeiten ... (kann beim ersten Mal einige Minuten dauern)"
  "$UMGEBUNG/bin/python" -m pip install --upgrade pip
  "$UMGEBUNG/bin/python" -m pip install -r requirements-streamlit.txt
  touch "$UMGEBUNG/.bereit"
fi

echo "Starte Streamlit-Oberfläche im Browser ..."
exec "$UMGEBUNG/bin/python" -m streamlit run app.py
