# 💶 Finance-Tool

Eine schlanke, **lokal laufende** Desktop-App, um Einnahmen und Ausgaben zu
**tracken, kategorisieren und visualisieren** – täglich, monatlich und jährlich.
Zusätzlich ermittelt das Tool automatisch deine **monatlichen Fixkosten**.

Das Programm läuft **vollständig auf deinem Rechner** – in einem eigenen Fenster,
ohne Browser-Tab und ohne Terminal. Deine Umsätze liegen lokal in einer
SQLite-Datenbank und werden **nie** ins Internet übertragen. Der interne Server
lauscht ausschliesslich auf `127.0.0.1` und ist von aussen nicht erreichbar.

---

## Schnellstart

### Windows
Doppelklick auf **`Finance-Tool.bat`**

### macOS / Linux
Doppelklick auf **`Finance-Tool.command`** – oder im Terminal:
```bash
./Finance-Tool.command
```

Beim ersten Start werden eine virtuelle Umgebung angelegt und alle
Abhängigkeiten installiert (das dauert einige Minuten). Danach öffnet sich das
Programm in wenigen Sekunden in einem eigenen Fenster.

> **Verknüpfung auf dem Desktop:** Rechtsklick auf `Finance-Tool.bat` →
> *Senden an* → *Desktop (Verknüpfung erstellen)*. Über *Eigenschaften* lässt
> sich der Verknüpfung auch ein eigenes Symbol geben.

Beim allerersten Start ist die Datenbank leer – lade deine Umsätze im Bereich
**Import** hoch. Zum Ausprobieren gibt es unter **Einstellungen** Demo-Daten.

> Alternativ manuell:
> ```bash
> python3 -m venv .venv && source .venv/bin/activate
> pip install -r requirements.txt
> pip install pywebview        # optional: natives Fenster
> python desktop.py
> ```
> Ohne `pywebview` startet das Programm ersatzweise im Standardbrowser –
> alle Funktionen bleiben identisch.

### Aufbau

Die Oberfläche ist eine eigenständige HTML/CSS/JS-Anwendung (`webui/`), die von
einem lokalen Flask-Server (`finance/server.py`) bedient wird. Die Diagramme
sind selbst gezeichnetes SVG – es werden **keine externen Bibliotheken oder
Web-Ressourcen** geladen, das Programm funktioniert vollständig offline.

> Die frühere **Streamlit-Oberfläche** bleibt als Alternative erhalten
> (`run.bat` / `./run.sh` bzw. `streamlit run app.py`). Beide greifen auf
> dieselbe Datenbank und dieselbe Logik zu.

### Problembehebung (Windows)

**Klammern im Ordnernamen** (z. B. `Finance-Tool (1)`) haben `run.bat` früher
sofort abstürzen lassen: Eine schließende Klammer aus dem Pfad beendete in
`cmd` einen `if (...)`-Block vorzeitig. Das ist behoben – der Ablauf kommt ohne
solche Blöcke aus. Ordnernamen mit Klammern sind also unproblematisch.

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
| **📊 Übersicht** | Summen im Zeitraum **und Durchschnitt pro Monat** (Ø Einnahmen, Ø Ausgaben, davon Fixkosten, Ø Sparen – gemittelt nur über vollständige Monate). Einnahmen/Ausgaben/Sparen als **gruppierte Balken nebeneinander** (alle positiv, eine gemeinsame Achse), Saldo-Verlauf, Ausgaben je Kategorie, gestapelter Kategorienverlauf. Umschaltbar zwischen **täglich / monatlich / jährlich**. |
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
10. Sonstige Einnahmen *(Einnahme – Erstattungen, Überweisungen, PayPal …)*
11. Überweisung an Sparkonten (Trade Republic & Revolut) *(Sparen)*

Einnahme vs. Ausgabe richtet sich nach dem **Vorzeichen**: Ein Geldeingang, der
keiner Einnahmen-Regel entspricht (z. B. Steuererstattung, Rückzahlung von
Freunden), wird als **Sonstige Einnahmen** geführt – nicht als Ausgabe.
Gehälter werden am Buchungstag (bei Zahlung am letzten Werktag automatisch dem
richtigen Monat) zugeordnet.

Zusätzlich gibt es die Auffang-Kategorie **Sonstiges**. Die Zuordnung erfolgt
automatisch über Stichwort-Regeln in [`config/rules.yaml`](config/rules.yaml) –
diese Datei kannst du beliebig erweitern. Nach einer Änderung in den
**Einstellungen** auf *„Regeln neu anwenden"* klicken (manuell gesetzte
Kategorien bleiben erhalten).

#### Selbstlernende Kategorisierung
Wie bei Apps à la Finanzguru **lernt das Tool aus deinen Korrekturen**: Sobald du
im Tab *📋 Transaktionen* die Kategorie einer Buchung änderst, merkt sich das
Tool den Händler und ordnet **alle weiteren und künftigen** Buchungen desselben
Händlers automatisch genauso ein. Die Erkennung berücksichtigt dabei auch die
BIC (damit z. B. Trade-Republic-/Revolut-Daueraufträge ohne Namen korrekt als
*Überweisung an Sparkonten* erkannt werden) und setzt von der Bank durch
Zeilenumbruch zerrissene Händlernamen wieder zusammen. Gelernte Regeln lassen
sich in den **Einstellungen** einsehen und zurücksetzen.

#### Lokaler ML-Klassifikator (offline, lernt mit)
Zusätzlich gibt es ein **lokales Machine-Learning-Modell** (scikit-learn), das
aus deinen bereits kategorisierten **Ausgaben** lernt und ähnliche neue
Buchungen automatisch einordnet – z. B. erkennt es „Curry Keule" als *Auswärts*,
weil es „Curry 36" & Co. gelernt hat. Es läuft **komplett offline**; nichts
verlässt deinen Rechner.

Bedienung im Tab **⚙️ Einstellungen** → *Selbstlernende Kategorisierung (ML)*:
- **Modell trainieren & anwenden** – trainiert aus dem aktuellen Datenbestand
  (manuelle Korrekturen zählen stärker) und ordnet offene *Sonstiges*-Ausgaben zu.
- **Mindest-Sicherheit** (Schwelle) – nur Vorhersagen oberhalb der Schwelle
  werden übernommen; unsichere Fälle bleiben bewusst *Sonstiges*.
- Je mehr du korrigierst und neu trainierst, desto besser wird es.

Reihenfolge der Zuordnung: **1.** gelernte Korrekturen → **2.** Stichwort-Regeln
→ **3.** ML-Modell (nur Ausgaben, nur bei hoher Sicherheit) → sonst *Sonstiges*.

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
├── Finance-Tool.bat        # Start unter Windows (Doppelklick)
├── Finance-Tool.command    # Start unter macOS/Linux
├── desktop.py              # startet Server + eigenes Fenster
├── webui/                  # Oberfläche (HTML/CSS/JS, SVG-Diagramme)
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   └── charts.js
├── app.py                  # optionale Streamlit-Oberfläche
├── finance/
│   ├── server.py           # lokaler Flask-Server (JSON-Schnittstelle)
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
