@echo off
REM Startet das Finance-Tool unter Windows. Legt beim ersten Aufruf eine
REM virtuelle Umgebung an und installiert die Abhaengigkeiten.
cd /d "%~dp0"

if not exist ".venv" (
  echo Erstelle virtuelle Umgebung ...
  python -m venv .venv
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate.bat
)

echo Starte Finance-Tool im Browser ...
streamlit run app.py
