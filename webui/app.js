/* Finance-Tool – Steuerung der Oberfläche. */

const S = {
  meta: null,
  aufloesung: 'monat',
  verlaufArt: 'ausgaben',
  filter: { jahr: 'alle', monat: 'alle', kategorie: '' },
  dateien: [],
  uebersicht: null,
};

const $  = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));
const euro = (v) => Charts.euro(v);

/* ---------------- Hilfsfunktionen ---------------- */
function toast(text, fehler = false) {
  const t = $('#toast');
  t.textContent = text;
  t.className = 'toast' + (fehler ? ' fehler' : '');
  t.hidden = false;
  clearTimeout(t._timer);
  t._timer = setTimeout(() => { t.hidden = true; }, 5200);
}

function query(extra = {}) {
  const p = new URLSearchParams();
  if (S.filter.jahr !== 'alle') p.set('jahr', S.filter.jahr);
  if (S.filter.monat !== 'alle') p.set('monat', S.filter.monat);
  if (S.filter.kategorie) p.append('kategorie', S.filter.kategorie);
  for (const [k, v] of Object.entries(extra)) p.set(k, v);
  return p.toString();
}

async function holen(pfad) {
  const r = await fetch(pfad);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

async function senden(pfad, daten) {
  const r = await fetch(pfad, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(daten || {}),
  });
  return r.json();
}

function kpi(name, wert, negativRot = false) {
  const neg = negativRot && wert < 0 ? ' neg' : '';
  return `<div class="kpi"><div class="kpi-name">${name}</div>
          <div class="kpi-wert${neg}">${euro(wert)}</div></div>`;
}

/* ---------------- Navigation ---------------- */
$$('#nav .nav-item').forEach(b => b.addEventListener('click', () => {
  $$('#nav .nav-item').forEach(x => x.classList.remove('is-active'));
  b.classList.add('is-active');
  $$('.tab').forEach(t => t.classList.remove('is-active'));
  $('#tab-' + b.dataset.tab).classList.add('is-active');
  if (b.dataset.tab === 'fixkosten') ladeFixkosten();
  if (b.dataset.tab === 'transaktionen') ladeTransaktionen();
  if (b.dataset.tab === 'einstellungen') ladeMeta();
}));

$$('#aufloesung button').forEach(b => b.addEventListener('click', () => {
  $$('#aufloesung button').forEach(x => x.classList.remove('is-active'));
  b.classList.add('is-active');
  S.aufloesung = b.dataset.wert;
  ladeUebersicht();
}));

$$('#verlauf-art button').forEach(b => b.addEventListener('click', () => {
  $$('#verlauf-art button').forEach(x => x.classList.remove('is-active'));
  b.classList.add('is-active');
  S.verlaufArt = b.dataset.wert;
  zeichneVerlauf();
}));

/* ---------------- Stammdaten & Filter ---------------- */
async function ladeMeta() {
  S.meta = await holen('/api/meta');
  const m = S.meta;

  $('#bestand').innerHTML = m.anzahl
    ? `Datenbestand: ${m.anzahl} Umsätze<br>Zeitraum: ${m.von} – ${m.bis}`
    : 'Noch keine Umsätze.';

  const jahr = $('#f-jahr');
  if (jahr.dataset.gefuellt !== String(m.jahre)) {
    jahr.innerHTML = '<option value="alle">Alle Jahre</option>' +
      m.jahre.map(j => `<option value="${j}">${j}</option>`).join('');
    jahr.dataset.gefuellt = String(m.jahre);
    jahr.value = S.filter.jahr;
  }
  fuelleMonate();

  const kat = $('#f-kategorie');
  if (!kat.dataset.gefuellt) {
    kat.innerHTML = '<option value="">Alle Kategorien</option>' +
      m.kategorien.map(k => `<option value="${k}">${k}</option>`).join('');
    kat.dataset.gefuellt = '1';
  }

  // Statuszeilen in den Einstellungen
  $('#ml-status').innerHTML = !m.ml_verfuegbar
    ? 'Das Paket <b>scikit-learn</b> fehlt – ohne es bleibt die Kategorisierung '
      + 'rein regelbasiert. Nachinstallieren mit <code>pip install scikit-learn</code>.'
    : `Das Modell lernt aus deinen bereits kategorisierten Ausgaben und ordnet
       ähnliche neue Buchungen automatisch zu. Status:
       <b>${m.ml_trainiert ? 'trainiert' : 'noch nicht trainiert'}</b>.
       Alles bleibt lokal auf deinem Rechner.`;
  $('#regel-status').innerHTML =
    `Gelernte Händler-Regeln: <b>${m.gelernte_regeln}</b> ·
     Manuelle Fixkosten-Entscheidungen: <b>${m.manuelle_fixkosten}</b>`;
  $('#daten-status').innerHTML =
    `Gespeicherte Umsätze: <b>${m.anzahl}</b> · davon Demo-Daten:
     <b>${m.demo_anzahl}</b>`;
}

