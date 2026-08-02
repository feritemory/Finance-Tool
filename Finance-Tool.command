#!/usr/bin/env bash
# Startet das Finance-Tool als Desktop-Programm (macOS/Linux).
# Unter macOS laesst sich diese Datei direkt per Doppelklick starten.
set -e
cd "$(dirname "$0")"

# Arbeitsumgebung ausserhalb des Projektordners – hält Projektpfade kurz und
# das Projektverzeichnis frei von Installationsdateien.
UMGEBUNG="${XDG_DATA_HOME:-$HOME/.local/share}/finance-tool/venv"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "[FEHLER] Kein Python 3 gefunden. Bitte von https://www.python.org installieren." >&2
  read -rp "Zum Schliessen Eingabetaste druecken." _
  exit 1
fi

if [ ! -x "$UMGEBUNG/bin/python" ]; then
  echo "Erstelle Arbeitsumgebung unter: $UMGEBUNG"
  "$PY" -m venv "$UMGEBUNG"
fi

if [ ! -f "$UMGEBUNG/.bereit" ]; then
  echo "Installiere Abhängigkeiten ... (kann beim ersten Mal einige Minuten dauern)"
  "$UMGEBUNG/bin/python" -m pip install --upgrade pip
  "$UMGEBUNG/bin/python" -m pip install -r requirements.txt
  echo "Richte natives Fenster ein ..."
  "$UMGEBUNG/bin/python" -m pip install pywebview || \
    echo "Hinweis: Kein natives Fenster verfügbar – das Programm öffnet sich im Browser."
  touch "$UMGEBUNG/.bereit"
fi

echo "Starte Finance-Tool ..."
exec "$UMGEBUNG/bin/python" desktop.py
