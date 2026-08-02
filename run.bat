@echo off
REM ---------------------------------------------------------------------------
REM Startet die OPTIONALE Streamlit-Oberflaeche im Browser.
REM Das eigentliche Desktop-Programm startest du mit Finance-Tool.bat.
REM
REM Die virtuelle Umgebung liegt BEWUSST unter %LOCALAPPDATA%\Finance-Tool,
REM nicht im Projektordner: Streamlit bringt sehr tief verschachtelte Dateien
REM mit und sprengt in langen Projektpfaden sonst die 260-Zeichen-Grenze von
REM Windows ("OSError: No such file or directory").
REM
REM Ausserdem: NIE %VAR% innerhalb eines Klammer-Blocks "if ... ( ... )"
REM ausgeben - eine Klammer im Pfad ("Ordner (1)") wuerde den Block beenden.
REM ---------------------------------------------------------------------------
setlocal enableextensions enabledelayedexpansion
cd /d "%~dp0"

echo ============================================
echo    Finance-Tool - Streamlit-Oberflaeche
echo ============================================
echo.

set "UMGEBUNG=%LOCALAPPDATA%\Finance-Tool\venv-streamlit"
if not defined LOCALAPPDATA set "UMGEBUNG=%USERPROFILE%\.finance-tool\venv-streamlit"
set "VENV_PY=!UMGEBUNG!\Scripts\python.exe"

set "PY="
py -3 --version >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if defined PY goto :python_ok
python --version >nul 2>&1
if not errorlevel 1 set "PY=python"
if defined PY goto :python_ok
goto :kein_python

:python_ok
if exist "!VENV_PY!" goto :venv_da
echo Erstelle Arbeitsumgebung unter:
echo    !UMGEBUNG!
!PY! -m venv "!UMGEBUNG!"
if errorlevel 1 goto :venv_fehler
if not exist "!VENV_PY!" goto :venv_fehler

:venv_da
if exist "!UMGEBUNG!\.bereit" goto :start
echo.
echo Installiere Abhaengigkeiten ... das kann beim ersten Mal einige Minuten dauern.
"!VENV_PY!" -m pip install --upgrade pip
"!VENV_PY!" -m pip install -r requirements-streamlit.txt
if errorlevel 1 goto :install_fehler
echo bereit> "!UMGEBUNG!\.bereit"

:start
echo.
echo Starte Streamlit-Oberflaeche im Browser ...
echo Zum Beenden: dieses Fenster schliessen oder Strg+C druecken.
echo.
"!VENV_PY!" -m streamlit run app.py
echo.
echo Die Oberflaeche wurde beendet.
pause
exit /b 0

:kein_python
echo [FEHLER] Es wurde keine Python-Installation gefunden.
echo.
echo Bitte installiere Python 3 von:  https://www.python.org/downloads/
echo WICHTIG: Beim Installieren die Option "Add python.exe to PATH" anhaken.
echo.
pause
exit /b 1

:venv_fehler
echo.
echo [FEHLER] Die Arbeitsumgebung konnte nicht erstellt werden unter:
echo    !UMGEBUNG!
echo.
pause
exit /b 1

:install_fehler
echo.
echo [FEHLER] Installation der Abhaengigkeiten fehlgeschlagen.
echo Loesche den Ordner
echo    !UMGEBUNG!
echo und starte run.bat erneut.
echo.
pause
exit /b 1