function fuelleMonate() {
  const sel = $('#f-monat');
  const monate = (S.meta.monate || []).filter(
    mo => S.filter.jahr === 'alle' || mo.startsWith(S.filter.jahr));
  sel.innerHTML = '<option value="alle">Alle Monate</option>' +
    monate.map(mo => {
      const [j, m] = mo.split('-');
      return `<option value="${mo}">${m}/${j}</option>`;
    }).join('');
  sel.value = monate.includes(S.filter.monat) ? S.filter.monat : 'alle';
  S.filter.monat = sel.value;
}

$('#f-jahr').addEventListener('change', e => {
  S.filter.jahr = e.target.value; S.filter.monat = 'alle';
  fuelleMonate(); allesLaden();
});
$('#f-monat').addEventListener('change', e => {
  S.filter.monat = e.target.value; allesLaden();
});
$('#f-kategorie').addEventListener('change', e => {
  S.filter.kategorie = e.target.value; allesLaden();
});

/* ---------------- Übersicht ---------------- */
async function ladeUebersicht() {
  const d = await holen('/api/uebersicht?' + query({ aufloesung: S.aufloesung }));
  S.uebersicht = d;
  const hatDaten = d.reihen.length > 0;
  $('#u-leer').hidden = hatDaten;
  $('#u-inhalt').hidden = !hatDaten;
  if (!hatDaten) return;

  const s = d.summe, a = d.schnitt;
  $('#kpi-summe').innerHTML =
    kpi('Einnahmen', s.einnahmen) + kpi('Ausgaben', s.ausgaben) +
    kpi('Sparen', s.sparen) + kpi('Saldo', s.saldo, true);

  const n = a.monate;
  $('#kpi-schnitt-label').textContent =
    `Pro Monat · Ø über ${n} vollständige${n === 1 ? 'n' : ''} Monat${n === 1 ? '' : 'e'}`;
  $('#kpi-schnitt').innerHTML =
    kpi('Ø Einnahmen', a.einnahmen) + kpi('Ø Ausgaben', a.ausgaben) +
    kpi('davon Fixkosten', d.fixkosten_monat) + kpi('Ø Sparen', a.sparen);
  const variabel = Math.max(a.ausgaben - d.fixkosten_monat, 0);
  $('#variabel-hinweis').innerHTML = a.ausgaben > 0
    ? `Das entspricht rund <b>${euro(variabel)}</b> variablen Ausgaben pro Monat
       (Ø Ausgaben abzüglich Fixkosten).` : '';

  const perioden = d.reihen.map(r => r.label);
  const f = S.meta.serienfarben;
  Charts.gruppierteBalken($('#chart-vergleich'), {
    perioden,
    serien: [
      { name: 'Einnahmen', farbe: f.einnahmen, werte: d.reihen.map(r => r.einnahmen) },
      { name: 'Ausgaben',  farbe: f.ausgaben,  werte: d.reihen.map(r => r.ausgaben) },
      { name: 'Sparen',    farbe: f.sparen,    werte: d.reihen.map(r => r.sparen) },
    ],
    beschriften: perioden.length <= 14,
  });

  $('#tabelle-reihen').innerHTML = `
    <div class="tabellen-rahmen"><table>
      <thead><tr><th>Zeitraum</th><th class="num">Einnahmen</th>
        <th class="num">Ausgaben</th><th class="num">Sparen</th>
        <th class="num">Saldo</th></tr></thead>
      <tbody>${d.reihen.map(r => `<tr><td>${r.label}</td>
        <td class="num">${euro(r.einnahmen)}</td>
        <td class="num">${euro(r.ausgaben)}</td>
        <td class="num">${euro(r.sparen)}</td>
        <td class="num ${r.saldo < 0 ? 'neg' : ''}">${euro(r.saldo)}</td></tr>`).join('')}
      </tbody></table></div>`;

  Charts.linie($('#chart-saldo'),
    { perioden, werte: d.reihen.map(r => r.saldo) });

  const gesamt = d.ausgaben_kategorien.reduce((x, k) => x + k.betrag, 0);
  Charts.balkenWaagerecht($('#chart-kategorien'), {
    gesamt,
    zeilen: d.ausgaben_kategorien.map(k => ({
      label: k.kategorie, wert: k.betrag,
      farbe: S.meta.farben[k.kategorie] || '#9b9a97' })),
  });

  zeichneVerlauf();
}

