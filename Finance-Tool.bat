@echo off
REM ---------------------------------------------------------------------------
REM Startet das Finance-Tool als Desktop-Programm (eigenes Fenster).
REM
REM Die virtuelle Umgebung wird BEWUSST NICHT im Projektordner angelegt,
REM sondern unter %LOCALAPPDATA%\Finance-Tool\venv. Grund: Windows begrenzt
REM Pfade auf 260 Zeichen. Liegt das Projekt tief verschachtelt (z. B. auf dem
REM Desktop mit langem Ordnernamen), sprengen die verschachtelten Paketdateien
REM sonst die Grenze und die Installation bricht mit
REM "OSError: No such file or directory" ab.
REM
REM Ausserdem: Verzeichnisnamen duerfen Klammern enthalten ("Ordner (1)").
REM Deshalb NIE %VAR% innerhalb eines Klammer-Blocks "if ... ( ... )" ausgeben -
REM die schliessende Klammer aus dem Pfad wuerde den Block beenden.
REM Stattdessen: Sprungmarken (goto) und verzoegerte Aufloesung (!VAR!).
REM ---------------------------------------------------------------------------
setlocal enableextensions enabledelayedexpansion
cd /d "%~dp0"

echo ============================================
echo    Finance-Tool
echo ============================================
echo.

REM --- Ort der virtuellen Umgebung (kurzer Pfad) -----------------------------
set "UMGEBUNG=%LOCALAPPDATA%\Finance-Tool\venv"
if not defined LOCALAPPDATA set "UMGEBUNG=%USERPROFILE%\.finance-tool\venv"
set "VENV_PY=!UMGEBUNG!\Scripts\python.exe"

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
if exist "!VENV_PY!" goto :venv_da
echo Erstelle Arbeitsumgebung unter:
echo    !UMGEBUNG!
!PY! -m venv "!UMGEBUNG!"
if errorlevel 1 goto :venv_fehler
if not exist "!VENV_PY!" goto :venv_fehler

:venv_da
REM --- Abhaengigkeiten (nur beim ersten Mal) ---------------------------------
if exist "!UMGEBUNG!\.bereit" goto :start
echo.
echo Installiere Abhaengigkeiten ... das kann beim ersten Mal einige Minuten dauern.
"!VENV_PY!" -m pip install --upgrade pip
"!VENV_PY!" -m pip install -r requirements.txt
if errorlevel 1 goto :install_fehler

echo.
echo Richte natives Fenster ein ...
"!VENV_PY!" -m pip install pywebview
if errorlevel 1 echo Hinweis: Kein natives Fenster verfuegbar - das Programm oeffnet sich stattdessen im Browser.
echo bereit> "!UMGEBUNG!\.bereit"

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
echo.
echo [FEHLER] Die Arbeitsumgebung konnte nicht erstellt werden unter:
echo    !UMGEBUNG!
echo Loesche diesen Ordner, falls vorhanden, und starte erneut.
echo.
pause
exit /b 1

:install_fehler
echo.
echo [FEHLER] Installation der Abhaengigkeiten fehlgeschlagen.
echo Pruefe deine Internetverbindung, loesche den Ordner
echo    !UMGEBUNG!
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
