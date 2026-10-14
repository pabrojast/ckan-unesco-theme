/*
 * Initiative pages (added by Jorgen Van Der Biest). New file.
 * Cuestionario de la página completa de una iniciativa
 * (templates/initiative/snippets/questionnaire.html):
 *  - listas con búsqueda sobre cada select[data-picker] (organizaciones,
 *    Estados miembros, outputs de IHP-IX con su texto, datasets)
 *  - filas repetibles (objetivos 1-8, cifras clave, contactos)
 *  - paso 6 opcional (Skip this step)
 *  - vista previa de imágenes y extracción de colores (k-means en OKLab),
 *    con los mismos roles y comprobaciones de contraste que initiative.py
 * Sin este script el formulario sigue funcionando con los controles estándar.
 */
(function () {
  'use strict';

  /* ------------------------------------------------------------------ */
  /* Utilidades                                                          */
  /* ------------------------------------------------------------------ */
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function el(tag, attrs, children) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === 'text') { n.textContent = attrs[k]; }
      else if (k === 'class') { n.className = attrs[k]; }
      else if (k.indexOf('on') === 0) { n.addEventListener(k.slice(2), attrs[k]); }
      else if (attrs[k] !== null && attrs[k] !== undefined && attrs[k] !== false) { n.setAttribute(k, attrs[k] === true ? '' : attrs[k]); }
    });
    (children || []).forEach(function (c) { if (c) { n.appendChild(typeof c === 'string' ? document.createTextNode(c) : c); } });
    return n;
  }
  function norm(s) { return String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase(); }
  var STOP = ['of', 'the', 'and', 'for', 'in', 'on', 'de', 'del', 'la', 'du', 'et', '&'];
  function initials(s) {
    return String(s).split(/[\s\-–\/,()]+/).filter(function (w) { return w && STOP.indexOf(w.toLowerCase()) < 0; })
      .map(function (w) { return w.charAt(0); }).join('');
  }
  function escRx(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

  /* Búsqueda: todas las palabras deben aparecer; primero los que empiezan por
     la primera palabra, luego los que la tienen al inicio de una palabra. */
  function search(items, q, limit) {
    var terms = norm(q).trim().split(/\s+/).filter(Boolean);
    if (!terms.length) { return { list: [], total: 0, term: '' }; }
    var ws = new RegExp('(^|[^a-z0-9])' + escRx(terms[0]));
    var hits = [];
    items.forEach(function (it) {
      var hay = it.hay;
      if (!terms.every(function (t) { return hay.indexOf(t) >= 0; })) { return; }
      hits.push({ it: it, score: hay.indexOf(terms[0]) === 0 ? 0 : (ws.test(hay) ? 1 : 2) });
    });
    hits.sort(function (a, b) { return a.score - b.score || a.it.sort.localeCompare(b.it.sort); });
    return { list: hits.slice(0, limit).map(function (h) { return h.it; }), total: hits.length, term: terms[0] };
  }
  function marked(text, term) {
    var span = document.createElement('span');
    var i = term ? norm(text).indexOf(term) : -1;
    if (i < 0) { span.textContent = text; return span; }
    span.appendChild(document.createTextNode(text.slice(0, i)));
    span.appendChild(el('mark', { text: text.slice(i, i + term.length) }));
    span.appendChild(document.createTextNode(text.slice(i + term.length)));
    return span;
  }

  /* ------------------------------------------------------------------ */
  /* Listas con búsqueda                                                 */
  /* ------------------------------------------------------------------ */
  var LIMIT = 8;

  function initPicker(select) {
    var kind = select.getAttribute('data-picker');           // single | multi | outputs
    var noun = select.getAttribute('data-noun') || 'items';
    var max = parseInt(select.getAttribute('data-max') || '0', 10);
    var items = $$('option', select).filter(function (o) { return o.value; }).map(function (o) {
      var grp = o.parentNode.tagName === 'OPTGROUP' ? o.parentNode : null;
      var label = kind === 'outputs' ? (o.getAttribute('data-text') || o.textContent) : o.textContent.trim();
      return {
        opt: o, value: o.value, label: label, pa: grp ? grp.getAttribute('data-pa') : '',
        paTitle: grp ? grp.label : '', sort: kind === 'outputs' ? pad(o.value) : label.toLowerCase(),
        hay: norm(o.value + ' ' + label + ' ' + initials(label) + (grp ? ' ' + grp.label : ''))
      };
    });
    function pad(code) { var p = code.split('.'); return ('000' + p[0]).slice(-3) + ('000' + (p[1] || 0)).slice(-3); }

    var id = select.id || ('ini-p-' + Math.random().toString(36).slice(2));
    var listId = id + '-list';
    var box = el('div', { class: 'ini-picker' });
    var selected = el(kind === 'outputs' ? 'ul' : 'ul', { class: kind === 'outputs' ? 'ini-outsel' : 'ini-chipset', 'aria-label': 'Selected ' + noun });
    var single = el('div', { class: 'ini-single', hidden: true });
    var input = el('input', {
      type: 'search', role: 'combobox', 'aria-autocomplete': 'list', 'aria-expanded': 'false',
      'aria-controls': listId, autocomplete: 'off', placeholder: select.getAttribute('data-placeholder') || '',
      'aria-describedby': select.getAttribute('aria-describedby')
    });
    var list = el('ul', { class: 'ini-picker-list', id: listId, role: 'listbox', hidden: true });
    var paFilter = '';
    var paBar = null;
    var active = -1;

    // La etiqueta del select pasa a la caja de búsqueda
    var lab = select.id && document.querySelector('label[for="' + select.id + '"]');
    select.id = id + '-select';
    input.id = id;
    if (lab) { lab.setAttribute('for', id); }
    select.hidden = true;
    select.setAttribute('aria-hidden', 'true');
    select.tabIndex = -1;

    if (kind === 'outputs') {
      var areas = [];
      items.forEach(function (it) { if (areas.map(function (a) { return a.pa; }).indexOf(it.pa) < 0) { areas.push({ pa: it.pa, title: it.paTitle }); } });
      paBar = el('div', { class: 'ini-pa-filters', role: 'group', 'aria-label': 'Browse by priority area' });
      areas.forEach(function (a) {
        paBar.appendChild(el('button', {
          type: 'button', title: a.title, 'aria-pressed': 'false', text: a.pa,
          onclick: function () { paFilter = paFilter === a.pa ? '' : a.pa; input.value = ''; render(); if (paFilter) { list.hidden = false; } }
        }));
      });
    }

    function chosen() { return items.filter(function (it) { return it.opt.selected; }); }
    function pick(it) {
      if (kind === 'single') {
        items.forEach(function (x) { x.opt.selected = false; });
        it.opt.selected = true;
      } else {
        if (max && chosen().length >= max) { return; }
        it.opt.selected = true;
      }
      input.value = '';
      select.dispatchEvent(new Event('change', { bubbles: true }));
      render();
      if (kind !== 'single') { input.focus(); }
    }
    function unpick(it) {
      it.opt.selected = false;
      select.dispatchEvent(new Event('change', { bubbles: true }));
      render();
      input.focus();
    }

    function renderSelected() {
      var ch = chosen();
      if (kind === 'single') {
        single.innerHTML = '';
        if (ch.length) {
          single.appendChild(el('span', { text: ch[0].label }));
          single.appendChild(el('button', { type: 'button', class: 'ini-ghost', text: 'Change', onclick: function () { ch[0].opt.selected = false; select.value = ''; render(); input.focus(); } }));
        }
        single.hidden = !ch.length;
        input.hidden = !!ch.length;
        return;
      }
      selected.innerHTML = '';
      ch.forEach(function (it) {
        var rm = el('button', { type: 'button', 'aria-label': 'Remove ' + (kind === 'outputs' ? 'output ' + it.value : it.label), onclick: function () { unpick(it); } }, ['×']);
        if (kind === 'outputs') {
          rm.className = 'ini-x';
          selected.appendChild(el('li', {}, [
            el('span', { class: 'code', text: it.value }),
            el('span', {}, [el('span', { class: 'pa', text: it.paTitle }), el('span', { text: it.label })]),
            rm
          ]));
        } else {
          selected.appendChild(el('li', {}, [it.label, rm]));
        }
      });
      var full = max && ch.length >= max;
      input.disabled = !!full;
      input.placeholder = full ? ('Maximum ' + max + ' ' + noun) : (select.getAttribute('data-placeholder') || '');
    }

    function renderList() {
      var q = input.value.trim();
      list.innerHTML = '';
      active = -1;
      var pool = items.filter(function (it) { return kind === 'single' || !it.opt.selected; });
      var shown = [], total = 0, term = '';
      if (q) {
        var r = search(pool, q, LIMIT); shown = r.list; total = r.total; term = r.term;
      } else if (paFilter) {
        shown = pool.filter(function (it) { return it.pa === paFilter; }); total = shown.length;
        var head = items.filter(function (it) { return it.pa === paFilter; })[0];
        if (head) { list.appendChild(el('li', { class: 'ini-picker-head', text: head.paTitle })); }
      }
      shown.forEach(function (it) {
        var btn = el('button', { type: 'button', class: 'ini-picker-opt' + (kind === 'outputs' ? ' ini-picker-opt--output' : ''), tabindex: '-1', onclick: function () { pick(it); } });
        if (kind === 'outputs') { btn.appendChild(el('b', { text: it.value })); }
        btn.appendChild(marked(it.label, term));
        if (kind !== 'single') { btn.appendChild(el('em', { text: 'Add' })); }
        list.appendChild(el('li', { role: 'option', 'aria-selected': 'false' }, [btn]));
      });
      if (q && total > shown.length) { list.appendChild(el('li', { class: 'ini-picker-note', text: (total - shown.length) + ' more ' + noun + ' match. Keep typing to narrow down.' })); }
      if ((q || paFilter) && total === 0) { list.appendChild(el('li', { class: 'ini-picker-note', text: 'No ' + noun + ' match.' })); }
      var open = !!(q || paFilter);
      list.hidden = !open;
      input.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (paBar) { $$('button', paBar).forEach(function (b) { b.setAttribute('aria-pressed', b.textContent === paFilter ? 'true' : 'false'); }); }
    }
    function render() { renderSelected(); renderList(); }

    function move(step) {
      var opts = $$('.ini-picker-opt', list);
      if (!opts.length) { return; }
      active = (active + step + opts.length) % opts.length;
      opts.forEach(function (o, i) { o.classList.toggle('is-active', i === active); });
      opts[active].scrollIntoView({ block: 'nearest' });
    }
    input.addEventListener('input', function () { paFilter = ''; renderList(); });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); move(1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1); }
      else if (e.key === 'Enter') {
        var opts = $$('.ini-picker-opt', list);
        if (opts.length) { e.preventDefault(); (opts[active >= 0 ? active : 0]).click(); }
      } else if (e.key === 'Escape') { input.value = ''; paFilter = ''; renderList(); }
    });
    document.addEventListener('click', function (e) { if (!box.contains(e.target)) { list.hidden = true; input.setAttribute('aria-expanded', 'false'); } });

    if (kind === 'single') { box.appendChild(single); } else { box.appendChild(selected); }
    if (paBar) { box.appendChild(paBar); }
    box.appendChild(input);
    box.appendChild(list);
    select.parentNode.insertBefore(box, select.nextSibling);
    render();
  }

  /* ------------------------------------------------------------------ */
  /* Filas repetibles                                                    */
  /* ------------------------------------------------------------------ */
  function initRepeat(rep) {
    var prefix = rep.getAttribute('data-repeat');
    var min = parseInt(rep.getAttribute('data-min') || '0', 10);
    var max = parseInt(rep.getAttribute('data-max') || '99', 10);
    var tpl = $('template[data-row-template]', rep);
    var addBtn = $('[data-add]', rep);
    var next = 0;
    $$('[data-row]', rep).forEach(function (row) {
      $$('[name]', row).forEach(function (f) {
        var m = f.name.match(/-(\d+)-/);
        if (m) { next = Math.max(next, parseInt(m[1], 10) + 1); }
      });
    });
    function rows() { return $$(':scope > [data-row]', rep); }
    function refresh() {
      var rs = rows();
      rs.forEach(function (row, i) {
        $$('[data-row-no]', row).forEach(function (n) { n.textContent = i + 1; });
        var rm = $('[data-remove]', row);
        if (rm) { rm.disabled = rs.length <= min; }
      });
      if (addBtn) { addBtn.disabled = rs.length >= max; }
      $$('[data-count-for="' + prefix + '"]').forEach(function (c) { c.textContent = '· ' + rs.length + ' of ' + max; });
      document.dispatchEvent(new CustomEvent('ini:changed'));
    }
    rep.addEventListener('click', function (e) {
      var rm = e.target.closest('[data-remove]');
      if (rm && rep.contains(rm)) {
        var row = rm.closest('[data-row]');
        if (row && rows().length > min) { row.parentNode.removeChild(row); refresh(); }
      }
    });
    if (addBtn && tpl) {
      addBtn.addEventListener('click', function () {
        if (rows().length >= max) { return; }
        var html = tpl.innerHTML.replace(/__i__/g, String(next++));
        var wrap = document.createElement('div');
        wrap.innerHTML = html.trim();
        var row = wrap.firstElementChild;
        rep.insertBefore(row, addBtn);
        $$('[data-image-input]', row).forEach(bindImage);
        var first = $('input, textarea', row);
        if (first) { first.focus(); }
        refresh();
      });
    }
    refresh();
  }

  /* ------------------------------------------------------------------ */
  /* Colores (mismas reglas que initiative.py)                           */
  /* ------------------------------------------------------------------ */
  function toLin(c) { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
  function toSrgb(c) { return 255 * (c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055); }
  function rgbOf(hx) { hx = String(hx || '#000000').replace('#', ''); return [0, 2, 4].map(function (i) { return parseInt(hx.substr(i, 2), 16) || 0; }); }
  function labOf(r, g, b) {
    r = toLin(r); g = toLin(g); b = toLin(b);
    var l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
    var m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
    var s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
    return [0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
      1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
      0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s];
  }
  function lchOf(hx) { var c = rgbOf(hx); var lab = labOf(c[0], c[1], c[2]); return { L: lab[0], C: Math.hypot(lab[1], lab[2]), h: ((Math.atan2(lab[2], lab[1]) * 180 / Math.PI) + 360) % 360 }; }
  function hexOf(L, C, h) {
    var lin = [0, 0, 0];
    for (var i = 0; i < 60; i++) {
      var a = C * Math.cos(h * Math.PI / 180), b = C * Math.sin(h * Math.PI / 180);
      var l = Math.pow(L + 0.3963377774 * a + 0.2158037573 * b, 3);
      var m = Math.pow(L - 0.1055613458 * a - 0.0638541728 * b, 3);
      var s = Math.pow(L - 0.0894841775 * a - 1.2914855480 * b, 3);
      lin = [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s];
      if (lin.every(function (v) { return v >= -1e-4 && v <= 1.0001; })) { break; }
      C *= 0.95;
    }
    return '#' + lin.map(function (v) {
      var n = Math.max(0, Math.min(255, Math.round(toSrgb(Math.max(0, Math.min(1, v))))));
      return (n < 16 ? '0' : '') + n.toString(16).toUpperCase();
    }).join('');
  }
  function lum(hx) { var c = rgbOf(hx).map(toLin); return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; }
  function ratio(x, y) { var a = lum(x), b = lum(y); return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05); }
  function fit(C, h, L, against, target, dir) {
    var hx = hexOf(L, C, h);
    while (ratio(hx, against) < target && L > 0.05 && L < 0.98) { L += 0.005 * dir; hx = hexOf(L, C, h); }
    return hx;
  }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function deriveRoles(p, a, s) {
    var P = lchOf(p), A = lchOf(a), S = lchOf(s), W = '#FFFFFF';
    var Cp = clamp(P.C, 0.07, 0.15), Ca = clamp(A.C, 0.11, 0.19), r = {};
    r.primary = fit(Cp, P.h, 0.44, W, 7.0, -1);
    r.ink = fit(0.035, P.h, 0.30, W, 12.0, -1);
    r.soft = hexOf(clamp(S.L, 0.84, 0.92), Math.min(S.C, 0.09), S.h);
    r.tint = hexOf(0.975, 0.012, S.h);
    r.line = hexOf(0.90, 0.025, S.h);
    r.onPrimarySoft = hexOf(0.92, 0.03, P.h);
    r.highlight = fit(Math.min(0.10, Cp), S.h, 0.86, r.primary, 4.5, +1);
    r.accent = fit(Ca, A.h, 0.70, W, 3.0, -1);
    r.accentInk = fit(Ca, A.h, 0.55, r.tint, 4.5, -1);
    r.checks = [
      ['White text on the main colour', ratio(W, r.primary), 7],
      ['Body text on white', ratio(r.ink, W), 7],
      ['Eyebrows and links on tinted sections', ratio(r.accentInk, r.tint), 4.5],
      ['Highlighted title on the main colour', ratio(r.highlight, r.primary), 4.5],
      ['Key figures on the light band', ratio(r.primary, r.soft), 4.5],
      ['Accent lines against white', ratio(r.accent, W), 3]
    ];
    return r;
  }

  /* k-means en OKLab sobre los píxeles de las imágenes (cada imagen pesa igual) */
  function pixelsOf(img) {
    try {
      var c = document.createElement('canvas');
      var scale = Math.min(1, 120 / Math.max(img.naturalWidth || 1, img.naturalHeight || 1));
      c.width = Math.max(1, Math.round((img.naturalWidth || 1) * scale));
      c.height = Math.max(1, Math.round((img.naturalHeight || 1) * scale));
      var ctx = c.getContext('2d');
      ctx.drawImage(img, 0, 0, c.width, c.height);
      var data = ctx.getImageData(0, 0, c.width, c.height).data, pts = [];
      var step = Math.max(1, Math.floor((data.length / 4) / 3000));
      for (var i = 0; i < data.length; i += 4 * step) {
        if (data[i + 3] < 128) { continue; }
        pts.push(labOf(data[i], data[i + 1], data[i + 2]));
      }
      return pts;
    } catch (e) { return []; }  // imagen de otro dominio: sin acceso a los píxeles
  }
  function kmeans(pts, k) {
    var seed = 11;
    function rnd() { seed = (seed * 16807) % 2147483647; return seed / 2147483647; }
    var centers = [pts[Math.floor(rnd() * pts.length)]];
    while (centers.length < k) {
      var d2 = pts.map(function (p) { return Math.min.apply(null, centers.map(function (c) { return dist(p, c); })); });
      var tot = d2.reduce(function (a, b) { return a + b; }, 0), r = rnd() * tot, acc = 0, idx = 0;
      for (var i = 0; i < d2.length; i++) { acc += d2[i]; if (acc >= r) { idx = i; break; } }
      centers.push(pts[idx]);
    }
    var groups = [];
    for (var it = 0; it < 18; it++) {
      groups = centers.map(function () { return []; });
      pts.forEach(function (p) {
        var best = 0, bd = Infinity;
        centers.forEach(function (c, j) { var dd = dist(p, c); if (dd < bd) { bd = dd; best = j; } });
        groups[best].push(p);
      });
      centers = groups.map(function (g, j) {
        if (!g.length) { return centers[j]; }
        var s = [0, 0, 0]; g.forEach(function (p) { s[0] += p[0]; s[1] += p[1]; s[2] += p[2]; });
        return [s[0] / g.length, s[1] / g.length, s[2] / g.length];
      });
    }
    return centers.map(function (c, j) {
      return { L: c[0], C: Math.hypot(c[1], c[2]), h: ((Math.atan2(c[2], c[1]) * 180 / Math.PI) + 360) % 360, share: groups[j].length / pts.length };
    }).filter(function (c) { return c.share > 0; }).map(function (c) { c.hex = hexOf(c.L, c.C, c.h); return c; })
      .sort(function (a, b) { return b.share - a.share; });
  }
  function dist(a, b) { var x = a[0] - b[0], y = a[1] - b[1], z = a[2] - b[2]; return x * x + y * y + z * z; }
  function hueDist(a, b) { var d = Math.abs(a - b) % 360; return Math.min(d, 360 - d); }
  function autoSeeds(clusters) {
    var col = clusters.filter(function (c) { return c.C >= 0.035 && c.L > 0.15 && c.L < 0.95; });
    if (!col.length) { return null; }
    function sal(c) { return Math.pow(c.share, 0.6) * Math.min(c.C, 0.18); }
    var primary = col.slice().sort(function (a, b) { return sal(b) - sal(a); })[0];
    // El acento: un color vivo (ni muy oscuro ni casi gris) con otro tono
    var far = col.filter(function (c) { return hueDist(c.h, primary.h) >= 60 && c.C >= 0.05 && c.L >= 0.35 && c.L <= 0.9; });
    var accent = far.sort(function (a, b) {
      return sal(b) * (0.5 + hueDist(b.h, primary.h) / 180) - sal(a) * (0.5 + hueDist(a.h, primary.h) / 180);
    })[0];
    var light = clusters.filter(function (c) { return c.L >= 0.75 && c.C >= 0.03; });
    var soft = light.length ? light.sort(function (a, b) { return b.share - a.share; })[0] : primary;
    // Sin segundo color en las imágenes: naranja para principales fríos, azul agua para el resto
    var fallbackHue = (primary.h >= 150 && primary.h <= 330) ? 45 : 235;
    return { primary: primary.hex, accent: accent ? accent.hex : hexOf(0.7, 0.14, fallbackHue), soft: soft.hex };
  }

  function initColours(form) {
    var box = $('[data-colours]', form);
    if (!box) { return; }
    var seedInputs = {};
    $$('[data-seed]', box).forEach(function (i) { seedInputs[i.getAttribute('data-seed')] = i; });
    var autoInput = $('[data-seed-auto]', box);
    var clusters = [];
    var auto = null;

    function seeds() { return { primary: seedInputs.primary.value, accent: seedInputs.accent.value, soft: seedInputs.soft.value }; }
    function setSeeds(s, isAuto) {
      ['primary', 'accent', 'soft'].forEach(function (k) { if (s[k]) { seedInputs[k].value = s[k]; } });
      autoInput.value = isAuto ? '1' : '0';
      paint();
    }
    function paint() {
      var s = seeds(), r = deriveRoles(s.primary, s.accent, s.soft);
      var pv = $('[data-preview-box]', box);
      if (pv) {
        var vars = { '--p': r.primary, '--soft': r.soft, '--tint': r.tint, '--line': r.line, '--hl': r.highlight, '--onp': r.onPrimarySoft, '--acc': r.accent, '--acci': r.accentInk, '--ink': r.ink };
        Object.keys(vars).forEach(function (k) { pv.style.setProperty(k, vars[k]); });
      }
      $$('.ini-layout-pic').forEach(function (p) { p.style.setProperty('--ini-p', r.primary); });
      var list = $('[data-checks]', box);
      if (list) {
        list.innerHTML = '';
        r.checks.forEach(function (c) {
          var ok = c[1] >= c[2];
          list.appendChild(el('li', { class: ok ? 'ok' : 'fail' }, [
            el('span', { class: 'ini-check-mark', 'aria-label': ok ? 'Passes' : 'Fails' }),
            el('span', { text: c[0] }),
            el('code', { text: c[1].toFixed(1) + ':1 / ' + c[2] + ':1' })
          ]));
        });
        var sum = $('[data-summary="checks"]', form);
        if (sum) { sum.textContent = r.checks.filter(function (c) { return c[1] >= c[2]; }).length + ' / ' + r.checks.length; }
      }
      // Muestras: los colores de las imágenes (o las semillas actuales si no hay)
      ['primary', 'accent', 'soft'].forEach(function (key) {
        var row = $('[data-swatches="' + key + '"]', box);
        if (!row) { return; }
        row.innerHTML = '';
        var pool = clusters.filter(function (c) { return key !== 'soft' ? c.L < 0.97 : c.L >= 0.6; }).map(function (c) { return c.hex; });
        if (pool.indexOf(s[key].toUpperCase()) < 0) { pool.unshift(s[key].toUpperCase()); }
        pool.slice(0, 8).forEach(function (hx, i) {
          var on = hx.toUpperCase() === s[key].toUpperCase();
          row.appendChild(el('button', {
            type: 'button', class: 'ini-swatch', style: 'background:' + hx, 'aria-pressed': on ? 'true' : 'false',
            'aria-label': key + ' colour ' + (i + 1) + ' (' + hx + ')' + (auto && auto[key] === hx ? ', automatic choice' : ''),
            onclick: function () { var o = {}; o[key] = hx; setSeeds(o, false); }
          }));
        });
      });
    }
    function extract() {
      var imgs = $$('[data-image-slot] img[data-preview]', form).filter(function (i) { return !i.hidden && i.complete && i.naturalWidth; });
      if (!imgs.length) { paint(); return; }
      var pts = [];
      imgs.forEach(function (img) { pts = pts.concat(pixelsOf(img)); });
      if (pts.length < 50) { paint(); return; }
      clusters = kmeans(pts, 8);
      auto = autoSeeds(clusters);
      if (auto && autoInput.value === '1') { setSeeds(auto, true); } else { paint(); }
    }
    $('[data-colour-reset]', box).addEventListener('click', function () { if (auto) { setSeeds(auto, true); } else { autoInput.value = '1'; paint(); } });
    document.addEventListener('ini:images', extract);
    // Imágenes ya guardadas (modo edición): esperar a que carguen
    var pending = $$('[data-image-slot] img[data-preview]', form).filter(function (i) { return !i.hidden && !i.complete; });
    pending.forEach(function (i) { i.addEventListener('load', extract, { once: true }); });
    extract();
  }

  /* ------------------------------------------------------------------ */
  /* Imágenes: vista previa                                              */
  /* ------------------------------------------------------------------ */
  function bindImage(input) {
    input.addEventListener('change', function () {
      var f = input.files && input.files[0];
      var scope = input.closest('[data-image-slot]') || input.closest('.ini-field');
      var img = scope && $('img[data-preview]', scope);
      var empty = scope && $('.ini-image-empty', scope);
      if (!img) { return; }
      if (!f) { return; }
      img.onload = function () { if (input.hasAttribute('data-colour-source')) { document.dispatchEvent(new CustomEvent('ini:images')); } };
      img.src = URL.createObjectURL(f);
      img.hidden = false;
      if (empty) { empty.hidden = true; }
    });
  }

  /* ------------------------------------------------------------------ */
  /* Arranque                                                            */
  /* ------------------------------------------------------------------ */
  function init() {
    var form = document.getElementById('ini-form');
    if (!form) { return; }

    // Dirección propuesta a partir del nombre (como munge_name de CKAN)
    var src = $('[data-slug-source]', form), out = $('[data-slug-preview]', form);
    if (src && out) {
      var upd = function () {
        var v = norm(src.value).replace(/[^a-z0-9_-]+/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '').slice(0, 100);
        out.textContent = v || 'your-initiative';
      };
      src.addEventListener('input', upd); upd();
    }

    $$('select[data-picker]', form).forEach(initPicker);
    $$('[data-repeat]', form).forEach(initRepeat);
    $$('[data-image-input]', form).forEach(bindImage);
    initColours(form);

    // Paso 6 opcional
    var step6 = $('[data-skippable]', form);
    if (step6) {
      var btn = $('[data-skip-toggle]', step6), inp = $('[data-skip-input]', step6);
      btn.addEventListener('click', function () {
        var skip = inp.value !== '1';
        inp.value = skip ? '1' : '0';
        step6.classList.toggle('is-skipped', skip);
        btn.setAttribute('aria-pressed', skip ? 'true' : 'false');
        btn.textContent = skip ? 'Fill in this step' : 'Skip this step';
      });
    }

    // Resumen del paso 7
    function summary() {
      var objs = $$('[data-repeat="ini_obj"] > [data-row]', form).filter(function (r) { var t = $('input[name$="-title"]', r); return t && t.value.trim(); }).length;
      var outs = $$('select[name="ini_outputs"] option', form).filter(function (o) { return o.selected; }).length;
      var parts = $$('select[name="ini_partners"] option', form).filter(function (o) { return o.selected; }).length;
      var set = function (k, v) { var n = $('[data-summary="' + k + '"]', form); if (n) { n.textContent = v; } };
      set('objectives', objs); set('outputs', outs); set('partners', parts);
    }
    form.addEventListener('change', summary);
    form.addEventListener('input', summary);
    document.addEventListener('ini:changed', summary);
    summary();
  }

  if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', init); } else { init(); }
})();
