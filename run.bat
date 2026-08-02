@echo off
REM ---------------------------------------------------------------------------
REM Startet das Finance-Tool unter Windows. Legt beim ersten Aufruf eine
REM virtuelle Umgebung an und installiert die Abhaengigkeiten.
REM
REM Hinweis fuer Aenderungen: Verzeichnisnamen duerfen Klammern enthalten
REM (z. B. "Ordner (1)"). Deshalb werden Pfade NIE mit %VAR% innerhalb eines
REM Klammer-Blocks "if ... ( ... )" ausgegeben - die schliessende Klammer aus
REM dem Pfad wuerde den Block vorzeitig beenden und das Skript abstuerzen
REM lassen. Stattdessen: Sprungmarken (goto) und verzoegerte Aufloesung (!VAR!).
REM ---------------------------------------------------------------------------
setlocal enableextensions enabledelayedexpansion
cd /d "%~dp0"

echo ============================================
echo    Finance-Tool
echo ============================================
echo.

REM --- Pfadlaenge pruefen (Windows begrenzt Pfade auf 260 Zeichen) -----------
set "PROJEKTPFAD=!CD!"
call :strlen PATHLEN "!PROJEKTPFAD!"
if not defined PATHLEN set "PATHLEN=0"
if !PATHLEN! GTR 100 goto :pfad_warnung
goto :pfad_ok

:pfad_warnung
echo [WARNUNG] Der Projektpfad ist sehr lang - !PATHLEN! Zeichen:
echo    !PROJEKTPFAD!
echo.
echo Windows begrenzt Pfade auf 260 Zeichen. Bei so langen Pfaden kann die
echo Installation von Streamlit fehlschlagen.
echo EMPFEHLUNG: Ordner an einen kurzen Ort verschieben, z. B. C:\Finance-Tool,
echo danach den Unterordner ".venv" loeschen und run.bat erneut starten.
echo.

:pfad_ok
REM --- Python-Interpreter finden (erst py-Launcher, dann python) -------------
REM Bewusst ohne "&&"-Verkettung: die Bindung von && an ein if ist in cmd
REM mehrdeutig und kann die Erkennung still verfaelschen.
set "PY="
py -3 --version >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if defined PY goto :python_ok
python --version >nul 2>&1
if not errorlevel 1 set "PY=python"
if defined PY goto :python_ok
goto :kein_python

:python_ok
echo Verwende Python: !PY!

REM --- Virtuelle Umgebung anlegen -------------------------------------------
if exist ".venv\Scripts\python.exe" goto :venv_da
echo Erstelle virtuelle Umgebung ...
!PY! -m venv .venv
if errorlevel 1 goto :venv_fehler
if not exist ".venv\Scripts\python.exe" goto :venv_fehler

:venv_da
set "VENV_PY=.venv\Scripts\python.exe"

REM --- Abhaengigkeiten installieren (nur beim ersten Mal) -------------------
if exist ".venv\.installed" goto :start
echo Installiere Abhaengigkeiten ... das kann beim ersten Mal einige Minuten dauern.
"!VENV_PY!" -m pip install --upgrade pip
"!VENV_PY!" -m pip install -r requirements.txt
if errorlevel 1 goto :install_fehler
echo installed> ".venv\.installed"

:start
echo.
echo Starte Finance-Tool im Browser ...
echo Zum Beenden: dieses Fenster schliessen oder Strg+C druecken.
echo.
"!VENV_PY!" -m streamlit run app.py
echo.
echo Die App wurde beendet.
pause
exit /b 0

REM --- Fehlerausgaben --------------------------------------------------------
:kein_python
echo [FEHLER] Es wurde keine Python-Installation gefunden.
echo.
echo Bitte installiere Python 3 von:  https://www.python.org/downloads/
echo WICHTIG: Beim Installieren die Option "Add python.exe to PATH" anhaken.
echo Danach ein neues Fenster oeffnen und run.bat erneut starten.
echo.
pause
exit /b 1

:venv_fehler
echo [FEHLER] Die virtuelle Umgebung konnte nicht erstellt werden.
echo Loesche den Ordner ".venv" und starte run.bat erneut.
echo.
pause
exit /b 1

:install_fehler
echo [FEHLER] Installation der Abhaengigkeiten fehlgeschlagen.
echo Haeufigste Ursachen: zu langer Projektpfad oder keine Internetverbindung.
echo Verschiebe den Ordner nach C:\Finance-Tool, loesche ".venv"
echo und starte run.bat erneut.
echo.
pause
exit /b 1

REM ---------------------------------------------------------------------------
REM Hilfsroutine: Laenge einer Zeichenkette -> %~1 = Name der Ergebnisvariable
REM ---------------------------------------------------------------------------
:strlen
setlocal enabledelayedexpansion
set "s=%~2#"
set "len=0"
for %%A in (4096 2048 1024 512 256 128 64 32 16 8 4 2 1) do (
  if "!s:~%%A,1!" neq "" (
    set /a len+=%%A
    set "s=!s:~%%A!"
  )
)
endlocal & set "%~1=%len%"
goto :eof
