# Finance-Tool

Ein eigenständiges **Windows-Programm** (Windows 10 und neuer), um Einnahmen und
Ausgaben zu **tracken, kategorisieren und visualisieren** – täglich, monatlich
und jährlich – und die monatlichen **Fixkosten** zu ermitteln. Oberfläche im
ruhigen Stil von Notion.

Das Programm wird ganz normal installiert und läuft **vollständig lokal**: kein
Browser, kein Server, keine Internetverbindung nötig. Deine Umsätze verlassen
den Rechner nie.

---

## Installation

1. Installer herunterladen: auf GitHub unter **Actions → Windows-Build →**
   neuester erfolgreicher Lauf **→ Artifacts → Finance-Tool-Setup**.
   (Das ist eine ZIP-Datei; darin liegt `Finance-Tool-Setup-<Version>.exe`.)
2. Installer starten. Es werden **keine Administratorrechte** benötigt.
3. **Windows-SmartScreen:** Da das Programm nicht kostenpflichtig signiert ist,
   meldet Windows beim ersten Start „Der Computer wurde durch Windows
   geschützt“. Auf **Weitere Informationen → Trotzdem ausführen** klicken.
4. Starten über das **Startmenü** oder die **Desktop-Verknüpfung**.

Installiert wird nach `%LOCALAPPDATA%\Programs\Finance-Tool`. Ein neuerer
Installer aktualisiert das Programm einfach; deine Daten bleiben erhalten.
**Deinstallieren:** Windows-Einstellungen → Apps → Finance-Tool.

### Daten aus der früheren Version übernehmen

Die frühere (Browser-)Version speicherte alles in `data\finance.db` im
Projektordner. Im Programm: **Einstellungen → Daten → Datenbank übernehmen …**
und diese Datei auswählen. Übernommen werden Umsätze, gelernte Händler-Regeln
und deine Fixkosten-Häkchen; die aktuelle Datenbank wird vorher gesichert.

---

## Bedienung

| Bereich | Inhalt |
|---|---|
| **Übersicht** | Summen im Zeitraum und **Durchschnitt pro Monat** (Ø Einnahmen, Ø Ausgaben, davon Fixkosten, Ø Sparen – gemittelt nur über vollständige Monate). Einnahmen/Ausgaben/Sparen als Balken nebeneinander, Saldo-Verlauf, Ausgaben je Kategorie, Kategorien im Zeitverlauf. Auflösung täglich / monatlich / jährlich. |
| **Fixkosten** | Wiederkehrende Zahlungen mit Rhythmus (monatlich, vierteljährlich …), umgerechnet auf einen Monatsbetrag; feste Sparbeträge getrennt. |
| **Transaktionen** | Alle Umsätze, durchsuch- und sortierbar. Kategorie per Klick ändern, Fixkosten per Häkchen. |
| **Import** | CSV-/CAMT-Dateien per Drag & Drop oder Dateiauswahl; optional automatischer Abruf per PSD2. |
| **Einstellungen** | Lernendes Modell trainieren, Regeln bearbeiten, Demo-Daten, Export für Excel, Datenbank übernehmen. |

Links in der Seitenleiste filterst du nach **Jahr, Monat und Kategorie** – das
gilt für alle Bereiche. Mit **Strg+1 … Strg+5** wechselst du die Bereiche.

### Kategorien

Ausgaben: Lebensmittel · Auswärts Essen und Trinken · Shoppen · Freizeit ·
Reisen · Wohnkosten inkl. Internet und Handykosten · Sport ·
**Bafög-Rückzahlung** · Sonstiges
Einnahmen: Gehalt · Sonstige Einnahmen
Sparen: Überweisung an Sparkonten (Trade Republic & Revolut)

Einnahme oder Ausgabe richtet sich nach dem **Vorzeichen**: Eine Erstattung
oder Rückzahlung von Freunden zählt als *Sonstige Einnahme*, nicht als
„negative Ausgabe“.

### Import von der Consorsbank

Im Online-Banking unter **Umsätze** als CSV exportieren und im Bereich
**Import** hineinziehen. Das Programm ist auf die Eigenheiten dieses Exports
abgestimmt:

