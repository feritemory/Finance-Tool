# wi-hold.de – Corporate-Governance-Website

Minimale Website der Meyer Werft Beteiligungsgesellschaft GmbH.

| Datei | Zweck |
|---|---|
| `index.php` | Startseite: listet automatisch alle PDFs aus `berichte/` + Impressum + Datenschutzerklärung |
| `berichte/` | Hier die Reports hochladen, z. B. `Corporate-Governance-Report-2025.pdf` |
| `.htaccess` | Verhindert Ordner-Auflistungen |

**Neuen Report veröffentlichen:** PDF per FTP / webgo-Dateimanager in `berichte/` hochladen.
Der Dateiname muss die Jahreszahl enthalten. Sonst ist nichts zu ändern.

**Impressum & Datenschutz:** In `index.php` die Platzhalter in eckigen Klammern `[...]` ersetzen.
