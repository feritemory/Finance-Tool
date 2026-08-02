/* Diagramme als reines SVG – keine externen Bibliotheken, damit die App
   vollständig offline läuft.

   Gestaltung bewusst zurückhaltend: dünne Marken, abgerundete Balkenenden an
   der Grundlinie, feines waagerechtes Raster, Legende oben, Beschriftung nur
   dort, wo sie lesbar bleibt – der Rest über den Tooltip. */

const Charts = (() => {
  const NS = 'http://www.w3.org/2000/svg';
  const INK = '#37352f', SOFT = '#787774', FAINT = '#9b9a97';
  const LINE = '#e9e9e7', FLAECHE = '#ffffff';

  const euro = (v, nk = 2) => v.toLocaleString('de-DE', {
    minimumFractionDigits: nk, maximumFractionDigits: nk }) + ' €';
  const euroKurz = (v) => v.toLocaleString('de-DE', {
    minimumFractionDigits: 0, maximumFractionDigits: 0 }) + ' €';

  function el(name, attrs = {}) {
    const e = document.createElementNS(NS, name);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    return e;
  }

  /* Schöne Schrittweite (1/2/2,5/5 × 10^n). */
  function schrittweite(spanne, anzahl) {
    const roh = spanne / anzahl;
    if (roh <= 0) return 1;
    const gr = Math.pow(10, Math.floor(Math.log10(roh)));
    return [1, 2, 2.5, 5, 10].map(m => m * gr).find(m => m >= roh) || gr * 10;
  }

  /* Achsenschritte ab 0 aufwärts. */
  function schritte(max, anzahl = 5) {
    if (max <= 0) return [0];
    const s = schrittweite(max, anzahl);
    const out = [];
    for (let v = 0; v <= max * 1.0001; v += s) out.push(v);
    return out;
  }

  /* Achsenschritte über einen Bereich, der negativ sein darf – immer runde
     Werte und mit einer Marke genau bei 0. */
  function schritteBereich(min, max, anzahl = 4) {
    if (min === max) { min = Math.min(0, min); max = Math.max(0, max || 1); }
    const s = schrittweite(max - min, anzahl);
    const von = Math.floor(min / s) * s;
    const bis = Math.ceil(max / s) * s;
    const out = [];
    for (let v = von; v <= bis + s * 1e-6; v += s) out.push(Math.round(v * 1e6) / 1e6);
    return out;
  }

  /* Balkenpfad mit abgerundetem Ende (oben bzw. rechts). */
  function balkenPfad(x, y, b, h, r, waagerecht = false) {
    if (waagerecht) {
      r = Math.min(r, b, h / 2);
      return `M${x},${y} H${x + b - r} A${r},${r} 0 0 1 ${x + b},${y + r}`
           + ` V${y + h - r} A${r},${r} 0 0 1 ${x + b - r},${y + h} H${x} Z`;
    }
    r = Math.min(r, h, b / 2);
    return `M${x},${y + h} V${y + r} A${r},${r} 0 0 1 ${x + r},${y}`
         + ` H${x + b - r} A${r},${r} 0 0 1 ${x + b},${y + r} V${y + h} Z`;
  }

  /* --------- Tooltip --------- */
  const tip = () => document.getElementById('tooltip');
  function tipAn(evt, html) {
    const t = tip(); t.innerHTML = html; t.hidden = false;
    const r = t.getBoundingClientRect();
    let x = evt.clientX + 14, y = evt.clientY - r.height - 10;
    if (x + r.width > window.innerWidth - 8) x = evt.clientX - r.width - 14;
    if (y < 8) y = evt.clientY + 16;
    t.style.left = x + 'px'; t.style.top = y + 'px';
  }
  function tipAus() { tip().hidden = true; }

  function hover(node, html) {
    node.addEventListener('mousemove', e => tipAn(e, html));
    node.addEventListener('mouseleave', tipAus);
  }

  function leer(ziel, text = 'Keine Daten im Zeitraum.') {
    ziel.innerHTML = `<p class="leer-hinweis">${text}</p>`;
  }

  function legende(ziel, eintraege) {
    const d = document.createElement('div');
    d.className = 'legende';
    d.innerHTML = eintraege.map(e =>
      `<span class="legende-eintrag"><span class="punkt" style="background:${e.farbe}"></span>${e.name}</span>`
    ).join('');
    ziel.appendChild(d);
  }

  function svgBasis(ziel, hoehe) {
    const breite = Math.max(ziel.clientWidth || 640, 320);
    const s = el('svg', { viewBox: `0 0 ${breite} ${hoehe}`, width: '100%',
                          height: hoehe, role: 'img' });
    ziel.appendChild(s);
    return { s, breite };
  }

  function raster(s, box, werte, skala) {
    werte.forEach(v => {
      const y = skala(v);
      s.appendChild(el('line', { x1: box.l, x2: box.l + box.b, y1: y, y2: y,
                                stroke: LINE, 'stroke-width': 1 }));
      const t = el('text', { x: box.l - 8, y: y + 4, 'text-anchor': 'end',
                             fill: FAINT, 'font-size': 11 });
      t.textContent = v.toLocaleString('de-DE');
      s.appendChild(t);
    });
  }

  /* =====================================================================
     Gruppierte Balken – mehrere Reihen nebeneinander, alle positiv.
     ===================================================================== */
  function gruppierteBalken(ziel, { perioden, serien, beschriften = false }) {
    ziel.innerHTML = '';
    if (!perioden.length) return leer(ziel);
    legende(ziel, serien);

    const hoehe = 400;
    const { s, breite } = svgBasis(ziel, hoehe);
    const box = { l: 62, t: 18, b: breite - 74, h: hoehe - 52 };
    box.b = breite - box.l - 12;

    const max = Math.max(...serien.flatMap(r => r.werte), 1);
    const ticks = schritte(max);
    const obergrenze = Math.max(...ticks, max);
    const y = v => box.t + box.h - (v / obergrenze) * box.h;
    raster(s, box, ticks, y);

    const gruppeB = box.b / perioden.length;
    const innen = gruppeB * 0.72;
    const balkenB = Math.max(innen / serien.length - 2, 2);   // 2px Flächenspalt

    perioden.forEach((p, i) => {
      const start = box.l + i * gruppeB + (gruppeB - innen) / 2;
      serien.forEach((reihe, j) => {
        const wert = reihe.werte[i] || 0;
        const x = start + j * (balkenB + 2);
        const h = (wert / obergrenze) * box.h;
        if (h > 0.4) {
          const pfad = el('path', {
            d: balkenPfad(x, y(wert), balkenB, h, 4),
            fill: reihe.farbe });
          hover(pfad, `<b>${reihe.name}</b><br>${p}<br>${euro(wert)}`);
          s.appendChild(pfad);
        }
        if (beschriften && wert > 0) {
          const t = el('text', { x: x + balkenB / 2, y: y(wert) - 6,
                                 'text-anchor': 'middle', fill: SOFT,
                                 'font-size': 10 });
          t.textContent = euroKurz(wert);
          s.appendChild(t);
        }
      });
      const lab = el('text', { x: box.l + i * gruppeB + gruppeB / 2,
                               y: hoehe - 14, 'text-anchor': 'middle',
                               fill: FAINT, 'font-size': 11 });
      lab.textContent = p;
      s.appendChild(lab);
    });
  }

  /* =====================================================================
     Liniendiagramm – erlaubt negative Werte (Saldo).
     ===================================================================== */
  function linie(ziel, { perioden, werte, farbe = INK }) {
    ziel.innerHTML = '';
    if (!perioden.length) return leer(ziel);

    const hoehe = 300;
    const { s, breite } = svgBasis(ziel, hoehe);
    const box = { l: 66, t: 16, h: hoehe - 48 };
    box.b = breite - box.l - 14;

    const ticks = schritteBereich(Math.min(0, ...werte), Math.max(0, ...werte));
    const min = ticks[0], max = ticks[ticks.length - 1];
    const spanne = (max - min) || 1;
    const y = v => box.t + box.h - ((v - min) / spanne) * box.h;

    ticks.forEach(v => {
      const yy = y(v);
      const null_linie = Math.abs(v) < 1e-9;
      s.appendChild(el('line', { x1: box.l, x2: box.l + box.b, y1: yy, y2: yy,
                                 stroke: null_linie ? '#d8d7d4' : LINE,
                                 'stroke-width': 1 }));
      const t = el('text', { x: box.l - 8, y: yy + 4, 'text-anchor': 'end',
                             fill: FAINT, 'font-size': 11 });
      t.textContent = v.toLocaleString('de-DE');
      s.appendChild(t);
    });

    const x = i => perioden.length === 1
      ? box.l + box.b / 2
      : box.l + (i / (perioden.length - 1)) * box.b;

    const d = werte.map((v, i) => `${i ? 'L' : 'M'}${x(i)},${y(v)}`).join(' ');
    s.appendChild(el('path', { d, fill: 'none', stroke: farbe,
                               'stroke-width': 2, 'stroke-linejoin': 'round' }));

    werte.forEach((v, i) => {
      const k = el('circle', { cx: x(i), cy: y(v), r: 4.5, fill: farbe,
                               stroke: FLAECHE, 'stroke-width': 2 });
      hover(k, `${perioden[i]}<br><b>${euro(v)}</b>`);
      s.appendChild(k);
      if (perioden.length <= 14) {
        const t = el('text', { x: x(i), y: hoehe - 12, 'text-anchor': 'middle',
                               fill: FAINT, 'font-size': 11 });
        t.textContent = perioden[i];
        s.appendChild(t);
      }
    });
  }

  /* =====================================================================
     Waagerechte Balken – Rangfolge mit direkter Beschriftung.
     ===================================================================== */
  function balkenWaagerecht(ziel, { zeilen, gesamt = 0 }) {
    ziel.innerHTML = '';
    if (!zeilen.length) return leer(ziel);

    const zeilenH = 30;
    const hoehe = zeilen.length * zeilenH + 16;
    const { s, breite } = svgBasis(ziel, hoehe);
    const labelB = Math.min(Math.max(breite * 0.34, 120), 300);
    const box = { l: labelB + 10, t: 8, b: breite - labelB - 90 };

    const max = Math.max(...zeilen.map(z => z.wert), 1);
    zeilen.forEach((z, i) => {
      const y = box.t + i * zeilenH;
      const b = Math.max((z.wert / max) * box.b, 2);

      const lab = el('text', { x: labelB, y: y + 15, 'text-anchor': 'end',
                               fill: SOFT, 'font-size': 12 });
      lab.textContent = z.label.length > 40 ? z.label.slice(0, 38) + '…' : z.label;
      lab.appendChild(el('title')).textContent = z.label;
      s.appendChild(lab);

      const pfad = el('path', { d: balkenPfad(box.l, y + 4, b, 18, 4, true),
                                fill: z.farbe });
      const anteil = gesamt ? ` · ${(z.wert / gesamt * 100).toFixed(1)} %` : '';
      hover(pfad, `<b>${z.label}</b><br>${euro(z.wert)}${anteil}`);
      s.appendChild(pfad);

      const wt = el('text', { x: box.l + b + 8, y: y + 17, fill: SOFT,
                              'font-size': 11.5 });
      wt.textContent = euroKurz(z.wert);
      s.appendChild(wt);
    });
  }

  /* =====================================================================
     Gestapelte Balken – Anteile je Zeitraum.
     ===================================================================== */
  function gestapelt(ziel, { perioden, kategorien, werte, farben }) {
    ziel.innerHTML = '';
    if (!perioden.length || !kategorien.length) return leer(ziel);
    legende(ziel, kategorien.map(k => ({ name: k, farbe: farben[k] || FAINT })));

    const hoehe = 380;
    const { s, breite } = svgBasis(ziel, hoehe);
    const box = { l: 62, t: 16, h: hoehe - 50 };
    box.b = breite - box.l - 12;

    const summen = perioden.map((_, i) =>
      kategorien.reduce((a, k) => a + (werte[k]?.[i] || 0), 0));
    const max = Math.max(...summen, 1);
    const ticks = schritte(max);
    const obergrenze = Math.max(...ticks, max);
    const y = v => box.t + box.h - (v / obergrenze) * box.h;
    raster(s, box, ticks, y);

    const gruppeB = box.b / perioden.length;
    const balkenB = Math.min(gruppeB * 0.62, 64);

    perioden.forEach((p, i) => {
      const x = box.l + i * gruppeB + (gruppeB - balkenB) / 2;
      let unten = 0;
      kategorien.forEach(k => {
        const v = werte[k]?.[i] || 0;
        if (v <= 0) return;
        const h = (v / obergrenze) * box.h;
        const yo = y(unten + v);
        // 2px Flächenspalt zwischen den Segmenten
        const seg = el('rect', { x, y: yo, width: balkenB,
                                 height: Math.max(h - 2, 1),
                                 fill: farben[k] || FAINT, rx: 2 });
        hover(seg, `<b>${k}</b><br>${p}<br>${euro(v)}`);
        s.appendChild(seg);
        unten += v;
      });
      const lab = el('text', { x: x + balkenB / 2, y: hoehe - 14,
                               'text-anchor': 'middle', fill: FAINT,
                               'font-size': 11 });
      lab.textContent = p;
      s.appendChild(lab);
    });
  }

  return { gruppierteBalken, linie, balkenWaagerecht, gestapelt, euro, euroKurz };
})();
