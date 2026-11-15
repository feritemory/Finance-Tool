# ---------------------------------------------------------------------------
# Baut das Finance-Tool fuer Windows: Tests -> Programm -> Selbsttest -> Installer.
#
# Aufruf (PowerShell, im Projektordner):
#     powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
#
# Ergebnis:  dist\Finance-Tool-Setup-<Version>.exe
#
# Gebaut wird in einem KURZEN Arbeitsordner (Standard: %TEMP%\ftb), weil Windows
# Pfade auf 260 Zeichen begrenzt und die Qt-/scikit-learn-Dateien sonst in tief
# verschachtelten Projektordnern daran scheitern.
#
# Hinweis: Diese Datei enthaelt absichtlich keine Umlaute, damit sie auch
# Windows PowerShell 5 (liest Skripte ohne BOM als ANSI) korrekt einliest.
# ---------------------------------------------------------------------------
param(
    [string]$Arbeitsordner = (Join-Path $env:TEMP "ftb"),
    [switch]$OhneTests,
    [switch]$OhneInstaller
)

$ErrorActionPreference = "Stop"
$Projekt = Split-Path $PSScriptRoot -Parent
Set-Location $Projekt

function Schritt($text) { Write-Host ""; Write-Host "==> $text" -ForegroundColor Cyan }
function Pruefe($was) { if ($LASTEXITCODE -ne 0) { throw "$was fehlgeschlagen (Exitcode $LASTEXITCODE)" } }

$Version = (Select-String -Path "finance\__init__.py" -Pattern '__version__ = "(.+)"').Matches[0].Groups[1].Value
Schritt "Finance-Tool $Version - Arbeitsordner: $Arbeitsordner"
New-Item -ItemType Directory -Force -Path $Arbeitsordner | Out-Null

# --- Python-Umgebung -------------------------------------------------------
$Venv = Join-Path $Arbeitsordner "venv"
$Py = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path $Py)) {
    Schritt "Lege Python-Umgebung an"
    $basis = $null
    foreach ($kandidat in @("py -3.13", "py -3", "python")) {
        $teile = $kandidat.Split(" ")
        try {
            & $teile[0] $teile[1..9] --version *> $null
            if ($LASTEXITCODE -eq 0) { $basis = $teile; break }
        } catch { }
    }
    if (-not $basis) { throw "Kein Python 3 gefunden. Bitte von https://www.python.org installieren." }
    & $basis[0] $basis[1..9] -m venv $Venv
    Pruefe "venv"
}

Schritt "Installiere Abhaengigkeiten"
& $Py -m pip install --upgrade pip --quiet
& $Py -m pip install -r requirements-build.txt --quiet
Pruefe "pip install"

# --- Tests -------------------------------------------------------------------
if (-not $OhneTests) {
    Schritt "Tests"
    $env:QT_QPA_PLATFORM = "offscreen"
    & $Py -m pytest tests -q -p no:cacheprovider
    Pruefe "Tests"
    Remove-Item Env:\QT_QPA_PLATFORM
}

# --- Programm bauen ------------------------------------------------------------
Schritt "Baue Programm (PyInstaller)"
$Dist = Join-Path $Arbeitsordner "dist"
$Build = Join-Path $Arbeitsordner "build"
& $Py -m PyInstaller --noconfirm --clean --distpath $Dist --workpath $Build packaging\finance-tool.spec
Pruefe "PyInstaller"
$Exe = Join-Path $Dist "Finance-Tool\Finance-Tool.exe"
if (-not (Test-Path $Exe)) { throw "Programm wurde nicht erzeugt: $Exe" }

# --- Selbsttest des fertigen Programms -------------------------------------------
Schritt "Selbsttest des gebauten Programms"
New-Item -ItemType Directory -Force -Path "dist" | Out-Null
$Bericht = Join-Path $Projekt "dist\selbsttest.txt"
Remove-Item $Bericht -ErrorAction SilentlyContinue
$prozess = Start-Process -FilePath $Exe -ArgumentList @("--selbsttest", "`"$Bericht`"") -Wait -PassThru
if (Test-Path $Bericht) { Get-Content $Bericht -Encoding UTF8 | Write-Host }
if ($prozess.ExitCode -ne 0) { throw "Selbsttest fehlgeschlagen (Exitcode $($prozess.ExitCode))" }

$groesse = (Get-ChildItem (Join-Path $Dist "Finance-Tool") -Recurse | Measure-Object Length -Sum).Sum / 1MB
Write-Host ("Programmordner: {0:N0} MB" -f $groesse)

# --- Installer -------------------------------------------------------------------
if (-not $OhneInstaller) {
    Schritt "Erzeuge Installer (Inno Setup)"
    $Iscc = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $Iscc) {
        throw "Inno Setup 6 nicht gefunden. Installieren von https://jrsoftware.org/isdl.php (oder: winget install JRSoftware.InnoSetup)"
    }
    $Ausgabe = Join-Path $Projekt "dist"
    & $Iscc "/DAppVersion=$Version" "/DQuelle=$(Join-Path $Dist 'Finance-Tool')" "/DAusgabe=$Ausgabe" packaging\installer.iss
    Pruefe "Inno Setup"
    $Setup = Join-Path $Ausgabe "Finance-Tool-Setup-$Version.exe"
    Write-Host ("Installer: {0}  ({1:N0} MB)" -f $Setup, ((Get-Item $Setup).Length / 1MB)) -ForegroundColor Green
}
