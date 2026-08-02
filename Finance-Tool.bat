@echo off
REM ---------------------------------------------------------------------------
REM Startet das Finance-Tool als Desktop-Programm (eigenes Fenster).
REM Beim ersten Aufruf wird eine virtuelle Umgebung angelegt und alles Noetige
REM installiert. Danach startet das Programm in wenigen Sekunden.
REM
REM Hinweis fuer Aenderungen: Verzeichnisnamen duerfen Klammern enthalten
REM (z. B. "Ordner (1)"). Deshalb NIE %VAR% innerhalb eines Klammer-Blocks
REM "if ... ( ... )" ausgeben - die schliessende Klammer aus dem Pfad wuerde
REM den Block beenden und das Skript abstuerzen lassen. Stattdessen:
REM Sprungmarken (goto) und verzoegerte Aufloesung (!VAR!).
REM ---------------------------------------------------------------------------
setlocal enableextensions enabledelayedexpansion
cd /d "%~dp0"

echo ============================================
echo    Finance-Tool
echo ============================================
echo.

REM --- Python-Interpreter finden --------------------------------------------
set "PY="
py -3 --version >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if defined PY goto :python_ok
python --version >nul 2>&1
if not errorlevel 1 set "PY=python"
if defined PY goto :python_ok
goto :kein_python

:python_ok
REM --- Virtuelle Umgebung ----------------------------------------------------
if exist ".venv\Scripts\python.exe" goto :venv_da
echo Erstelle virtuelle Umgebung ...
!PY! -m venv .venv
if errorlevel 1 goto :venv_fehler
if not exist ".venv\Scripts\python.exe" goto :venv_fehler

:venv_da
set "VENV_PY=.venv\Scripts\python.exe"

REM --- Abhaengigkeiten (nur beim ersten Mal) ---------------------------------
if exist ".venv\.desktop_bereit" goto :start
echo Installiere Abhaengigkeiten ... das kann beim ersten Mal einige Minuten dauern.
"!VENV_PY!" -m pip install --upgrade pip
"!VENV_PY!" -m pip install -r requirements.txt
if errorlevel 1 goto :install_fehler

echo.
echo Richte natives Fenster ein ...
"!VENV_PY!" -m pip install pywebview
if errorlevel 1 echo Hinweis: Kein natives Fenster verfuegbar - das Programm oeffnet sich stattdessen im Browser.
echo bereit> ".venv\.desktop_bereit"

:start
echo.
echo Starte Finance-Tool ...
"!VENV_PY!" desktop.py
if errorlevel 1 goto :start_fehler
exit /b 0

REM --- Fehlerausgaben --------------------------------------------------------
:kein_python
echo [FEHLER] Es wurde keine Python-Installation gefunden.
echo.
echo Bitte installiere Python 3 von:  https://www.python.org/downloads/
echo WICHTIG: Beim Installieren die Option "Add python.exe to PATH" anhaken.
echo Danach ein neues Fenster oeffnen und Finance-Tool.bat erneut starten.
echo.
pause
exit /b 1

:venv_fehler
echo [FEHLER] Die virtuelle Umgebung konnte nicht erstellt werden.
echo Loesche den Ordner ".venv" und starte Finance-Tool.bat erneut.
echo.
pause
exit /b 1

:install_fehler
echo [FEHLER] Installation der Abhaengigkeiten fehlgeschlagen.
echo Haeufigste Ursachen: zu langer Projektpfad oder keine Internetverbindung.
echo Verschiebe den Ordner nach C:\Finance-Tool, loesche ".venv"
echo und starte Finance-Tool.bat erneut.
echo.
pause
exit /b 1

:start_fehler
echo.
echo [FEHLER] Das Programm wurde unerwartet beendet. Meldung siehe oben.
echo.
pause
exit /b 1