function zeichneVerlauf() {
  if (!S.uebersicht) return;
  const v = S.verlaufArt === 'ausgaben'
    ? S.uebersicht.verlauf_ausgaben : S.uebersicht.verlauf_einnahmen;
  Charts.gestapelt($('#chart-verlauf'), {
    perioden: v.perioden, kategorien: v.kategorien,
    werte: v.werte, farben: S.meta.farben,
  });
}

/* ---------------- Fixkosten ---------------- */
async function ladeFixkosten() {
  const d = await holen('/api/fixkosten?' + query());
  $('#fx-kpi').innerHTML =
    kpi('Fixkosten pro Monat', d.summe_fixkosten) +
    kpi('Festes Sparen pro Monat', d.summe_sparen);

  if (!d.fixkosten.length) {
    $('#chart-fixkosten').innerHTML =
      '<p class="leer-hinweis">Keine wiederkehrenden Fixkosten erkannt.</p>';
    $('#fx-tabelle').innerHTML = '';
  } else {
    Charts.balkenWaagerecht($('#chart-fixkosten'), {
      zeilen: d.fixkosten.map(z => ({
        label: z.empfaenger, wert: z.betrag,
        farbe: S.meta.farben[z.kategorie] || '#9b9a97' })),
    });
    $('#fx-tabelle').innerHTML = fixTabelle(d.fixkosten);
  }

  $('#fx-sparen-karte').hidden = !d.sparen.length;
  if (d.sparen.length) $('#fx-sparen').innerHTML = fixTabelle(d.sparen);
}

function fixTabelle(zeilen) {
  return `<div class="tabellen-rahmen"><table>
    <thead><tr><th>Empfänger (erkannt)</th><th>Kategorie</th>
      <th class="num">Monate</th><th class="num">Betrag/Monat</th>
      <th>Quelle</th></tr></thead>
    <tbody>${zeilen.map(z => `<tr>
      <td><span class="punkt" style="background:${S.meta.farben[z.kategorie] || '#9b9a97'}"></span>${z.empfaenger}</td>
      <td>${z.kategorie}</td>
      <td class="num">${z.monate}</td>
      <td class="num">${euro(z.betrag)}</td>
      <td><span class="badge ${z.manuell ? 'manuell' : ''}">${
        z.manuell ? 'manuell gesetzt' : 'automatisch erkannt'}</span></td>
      </tr>`).join('')}</tbody></table></div>`;
}

/* ---------------- Transaktionen ---------------- */
let suchTimer;
$('#tx-suche').addEventListener('input', () => {
  clearTimeout(suchTimer);
  suchTimer = setTimeout(ladeTransaktionen, 250);
});

async function ladeTransaktionen() {
  const suche = $('#tx-suche').value.trim();
  const d = await holen('/api/transaktionen?' + query(suche ? { suche } : {}));
  if (!d.zeilen.length) {
    $('#tx-tabelle').innerHTML = '<p class="leer-hinweis">Keine Transaktionen gefunden.</p>';
    $('#tx-info').textContent = '';
    return;
  }
  const optionen = (aktiv) => S.meta.kategorien.map(k =>
    `<option value="${k}"${k === aktiv ? ' selected' : ''}>${k}</option>`).join('');

  $('#tx-tabelle').innerHTML = `<div class="tabellen-rahmen"><table>
    <thead><tr><th>Datum</th><th class="num">Betrag</th><th>Kategorie</th>
      <th>Empfänger</th><th>Verwendungszweck</th><th>Fixkosten</th></tr></thead>
    <tbody>${d.zeilen.map(z => `<tr data-id="${z.id}">
      <td>${z.datum}</td>
      <td class="num ${z.betrag < 0 ? 'neg' : 'pos'}">${euro(z.betrag)}</td>
      <td><select class="tx-kategorie">${optionen(z.kategorie)}</select></td>
      <td>${escape2(z.empfaenger)}</td>
      <td>${escape2(z.zweck).slice(0, 70)}</td>
      <td><input type="checkbox" class="tx-fix"${z.fixkosten ? ' checked' : ''}></td>
      </tr>`).join('')}</tbody></table></div>`;

  $('#tx-info').innerHTML = `${d.zeilen.length} von ${d.gesamt} Transaktionen
    angezeigt. Änderungen werden sofort gespeichert und gelten für alle
    Buchungen desselben Empfängers.`;

  $$('#tx-tabelle .tx-kategorie').forEach(sel =>
    sel.addEventListener('change', async e => {
      const id = e.target.closest('tr').dataset.id;
      const a = await senden(`/api/transaktionen/${id}`, { kategorie: e.target.value });
      meldeAenderung(a, 'Kategorie gespeichert');
    }));

  $$('#tx-tabelle .tx-fix').forEach(box =>
    box.addEventListener('change', async e => {
      const id = e.target.closest('tr').dataset.id;
      const a = await senden(`/api/transaktionen/${id}`, { fixkosten: e.target.checked });
      meldeAenderung(a, 'Fixkosten-Kennzeichen gespeichert');
      ladeTransaktionen();
    }));
}

