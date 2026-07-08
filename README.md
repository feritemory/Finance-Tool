# 💶 Finance-Tool

Eine schlanke, **lokal laufende** Desktop-App, um Einnahmen und Ausgaben zu
**tracken, kategorisieren und visualisieren** – täglich, monatlich und jährlich.
Zusätzlich ermittelt das Tool automatisch deine **monatlichen Fixkosten**.

Die App läuft komplett auf deinem Rechner (Streamlit im Browser). Deine echten
Umsätze werden lokal in einer SQLite-Datenbank gespeichert und **nie** ins
Internet hochgeladen.

---

## Schnellstart

### macOS / Linux
```bash
./run.sh
```

### Windows
```bat
run.bat
```

Beim ersten Start wird automatisch eine virtuelle Umgebung angelegt, alle
Abhängigkeiten installiert und die App im Browser geöffnet
(http://localhost:8501). Beim allerersten Start werden **Demo-Daten ab
Januar 2026** geladen, damit du sofort etwas siehst.

> Alternativ manuell:
> ```bash
> python3 -m venv .venv && source .venv/bin/activate
> pip install -r requirements.txt
> streamlit run app.py
> ```

### Problembehebung (Windows)

**Das `cmd`-Fenster öffnet sich und schließt sich sofort wieder?**
Das passiert, wenn ein Fehler auftritt (meist: Python nicht installiert oder
nicht im PATH). Das aktuelle `run.bat` fängt das ab und bleibt mit einer
Meldung offen. Falls es dennoch sofort schließt, öffne die Eingabeaufforderung
manuell und starte es von Hand, damit die Meldung stehen bleibt:

1. `Windows-Taste` drücken, `cmd` eingeben, Enter.
2. In den Projektordner wechseln (Pfad anpassen):
   ```bat
   cd /d "C:\Pfad\zu\Finance-Tool"
   run.bat
   ```

**„Python was not found" / es öffnet sich der Microsoft Store?**
Dann ist Python nicht (richtig) installiert:
1. Python 3 von <https://www.python.org/downloads/> installieren.
2. Im Installer unbedingt **„Add python.exe to PATH"** anhaken.
3. Danach cmd-Fenster neu öffnen und `run.bat` erneut ausführen.

**Fehler „Could not install packages due to an OSError … No such file or
directory" beim Installieren von Streamlit/altair?**
Das ist die **260-Zeichen-Pfadgrenze** von Windows. Dein Projektordner liegt zu
tief verschachtelt (z. B. `C:\Users\...\Finance-Tool-claude-...\Finance-Tool-claude-...\`),
und die tief verschachtelten Streamlit-Dateien sprengen dann das Limit.

Lösung:
1. Ordner an einen **kurzen** Pfad verschieben, z. B. `C:\Finance-Tool`.
2. Darin den (kaputten) Unterordner `.venv` löschen.
3. `run.bat` erneut starten.

`run.bat` warnt inzwischen selbst, wenn der Pfad zu lang ist. Alternativ kannst
du in Windows die lange Pfadunterstützung aktivieren (Administrator-PowerShell):
```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
  -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```
Danach den Rechner neu starten.

**Installation hängt oder schlägt fehl?** Lösche den Ordner `.venv` und starte
`run.bat` erneut – er baut die Umgebung dann neu auf.

---

## Funktionen

| Bereich | Beschreibung |
|---|---|
| **📊 Übersicht** | Kennzahlen (Einnahmen, Ausgaben, Sparen, Saldo, Fixkosten), Einnahmen-vs-Ausgaben-Verlauf, Kategorien-Tortendiagramm, gestapelter Kategorienverlauf. Umschaltbar zwischen **täglich / monatlich / jährlich**. |
| **🔁 Fixkosten** | Automatische Erkennung wiederkehrender Zahlungen (Miete, Abos, Sparpläne …) und Summe der monatlichen Fixkosten. |
| **📋 Transaktionen** | Alle Umsätze durchsuchen; Kategorie oder Fixkosten-Kennzeichen pro Buchung manuell korrigieren. |
| **📥 Import** | CSV-/CAMT-Import (Consorsbank & andere Banken) + optionaler automatischer Kontoabruf per PSD2. |
| **⚙️ Einstellungen** | Regeln neu anwenden, Demo-Daten laden, alles zurücksetzen, Export als CSV. |

### Kategorien
1. Lebensmittel
2. Auswärts Essen und Trinken
3. Shoppen
4. Freizeit
5. Reisen
6. Wohnkosten inkl. Internet und Handykosten
7. Sport
8. Gehalt *(Einnahme)*
9. Bafög *(Einnahme)*
10. Überweisung an Sparkonten (Trade Republic & Revolut) *(Sparen)*

Zusätzlich gibt es die Auffang-Kategorie **Sonstiges**. Die Zuordnung erfolgt
automatisch über Stichwort-Regeln in [`config/rules.yaml`](config/rules.yaml) –
diese Datei kannst du beliebig erweitern. Nach einer Änderung in den
**Einstellungen** auf *„Regeln neu anwenden"* klicken (manuell gesetzte
Kategorien bleiben erhalten).

---

## Umsätze aus der Consorsbank importieren

Es gibt zwei Wege. Die **Consorsbank bietet keine zuverlässige FinTS/HBCI-
Schnittstelle** für Drittsoftware, daher sind das die praktikablen Optionen:

### Weg 1 – CSV/CAMT-Export (empfohlen, sofort nutzbar)
1. Im Consorsbank-Online-Banking bzw. in der App unter **Umsätze** den Zeitraum
   wählen.
2. Umsätze als **CSV** (oder CAMT/XML) exportieren.
3. Im Tab **📥 Import** die Datei(en) hochladen.

Der Import erkennt Duplikate automatisch (per Prüfsumme aus Datum, Betrag,
Empfänger, Verwendungszweck), du kannst also gefahrlos überlappende Zeiträume
laden. Der CSV-Parser versteht das deutsche Zahlen- und Datumsformat und erkennt
die Spalten flexibel – funktioniert daher auch mit Exporten von Sparkasse, DKB,
ING u. a.

**Speziell auf den Consorsbank-Export abgestimmt:**
- Der mehrzeilige Vorspann ("Allgemeine Informationen", "Kontostand" …) wird
  übersprungen; die eigentliche Umsatz-Kopfzeile wird automatisch gefunden.
- **Vorgemerkte** Umsätze (Spalte *Valuta = „vorgemerkt"*) werden ausgelassen,
  da sie noch nicht final gebucht sind und sonst doppelt zählen würden.
- Überträge auf **Trade Republic** und **Revolut** laufen bei der Consorsbank
  oft nur als „Dauerauftrag" ohne erkennbaren Namen – sie werden über die
  **BIC** (`TRBKDEBB` bzw. `REVODEB2`) automatisch der Kategorie
  *Überweisung an Sparkonten* zugeordnet.
- Durch Zeilenumbrüche zerrissene Wörter im Verwendungszweck (z. B.
  „Urban Sp orts") werden bei der Kategorisierung wieder zusammengesetzt.

Einnahme vs. Ausgabe wird am **Vorzeichen** des Betrags festgemacht: Jeder
Geldeingang (auch Steuererstattungen oder Rückzahlungen von Freunden) zählt als
Eingang. Lokale Kartenzahlungen, Bargeldabhebungen und PayPal-Zahlungen lassen
sich nicht immer automatisch zuordnen und landen in *Sonstiges* – im Tab
**📋 Transaktionen** kannst du sie mit einem Klick dauerhaft umkategorisieren.

**Halb-automatisieren:** Lade dir einmal im Monat den CSV-Export herunter (bei
der Consorsbank per E-Mail-Benachrichtigung an neue Umsätze erinnern lassen) und
ziehe ihn in den Import-Tab. Zwei Klicks pro Monat.

### Weg 2 – Automatischer Kontoabruf per PSD2 (optional)
Über die **kostenlose** API [GoCardless Bank Account Data](https://bankaccountdata.gocardless.com/)
(früher Nordigen) lassen sich Umsätze direkt und PSD2-konform abrufen – die
Consorsbank wird unterstützt.

1. Kostenloses Konto anlegen unter <https://bankaccountdata.gocardless.com/>.
2. Unter *User Secrets* eine **Secret ID** und einen **Secret Key** erzeugen.
3. Entweder als Umgebungsvariablen setzen …
   ```bash
   export GOCARDLESS_SECRET_ID=...
   export GOCARDLESS_SECRET_KEY=...
   ```
   … oder direkt im Import-Tab unter *„Automatischer Kontoabruf"* eingeben.
4. **Bank-Login-Link erzeugen** → einmalig bei der Consorsbank anmelden und den
   Zugriff bestätigen → **Umsätze abrufen**.

> Hinweis: Aus regulatorischen Gründen (SCA) gilt eine Zustimmung **90 Tage**;
> danach ist eine erneute Anmeldung nötig. Für diesen Weg wird zusätzlich das
> Paket `requests` benötigt (ist in `requirements.txt` enthalten).

---

## Projektstruktur

```
Finance-Tool/
├── app.py                  # Streamlit-Oberfläche (Tabs, Diagramme)
├── finance/
│   ├── categories.py       # Kategorie-Definitionen (Typ, Farbe, Fixkosten)
│   ├── categorize.py       # Regelbasierte Auto-Kategorisierung
│   ├── importer.py         # CSV-/CAMT-Parser (deutsche Zahlen/Daten, Duplikate)
│   ├── storage.py          # SQLite-Persistenz
│   ├── analytics.py        # Aggregationen + Fixkosten-Erkennung
│   ├── sampledata.py       # Demo-Daten ab 2026
│   └── banking/
│       └── gocardless.py   # optionaler PSD2-Kontoabruf
├── config/rules.yaml       # Stichwort-Regeln (frei anpassbar)
├── data/                   # lokale SQLite-DB (nicht im Git)
└── requirements.txt
```

---

## Datenschutz
Alle Daten bleiben lokal in `data/finance.db`. Diese Datei sowie CSV-Dateien im
`data/`-Ordner sind über `.gitignore` vom Versionskontroll-Upload ausgeschlossen.

## Anpassen
- **Kategorien-Regeln:** [`config/rules.yaml`](config/rules.yaml)
- **Fixkosten-Empfindlichkeit:** Parameter `min_months`, `max_cv`,
  `max_per_month` in `finance/analytics.py` → `detect_recurring()`.
- **Farben der Diagramme:** `finance/categories.py`.
