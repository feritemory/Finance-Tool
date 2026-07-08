@echo off
REM Startet das Finance-Tool unter Windows. Legt beim ersten Aufruf eine
REM virtuelle Umgebung an und installiert die Abhaengigkeiten.
setlocal enableextensions
cd /d "%~dp0"

echo ============================================
echo   Finance-Tool
echo ============================================
echo.

REM --- Python-Interpreter finden (erst py-Launcher, dann python) ---
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY (
  python --version >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo [FEHLER] Es wurde keine Python-Installation gefunden.
  echo.
  echo Bitte installiere Python 3 von:  https://www.python.org/downloads/
  echo WICHTIG: Beim Installieren die Option "Add Python to PATH" anhaken.
  echo.
  pause
  exit /b 1
)
echo Verwende Python: %PY%

REM --- Virtuelle Umgebung anlegen ---
if not exist ".venv\Scripts\python.exe" (
  echo Erstelle virtuelle Umgebung ...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo [FEHLER] Virtuelle Umgebung konnte nicht erstellt werden.
    pause
    exit /b 1
  )
)

set "VENV_PY=.venv\Scripts\python.exe"

REM --- Abhaengigkeiten installieren (nur beim ersten Mal) ---
if not exist ".venv\.installed" (
  echo Installiere Abhaengigkeiten ... das kann beim ersten Mal einige Minuten dauern.
  "%VENV_PY%" -m pip install --upgrade pip
  "%VENV_PY%" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [FEHLER] Installation der Abhaengigkeiten fehlgeschlagen.
    echo Pruefe deine Internetverbindung und starte run.bat erneut.
    pause
    exit /b 1
  )
  echo installed> ".venv\.installed"
)

echo.
echo Starte Finance-Tool im Browser ...
echo (Zum Beenden dieses Fenster schliessen oder Strg+C druecken.)
echo.
"%VENV_PY%" -m streamlit run app.py

REM Falls Streamlit unerwartet beendet wird, Fenster offen halten:
echo.
echo Die App wurde beendet.
pause
