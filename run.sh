#!/usr/bin/env bash
# Startet das Finance-Tool. Legt beim ersten Aufruf eine virtuelle Umgebung an
# und installiert die Abhängigkeiten.
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Erstelle virtuelle Umgebung ..."
  python3 -m venv .venv
  ./.venv/bin/pip install --upgrade pip
  ./.venv/bin/pip install -r requirements.txt
fi

echo "Starte Finance-Tool im Browser ..."
./.venv/bin/streamlit run app.py