- Der Vorspann (Kontoinformationen, Kontostand) wird übersprungen.
- **Vorgemerkte** Umsätze werden erst übernommen, wenn sie endgültig gebucht sind.
- **Duplikate** werden erkannt – überlappende Zeiträume kannst du gefahrlos laden.
- Daueraufträge an **Trade Republic** und **Revolut** werden über die BIC
  erkannt, auch wenn im Text nur „Dauerauftrag“ steht.
- Durch Zeilenumbruch zerrissene Wörter („Urban Sp orts“) werden zusammengesetzt.

### Kategorisierung, die mitlernt

Die Zuordnung läuft in drei Stufen: **1.** deine eigenen Korrekturen →
**2.** Stichwort-Regeln → **3.** ein lokales Lernmodell (nur bei hoher
Sicherheit). Änderst du unter *Transaktionen* eine Kategorie, merkt sich das
Programm den Händler und ordnet **alle weiteren und künftigen** Buchungen
genauso ein. Unter *Einstellungen* trainierst du das Lernmodell neu – je mehr
du korrigierst, desto besser wird es.

Die Stichwort-Regeln lassen sich unter **Einstellungen → Regeldatei
bearbeiten** im Editor anpassen.

### Fixkosten

Erkannt werden Empfänger mit wiederkehrendem, konstantem Betrag; häufig
besuchte Händler (Supermärkte) werden bewusst ausgeschlossen. Zahlungen, die
nur alle paar Monate anfallen (z. B. die BAföG-Rückzahlung), werden auf einen
Monatsbetrag umgerechnet. Stimmt etwas nicht, setzt oder entfernst du unter
*Transaktionen* das Häkchen **Fixkosten** – das gilt für alle Buchungen dieses
Empfängers und übersteuert die Automatik dauerhaft.

---

## Wo liegen meine Daten?

In `%APPDATA%\Finance-Tool` (Einstellungen → *Datenordner öffnen*):

| Datei | Inhalt |
|---|---|
| `finance.db` | alle Umsätze, gelernte Regeln, Fixkosten-Entscheidungen |
| `rules.yaml` | deine Stichwort-Regeln (bearbeitbar) |
| `model.pkl` | das trainierte Lernmodell |

Der Ordner bleibt bei Updates und Deinstallation erhalten. Zum Sichern genügt
es, ihn zu kopieren.

---

## Für Entwickler

```bash
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements-build.txt
python Finance-Tool.pyw                               # Programm aus dem Quellcode starten
python -m pytest tests                                # Tests
```

**Installer selbst bauen** (Windows, mit [Inno Setup 6](https://jrsoftware.org/isdl.php)):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

Das Skript führt die Tests aus, baut das Programm mit PyInstaller, startet die
fertige `.exe` im **Selbsttest** (`Finance-Tool.exe --selbsttest bericht.txt`)
und erzeugt `dist\Finance-Tool-Setup-<Version>.exe`. Dieselben Schritte laufen
bei jedem Push automatisch auf GitHub (`.github/workflows/windows-build.yml`).

```
Finance-Tool/
├── Finance-Tool.pyw          # Startdatei
├── finance/
│   ├── gui/                  # Oberfläche (PySide6/Qt)
│   │   ├── app.py            # Programmstart, Selbsttest
│   │   ├── hauptfenster.py   # Seitenleiste, Navigation, Filter
│   │   ├── seiten/           # Übersicht, Fixkosten, Transaktionen, Import, Einstellungen
│   │   ├── charts.py         # Diagramme (QPainter)
│   │   ├── theme.py          # Notion-Design (Farben, Schrift, Stylesheet)
│   │   └── widgets.py        # Kacheln, Karten, Umschalter, Hintergrund-Aufträge
│   ├── service.py            # Anwendungslogik zwischen Oberfläche und Kern
│   ├── importer.py           # CSV-/CAMT-Import (Consorsbank)
│   ├── categorize.py         # Regeln + gelernte Händler + Lernmodell
│   ├── analytics.py          # Auswertungen, Fixkosten-Erkennung
│   ├── storage.py            # SQLite-Datenbank
│   ├── ml.py                 # lokales Lernmodell (scikit-learn)
│   └── paths.py              # Speicherorte (%APPDATA%, Programmdateien)
├── config/rules.yaml         # mitgelieferte Standard-Regeln
├── assets/                   # Programmsymbol
├── packaging/                # PyInstaller-Bauanleitung, Installer-Skript
├── scripts/build_windows.ps1 # kompletter Windows-Build
└── tests/                    # Tests (Kern, Service, Oberfläche)
```