function meldeAenderung(antwort, text) {
  const mit = antwort.mitgeaendert || 0;
  toast(mit ? `${text}. ${mit} weitere Buchung(en) desselben Empfängers `
            + 'automatisch mit angepasst.' : text + '.');
  ladeUebersicht(); ladeMeta();
}

function escape2(s) {
  return (s || '').replace(/[&<>"]/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

/* ---------------- Import ---------------- */
const dz = $('#dropzone'), eingabe = $('#datei-eingabe');
$('#datei-waehlen').addEventListener('click', () => eingabe.click());
eingabe.addEventListener('change', () => setzeDateien([...eingabe.files]));

['dragenter', 'dragover'].forEach(ev => dz.addEventListener(ev, e => {
  e.preventDefault(); dz.classList.add('hover');
}));
['dragleave', 'drop'].forEach(ev => dz.addEventListener(ev, e => {
  e.preventDefault(); dz.classList.remove('hover');
}));
dz.addEventListener('drop', e => setzeDateien([...e.dataTransfer.files]));

function setzeDateien(dateien) {
  S.dateien = dateien.filter(f => /\.(csv|xml)$/i.test(f.name));
  $('#datei-liste').textContent = S.dateien.length
    ? S.dateien.map(f => f.name).join(', ')
    : 'Keine Datei ausgewählt.';
  $('#import-start').disabled = !S.dateien.length;
}

$('#import-start').addEventListener('click', async () => {
  const knopf = $('#import-start');
  knopf.disabled = true; knopf.textContent = 'Importiere …';
  const fd = new FormData();
  S.dateien.forEach(f => fd.append('dateien', f));
  try {
    const r = await fetch('/api/import', { method: 'POST', body: fd });
    const d = await r.json();
    let art = 'erfolg', text = `<b>${d.neu} neue Umsätze importiert</b>,
      ${d.duplikate} Duplikate übersprungen.`;
    if (d.gelesen === 0 && !d.fehler.length) {
      art = 'warn';
      text = '<b>Es konnten 0 Umsätze gelesen werden.</b> Vermutlich weicht das '
           + 'Spaltenformat ab – die Diagnose unten hilft weiter.';
    }
    if (d.fehler.length) { art = 'fehler'; text = d.fehler.join('<br>'); }
    $('#import-ergebnis').innerHTML =
      `<div class="meldung ${art}">${text}<pre>${escape2(d.diagnose)}</pre></div>`;
    setzeDateien([]); eingabe.value = '';
    await allesLaden();
  } catch (e) {
    $('#import-ergebnis').innerHTML =
      `<div class="meldung fehler">Import fehlgeschlagen: ${escape2(String(e))}</div>`;
  } finally {
    knopf.disabled = !S.dateien.length; knopf.textContent = 'Importieren';
  }
});

/* ---------------- Einstellungen ---------------- */
$('#ml-schwelle').addEventListener('input', e =>
  $('#ml-schwelle-wert').textContent = e.target.value + ' %');

$$('[data-aktion]').forEach(b => b.addEventListener('click', async () => {
  const name = b.dataset.aktion;
  if (name === 'alles-loeschen' &&
      !confirm('Wirklich ALLE gespeicherten Umsätze unwiderruflich löschen?')) return;
  const alt = b.textContent;
  b.disabled = true; b.textContent = 'Arbeite …';
  try {
    const daten = name === 'modell-trainieren'
      ? { schwelle: Number($('#ml-schwelle').value) / 100 } : {};
    const a = await senden('/api/aktion/' + name, daten);
    toast(a.meldung, !a.ok);
    await allesLaden();
  } catch (e) {
    toast('Fehler: ' + e, true);
  } finally {
    b.disabled = false; b.textContent = alt;
  }
}));

/* ---------------- Start ---------------- */
async function allesLaden() {
  await ladeMeta();
  await ladeUebersicht();
  if ($('#tab-fixkosten').classList.contains('is-active')) await ladeFixkosten();
  if ($('#tab-transaktionen').classList.contains('is-active')) await ladeTransaktionen();
}

let neuzeichnen;
window.addEventListener('resize', () => {
  clearTimeout(neuzeichnen);
  neuzeichnen = setTimeout(() => {
    if ($('#tab-uebersicht').classList.contains('is-active')) ladeUebersicht();
    if ($('#tab-fixkosten').classList.contains('is-active')) ladeFixkosten();
  }, 220);
});

allesLaden().catch(e => toast('Start fehlgeschlagen: ' + e, true));
