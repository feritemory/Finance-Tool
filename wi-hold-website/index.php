<?php
/*
 * Website der Meyer Werft Beteiligungsgesellschaft GmbH (wi-hold.de)
 *
 * Reports hinzufügen: Einfach eine PDF-Datei in den Ordner "berichte/" hochladen.
 * Dateiname MUSS die Jahreszahl enthalten, z. B.:
 *     Corporate-Governance-Report-2025.pdf
 *     Corporate-Governance-Report-2026.pdf
 * Die Liste auf der Website aktualisiert sich automatisch (neuestes Jahr oben).
 */

$berichte = [];
foreach (glob(__DIR__ . '/berichte/*.pdf') ?: [] as $pfad) {
    $datei = basename($pfad);
    $jahr  = preg_match('/(20\d{2})/', $datei, $m) ? $m[1] : '';
    $berichte[] = [
        'datei' => $datei,
        'jahr'  => $jahr,
        'groesse' => round(filesize($pfad) / 1024 / 1024, 1),
    ];
}
usort($berichte, fn($a, $b) => strcmp($b['jahr'] . $b['datei'], $a['jahr'] . $a['datei']));

function h($s) { return htmlspecialchars($s, ENT_QUOTES, 'UTF-8'); }
?>
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Meyer Werft Beteiligungsgesellschaft GmbH – Corporate Governance</title>
  <meta name="description" content="Corporate Governance Reports der Meyer Werft Beteiligungsgesellschaft GmbH zum Download.">
  <style>
    :root {
      --blau: #0b2a4a;
      --akzent: #1f6fb2;
      --text: #1d1d1f;
      --grau: #5f6368;
      --linie: #dfe3e8;
      --hinter: #f5f7fa;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: var(--text);
      background: #fff;
      line-height: 1.6;
    }
    .wrap { max-width: 860px; margin: 0 auto; padding: 0 20px; }
    header { background: var(--blau); color: #fff; padding: 28px 0; }
    header h1 { margin: 0; font-size: 1.5rem; font-weight: 600; }
    header p { margin: 4px 0 0; opacity: .8; font-size: .95rem; }
    main { padding: 48px 0; }
    h2 { font-size: 1.3rem; color: var(--blau); margin: 0 0 8px; }
    .intro { color: var(--grau); margin: 0 0 28px; }
    ul.reports { list-style: none; margin: 0; padding: 0; border-top: 1px solid var(--linie); }
    ul.reports li {
      display: flex; align-items: center; justify-content: space-between; gap: 16px;
      padding: 16px 4px; border-bottom: 1px solid var(--linie);
    }
    .titel { font-weight: 600; }
    .meta { color: var(--grau); font-size: .85rem; }
    a.download {
      flex-shrink: 0; text-decoration: none; color: #fff; background: var(--akzent);
      padding: 8px 16px; border-radius: 4px; font-size: .9rem;
    }
    a.download:hover, a.download:focus { background: var(--blau); }
    .leer { color: var(--grau); font-style: italic; }
    footer { background: var(--hinter); border-top: 1px solid var(--linie); padding: 40px 0; font-size: .9rem; }
    footer h2 { font-size: 1.1rem; }
    footer h3 { font-size: .95rem; margin: 20px 0 4px; color: var(--blau); }
    footer p { margin: 0 0 4px; }
    footer a { color: var(--akzent); }
    .copy { margin-top: 28px; color: var(--grau); font-size: .8rem; }
  </style>
</head>
<body>

  <header>
    <div class="wrap">
      <h1>Meyer Werft Beteiligungsgesellschaft GmbH</h1>
      <p>Corporate Governance</p>
    </div>
  </header>

  <main>
    <div class="wrap">
      <h2>Corporate Governance Reports</h2>
      <p class="intro">Hier finden Sie die Corporate Governance Reports der Meyer Werft Beteiligungsgesellschaft GmbH als PDF zum Download.</p>

      <?php if (empty($berichte)): ?>
        <p class="leer">Derzeit sind keine Berichte verfügbar.</p>
      <?php else: ?>
        <ul class="reports">
          <?php foreach ($berichte as $b): ?>
            <li>
              <div>
                <div class="titel">Corporate Governance Report<?= $b['jahr'] ? ' ' . h($b['jahr']) : '' ?></div>
                <div class="meta">PDF, <?= h(str_replace('.', ',', (string)$b['groesse'])) ?> MB</div>
              </div>
              <a class="download" href="berichte/<?= h(rawurlencode($b['datei'])) ?>" download>Herunterladen</a>
            </li>
          <?php endforeach; ?>
        </ul>
      <?php endif; ?>
    </div>
  </main>

  <footer id="impressum">
    <div class="wrap">
      <h2>Impressum</h2>

      <h3>Angaben gemäß § 5 DDG</h3>
      <p>Meyer Werft Beteiligungsgesellschaft GmbH</p>
      <p>[Straße Hausnummer]</p>
      <p>[PLZ Ort]</p>

      <h3>Vertreten durch die Geschäftsführung</h3>
      <p>[Vorname Nachname], [Vorname Nachname]</p>

      <h3>Kontakt</h3>
      <p>Telefon: [+49 …]</p>
      <p>E-Mail: <a href="mailto:[info@wi-hold.de]">[info@wi-hold.de]</a></p>

      <h3>Registereintrag</h3>
      <p>Registergericht: Amtsgericht [Ort]</p>
      <p>Registernummer: HRB [Nummer]</p>

      <h3>Umsatzsteuer-ID</h3>
      <p>Umsatzsteuer-Identifikationsnummer gemäß § 27a UStG: [DE…]</p>

      <p class="copy">&copy; <?= date('Y') ?> Meyer Werft Beteiligungsgesellschaft GmbH</p>
    </div>
  </footer>

</body>
</html>
