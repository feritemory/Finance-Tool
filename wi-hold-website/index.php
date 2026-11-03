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
    .rechtlich { margin-bottom: 24px; }
    #datenschutz { margin-top: 40px; padding-top: 32px; border-top: 1px solid var(--linie); }
    #datenschutz ul { margin: 4px 0 8px; padding-left: 20px; }
    #datenschutz p { margin-bottom: 8px; }
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

  <footer>
    <div class="wrap">
      <p class="rechtlich"><a href="#impressum">Impressum</a> &middot; <a href="#datenschutz">Datenschutzerklärung</a></p>

      <section id="impressum">
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

      </section>

      <!-- ============================================================
           DATENSCHUTZERKLÄRUNG
           Platzhalter in [eckigen Klammern] ersetzen und vor Veröffentlichung
           vom Datenschutzbeauftragten / der Rechtsabteilung prüfen lassen.
           ============================================================ -->
      <section id="datenschutz">
        <h2>Datenschutzerklärung</h2>

        <h3>1. Verantwortlicher</h3>
        <p>Verantwortlich für die Datenverarbeitung auf dieser Website im Sinne der Datenschutz-Grundverordnung (DSGVO) ist die Meyer Werft Beteiligungsgesellschaft GmbH (Kontaktdaten siehe <a href="#impressum">Impressum</a>).</p>

        <h3>2. Datenschutzbeauftragter</h3>
        <p>[Name bzw. Stelle des Datenschutzbeauftragten], E-Mail: <a href="mailto:[datenschutz@…]">[datenschutz@…]</a><br>
        <!-- Falls kein Datenschutzbeauftragter benannt ist, diesen Abschnitt löschen. -->
        </p>

        <h3>3. Allgemeines</h3>
        <p>Diese Website dient ausschließlich der Bereitstellung von Corporate Governance Reports zum Download. Wir setzen <strong>keine Cookies</strong>, <strong>keine Analyse- oder Tracking-Werkzeuge</strong> und <strong>keine externen Dienste</strong> (z.&nbsp;B. eingebundene Schriftarten, Karten oder Videos) ein. Es gibt kein Kontaktformular und keine Registrierung.</p>

        <h3>4. Hosting</h3>
        <p>Diese Website wird bei der webgo GmbH, [Anschrift der webgo GmbH], gehostet. Der Hoster verarbeitet die unter Ziffer&nbsp;5 genannten Daten in unserem Auftrag. Mit dem Hoster besteht ein Vertrag zur Auftragsverarbeitung gemäß Art.&nbsp;28 DSGVO. Die Server befinden sich in Deutschland.</p>

        <h3>5. Server-Logfiles</h3>
        <p>Bei jedem Aufruf dieser Website werden durch den Webserver automatisch folgende Daten erfasst und in sogenannten Server-Logfiles gespeichert:</p>
        <ul>
          <li>IP-Adresse des anfragenden Geräts</li>
          <li>Datum und Uhrzeit des Zugriffs</li>
          <li>Name und URL der abgerufenen Datei</li>
          <li>übertragene Datenmenge und Statuscode (z.&nbsp;B. erfolgreich / nicht gefunden)</li>
          <li>Browsertyp und -version, Betriebssystem</li>
          <li>Referrer-URL (zuvor besuchte Seite)</li>
        </ul>
        <p>Die Verarbeitung ist technisch erforderlich, um die Website auszuliefern sowie ihre Sicherheit und Stabilität zu gewährleisten. Rechtsgrundlage ist Art.&nbsp;6 Abs.&nbsp;1 lit.&nbsp;f DSGVO; unser berechtigtes Interesse liegt im sicheren und fehlerfreien Betrieb der Website. Die Logfiles werden nach [7] Tagen gelöscht. Eine Zusammenführung mit anderen Datenquellen oder eine Auswertung zu Marketingzwecken findet nicht statt.</p>

        <h3>6. Kontaktaufnahme per E-Mail</h3>
        <p>Wenn Sie uns per E-Mail kontaktieren, verarbeiten wir Ihre E-Mail-Adresse und die von Ihnen mitgeteilten Angaben, um Ihre Anfrage zu beantworten. Rechtsgrundlage ist Art.&nbsp;6 Abs.&nbsp;1 lit.&nbsp;f DSGVO (berechtigtes Interesse an der Bearbeitung von Anfragen) bzw. Art.&nbsp;6 Abs.&nbsp;1 lit.&nbsp;b DSGVO, sofern Ihre Anfrage auf einen Vertragsabschluss abzielt. Die Daten werden gelöscht, sobald sie für die Bearbeitung nicht mehr erforderlich sind und keine gesetzlichen Aufbewahrungspflichten entgegenstehen.</p>

        <h3>7. SSL-/TLS-Verschlüsselung</h3>
        <p>Diese Website nutzt aus Sicherheitsgründen eine SSL-/TLS-Verschlüsselung. Eine verschlüsselte Verbindung erkennen Sie an „https://“ und dem Schloss-Symbol in der Adresszeile Ihres Browsers.</p>

        <h3>8. Ihre Rechte</h3>
        <p>Sie haben gegenüber uns hinsichtlich der Sie betreffenden personenbezogenen Daten folgende Rechte:</p>
        <ul>
          <li>Recht auf Auskunft (Art.&nbsp;15 DSGVO)</li>
          <li>Recht auf Berichtigung (Art.&nbsp;16 DSGVO)</li>
          <li>Recht auf Löschung (Art.&nbsp;17 DSGVO)</li>
          <li>Recht auf Einschränkung der Verarbeitung (Art.&nbsp;18 DSGVO)</li>
          <li>Recht auf Datenübertragbarkeit (Art.&nbsp;20 DSGVO)</li>
          <li><strong>Widerspruchsrecht</strong> (Art.&nbsp;21 DSGVO): Sie können der Verarbeitung Ihrer Daten, die auf Art.&nbsp;6 Abs.&nbsp;1 lit.&nbsp;f DSGVO beruht, aus Gründen, die sich aus Ihrer besonderen Situation ergeben, jederzeit widersprechen.</li>
        </ul>
        <p>Zur Ausübung Ihrer Rechte genügt eine formlose Nachricht an die im Impressum genannte E-Mail-Adresse.</p>

        <h3>9. Beschwerderecht bei einer Aufsichtsbehörde</h3>
        <p>Sie haben das Recht, sich bei einer Datenschutz-Aufsichtsbehörde zu beschweren. Für uns zuständig ist: [Die Landesbeauftragte für den Datenschutz Niedersachsen, Prinzenstraße 5, 30159 Hannover]<!-- Nur korrekt, wenn der Firmensitz in Niedersachsen liegt. --></p>

        <p class="copy">Stand: [November 2026]</p>
      </section>

      <p class="copy">&copy; <?= date('Y') ?> Meyer Werft Beteiligungsgesellschaft GmbH</p>
    </div>
  </footer>

</body>
</html>
