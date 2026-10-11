/*
 * Dashboards de progreso IHP-IX (templates/ihpix/progress.html).
 *
 * Lee los datos iniciales de `#ihpix-progress-data` (JSON de la acción
 * `ihpix_progress_stats`) y la configuración de `#ihpix-progress-config`;
 * pinta tiles, gráficos (Chart.js), mapas (Leaflet) y tablas accesibles, y
 * vuelve a pedir los datos a la API cuando cambian los filtros (bienio,
 * región). Sin dependencias más allá de Chart.js y Leaflet, ya cargados por
 * el template. Expone `window.IhpixProgress = { init, load, render }`.
 */
(function (window, document) {
  'use strict';

  var CFG = null;
  var DATA = null;
  var charts = {};
  var maps = {};
  var pending = {};
  var observer = null;
  var reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ── Utilidades ─────────────────────────────────────────────── */
  function readJSON(id) {
    var el = document.getElementById(id);
    if (!el) { return null; }
    try { return JSON.parse(el.textContent || '{}'); } catch (e) { return null; }
  }
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function t(key, fallback) { return (CFG && CFG.strings && CFG.strings[key]) || fallback || key; }
  function fmt(n) {
    if (n === null || n === undefined || isNaN(n)) { return '–'; }
    try { return Number(n).toLocaleString(CFG && CFG.locale || undefined); } catch (e) { return String(n); }
  }
  function pct(v) { return (v === null || v === undefined) ? '–' : (Math.round(v * 10) / 10).toLocaleString(CFG && CFG.locale || undefined) + '%'; }
  function esc(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function get(obj, path, dflt) {
    var cur = obj;
    var parts = path.split('.');
    for (var i = 0; i < parts.length; i++) {
      if (cur === null || cur === undefined) { return dflt; }
      cur = cur[parts[i]];
    }
    return (cur === null || cur === undefined) ? dflt : cur;
  }
  function paColor(key) {
    var k = String(key || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
    var colors = CFG.paColors || {};
    for (var pa in colors) { if (colors.hasOwnProperty(pa) && k.indexOf(pa) === 0) { return colors[pa]; } }
    return CFG.neutral || '#94A3B8';
  }
  /* Color categórico fijo por entidad: la posición del valor en su lista
     canónica decide el color; "Other" y desconocidos van en gris. */
  function typeColor(value, canon) {
    if (!value || /^other$/i.test(value) || /^unspecified$/i.test(value)) { return CFG.neutral || '#94A3B8'; }
    var idx = canon ? canon.indexOf(value) : -1;
    var pal = CFG.categorical || [];
    if (idx < 0 || idx >= pal.length) { return CFG.neutral || '#94A3B8'; }
    return pal[idx];
  }
  function shortKey(key) {
    var m = /^PA(\d)$/.exec(String(key || ''));
    return m ? 'PA ' + m[1] : String(key || '');
  }
  function dimColor(item, dimension) {
    if (dimension === 'priority_area') { return paColor(item.key); }
    if (dimension === 'output') { return paColor(CFG.outputPa && CFG.outputPa[item.key] || ''); }
    return CFG.action || '#0069B4';
  }

  /* ── Chart.js: valores por defecto y plugins ────────────────── */
  function setupChartDefaults() {
    if (!window.Chart) { return; }
    var font = getComputedStyle(document.body).fontFamily || 'Inter, system-ui, sans-serif';
    Chart.defaults.font.family = font;
    Chart.defaults.font.size = 12;
    Chart.defaults.color = CFG.ink2 || '#5B6B7F';
    Chart.defaults.animation = reducedMotion ? false : { duration: 350 };
    Chart.defaults.plugins.legend.display = false;
    Chart.defaults.plugins.tooltip.backgroundColor = CFG.ink || '#0B2A4A';
    Chart.defaults.plugins.tooltip.titleFont = { size: 13, weight: '600' };
    Chart.defaults.plugins.tooltip.bodyFont = { size: 12 };
    Chart.defaults.plugins.tooltip.cornerRadius = 6;
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.displayColors = true;
    Chart.defaults.plugins.tooltip.boxPadding = 4;
  }

  /* Etiquetas directas al final de las barras horizontales */
  var barValueLabels = {
    id: 'ixgBarValues',
    afterDatasetsDraw: function (chart, args, opts) {
      if (!opts || !opts.enabled) { return; }
      var ctx = chart.ctx;
      var stacked = !!(chart.options.scales && chart.options.scales.x && chart.options.scales.x.stacked);
      ctx.save();
      ctx.font = '600 12px ' + Chart.defaults.font.family;
      ctx.fillStyle = CFG.ink || '#0B2A4A';
      ctx.textBaseline = 'middle';
      var totals = {};
      if (stacked) {
        chart.data.datasets.forEach(function (ds, di) {
          if (!chart.isDatasetVisible(di)) { return; }
          ds.data.forEach(function (v, i) { totals[i] = (totals[i] || 0) + (Number(v) || 0); });
        });
      }
      var lastVisible = -1;
      chart.data.datasets.forEach(function (ds, di) { if (chart.isDatasetVisible(di)) { lastVisible = di; } });
      chart.data.datasets.forEach(function (ds, di) {
        if (!chart.isDatasetVisible(di)) { return; }
        if (stacked && di !== lastVisible) { return; }
        var meta = chart.getDatasetMeta(di);
        meta.data.forEach(function (bar, i) {
          var v = stacked ? totals[i] : Number(ds.data[i]) || 0;
          if (!v) { return; }
          var text = fmt(v);
          var x = bar.x + 6;
          var width = ctx.measureText(text).width;
          if (x + width > chart.chartArea.right) {
            ctx.fillStyle = '#FFFFFF';
            x = bar.x - width - 6;
          } else {
            ctx.fillStyle = CFG.ink || '#0B2A4A';
          }
          ctx.textAlign = 'left';
          ctx.fillText(text, x, bar.y);
        });
      });
      ctx.restore();
    }
  };

  /* Texto central de los donuts y gauges */
  var centerText = {
    id: 'ixgCenterText',
    afterDraw: function (chart, args, opts) {
      if (!opts || !opts.text) { return; }
      var ctx = chart.ctx;
      var area = chart.chartArea;
      var cx = (area.left + area.right) / 2;
      var cy = opts.gauge ? area.bottom - 4 : (area.top + area.bottom) / 2;
      ctx.save();
      ctx.textAlign = 'center';
      ctx.textBaseline = opts.gauge ? 'bottom' : 'middle';
      ctx.fillStyle = CFG.ink || '#0B2A4A';
      ctx.font = '700 ' + (opts.size || 20) + 'px ' + Chart.defaults.font.family;
      ctx.fillText(opts.text, cx, opts.gauge ? cy : cy - (opts.sub ? 7 : 0));
      if (opts.sub && !opts.gauge) {
        ctx.font = '400 11px ' + Chart.defaults.font.family;
        ctx.fillStyle = CFG.ink2 || '#5B6B7F';
        ctx.fillText(opts.sub, cx, cy + 11);
      }
      ctx.restore();
    }
  };

  function destroyChart(id) {
    if (charts[id]) { try { charts[id].destroy(); } catch (e) { /* nada */ } delete charts[id]; }
  }
  function canvasFor(fig, id) {
    var wrap = $('.ixg-canvas-wrap', fig) || $('.ixg-plot', fig);
    var canvas = $('canvas', wrap);
    if (!canvas) {
      canvas = document.createElement('canvas');
      canvas.id = 'ixg-canvas-' + id;
      wrap.appendChild(canvas);
    }
    return canvas;
  }
  function setEmpty(fig, isEmpty) {
    var plot = $('.ixg-plot', fig);
    var empty = $('.ixg-empty', fig);
    if (isEmpty) {
      if (!empty) {
        empty = document.createElement('div');
        empty.className = 'ixg-empty';
        empty.textContent = t('noData', 'No activities match this selection yet.');
        fig.insertBefore(empty, plot);
      }
      plot.hidden = true;
    } else {
      if (empty) { empty.parentNode.removeChild(empty); }
      plot.hidden = false;
    }
  }
  function setAria(canvas, label) {
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', label);
  }

  /* ── Tablas accesibles (misma información que el gráfico) ───── */
  function renderTable(fig, columns, rows) {
    var wrap = $('.ixg-table-wrap', fig);
    if (!wrap) {
      wrap = document.createElement('div');
      wrap.className = 'ixg-table-wrap';
      wrap.hidden = true;
      fig.appendChild(wrap);
    }
    var html = '<table class="ixg-table"><thead><tr>';
    columns.forEach(function (c) { html += '<th' + (c.num ? ' class="ixg-num"' : '') + ' scope="col">' + esc(c.label) + '</th>'; });
    html += '</tr></thead><tbody>';
    if (!rows.length) {
      html += '<tr><td colspan="' + columns.length + '">' + esc(t('noData', 'No activities match this selection yet.')) + '</td></tr>';
    }
    rows.forEach(function (r) {
      html += '<tr>';
      columns.forEach(function (c) {
        var v = r[c.key];
        html += '<td' + (c.num ? ' class="ixg-num"' : '') + '>' + esc(c.num ? fmt(v) : v) + '</td>';
      });
      html += '</tr>';
    });
    html += '</tbody></table>';
    wrap.innerHTML = html;
  }
  function wireTableToggles() {
    $all('.ixg-fig').forEach(function (fig) {
      var btn = $('[data-ixg-toggle-table]', fig);
      if (!btn || btn.__wired) { return; }
      btn.__wired = true;
      btn.addEventListener('click', function () {
        var wrap = $('.ixg-table-wrap', fig);
        var plot = $('.ixg-plot', fig);
        if (!wrap) { return; }
        var showTable = wrap.hidden;
        wrap.hidden = !showTable;
        if (plot) { plot.style.display = showTable ? 'none' : ''; }
        btn.textContent = showTable ? t('showChart', 'Show as chart') : t('showTable', 'Show as table');
        btn.setAttribute('aria-expanded', showTable ? 'true' : 'false');
      });
    });
  }

  /* ── Leyenda HTML (texto en tinta, nunca en el color de la serie) ── */
  function renderLegend(fig, items, opts) {
    var ul = $('.ixg-legend', fig);
    if (!ul) {
      ul = document.createElement('ul');
      ul.className = 'ixg-legend';
      ($('.ixg-plot--donut', fig) || $('.ixg-plot', fig)).appendChild(ul);
    }
    var total = 0;
    items.forEach(function (it) { total += Number(it.value) || 0; });
    ul.innerHTML = items.map(function (it) {
      var share = (opts && opts.share && total) ? ' · ' + Math.round(100 * it.value / total) + '%' : '';
      return '<li><span class="ixg-legend-name"><span class="ixg-swatch" style="background:' + it.color + '"></span><span title="' + esc(it.label) + '">' + esc(it.label) + '</span></span>' +
        '<span class="ixg-legend-val">' + fmt(it.value) + share + '</span></li>';
    }).join('');
  }

  /* ── Fábricas de gráficos ───────────────────────────────────── */
  function doughnut(fig, id, items, opts) {
    opts = opts || {};
    var rows = items.filter(function (it) { return (Number(it.value) || 0) > 0; });
    if (opts.total !== undefined && opts.total !== null) {
      var declared = rows.reduce(function (s, it) { return s + Number(it.value); }, 0);
      if (opts.total > declared) {
        rows = rows.concat([{ label: t('notSpecified', 'Not specified'), key: 'Unspecified', value: opts.total - declared, color: CFG.neutral || '#94A3B8' }]);
      }
    }
    setEmpty(fig, !rows.length);
    renderTable(fig, opts.columns || [{ key: 'label', label: opts.labelHeader || t('category', 'Category') }, { key: 'value', label: opts.valueHeader || t('activities', 'Activities'), num: true }], rows);
    if (!rows.length) { destroyChart(id); var l = $('.ixg-legend', fig); if (l) { l.innerHTML = ''; } return; }
    var total = rows.reduce(function (s, it) { return s + Number(it.value); }, 0);
    renderLegend(fig, rows, { share: true });
    var canvas = canvasFor(fig, id);
    setAria(canvas, (opts.aria || '') + ' ' + rows.map(function (r) { return r.label + ': ' + fmt(r.value); }).join(', '));
    destroyChart(id);
    charts[id] = new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels: rows.map(function (r) { return r.label; }),
        datasets: [{ data: rows.map(function (r) { return r.value; }), backgroundColor: rows.map(function (r) { return r.color; }), borderColor: '#FFFFFF', borderWidth: 2, hoverOffset: 4 }]
      },
      options: {
        cutout: '68%',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          tooltip: { callbacks: { label: function (c) { return ' ' + c.label + ': ' + fmt(c.parsed) + ' (' + Math.round(100 * c.parsed / total) + '%)'; } } },
          ixgCenterText: { text: fmt(total), sub: opts.centerSub || '', size: 20 }
        }
      },
      plugins: [centerText]
    });
  }

  function bars(fig, id, items, series, opts) {
    /* items: [{key,label,...}], series: [{key, label, color}] */
    opts = opts || {};
    var rows = items.filter(function (it) {
      return series.some(function (s) { return (Number(it[s.key]) || 0) > 0; });
    });
    setEmpty(fig, !rows.length);
    var columns = [{ key: 'label', label: opts.labelHeader || t('category', 'Category') }].concat(series.map(function (s) { return { key: s.key, label: s.label, num: true }; }));
    renderTable(fig, columns, rows);
    if (!rows.length) { destroyChart(id); return; }
    var canvas = canvasFor(fig, id);
    var wrap = canvas.parentNode;
    wrap.style.height = Math.max(160, 28 * rows.length + 40) + 'px';
    setAria(canvas, (opts.aria || '') + ' ' + rows.map(function (r) { return r.label + ': ' + series.map(function (s) { return s.label + ' ' + fmt(r[s.key] || 0); }).join(', '); }).join('; '));
    if (series.length > 1) {
      var lg = $('.ixg-legend--inline', fig);
      if (!lg) { lg = document.createElement('ul'); lg.className = 'ixg-legend ixg-legend--inline'; $('figcaption', fig).appendChild(lg); }
      lg.innerHTML = series.map(function (s) { return '<li><span class="ixg-legend-name"><span class="ixg-swatch" style="background:' + s.color + '"></span><span>' + esc(s.label) + '</span></span></li>'; }).join('');
    }
    destroyChart(id);
    var stacked = series.length > 1 && opts.stacked !== false;
    charts[id] = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: rows.map(function (r) { return opts.shortLabels ? shortKey(r.key || r.label) : r.label; }),
        datasets: series.map(function (s, si) {
          return {
            label: s.label,
            data: rows.map(function (r) { return Number(r[s.key]) || 0; }),
            backgroundColor: s.color || rows.map(function (r) { return opts.colorFor ? opts.colorFor(r) : (CFG.action || '#0069B4'); }),
            borderColor: '#FFFFFF',
            borderWidth: stacked ? { left: si === 0 ? 0 : 2 } : 0,
            borderSkipped: false,
            borderRadius: stacked ? (si === series.length - 1 ? { topRight: 4, bottomRight: 4 } : 0) : 4,
            barThickness: 16,
            maxBarThickness: 18
          };
        })
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: { right: 44 } },
        scales: {
          x: { stacked: stacked, beginAtZero: true, grid: { color: CFG.ruleSoft || '#E6EEF6', drawTicks: false }, border: { display: false }, ticks: { precision: 0, maxTicksLimit: 6 } },
          y: { stacked: stacked, grid: { display: false }, border: { display: false }, ticks: { autoSkip: false, callback: function (v) { var l = this.getLabelForValue(v); return l.length > 34 ? l.slice(0, 32) + '…' : l; } } }
        },
        plugins: {
          tooltip: { callbacks: { title: function (its) { return rows[its[0].dataIndex].label; }, label: function (c) { return ' ' + c.dataset.label + ': ' + fmt(c.parsed.x); } } },
          ixgBarValues: { enabled: true }
        }
      },
      plugins: [barValueLabels]
    });
  }

  function gauge(fig, id, value, label) {
    /* value: 0..100 o null */
    var canvas = canvasFor(fig, id);
    var v = (value === null || value === undefined) ? null : Math.max(0, Math.min(100, Number(value)));
    setAria(canvas, label + ': ' + (v === null ? t('noData', 'no data') : pct(v)));
    destroyChart(id);
    charts[id] = new Chart(canvas, {
      type: 'doughnut',
      data: { datasets: [{ data: v === null ? [0, 100] : [v, 100 - v], backgroundColor: [CFG.action || '#0069B4', CFG.ruleSoft || '#E6EEF6'], borderWidth: 0, borderRadius: v === null ? 0 : 6 }] },
      options: {
        rotation: -90, circumference: 180, cutout: '72%', responsive: true, maintainAspectRatio: false,
        plugins: { tooltip: { enabled: false } }
      }
    });
  }

  /* ── Mapa ───────────────────────────────────────────────────── */
  function map(fig, id, points, opts) {
    opts = opts || {};
    var el = $('.ixg-plot--map', fig);
    if (!el || !window.L) { return; }
    var rows = (points || []).filter(function (p) { return p.lat !== null && p.lat !== undefined && p.lon !== null && p.lon !== undefined; });
    renderTable(fig, [{ key: 'country', label: t('memberState', 'Member State') }, { key: 'region', label: t('region', 'Region') }, { key: 'activities', label: t('activities', 'Activities'), num: true }], rows);
    var empty = $('.ixg-empty', fig);
    if (!rows.length) {
      if (!empty) { empty = document.createElement('div'); empty.className = 'ixg-empty'; empty.textContent = t('noData', 'No activities match this selection yet.'); fig.insertBefore(empty, el); }
      el.hidden = true;
      return;
    }
    if (empty) { empty.parentNode.removeChild(empty); }
    el.hidden = false;
    if (!maps[id]) {
      var m = L.map(el, { center: [18, 10], zoom: 2, minZoom: 1, scrollWheelZoom: false, zoomControl: true, attributionControl: true });
      L.tileLayer(CFG.basemap.url, { attribution: CFG.basemap.attribution, maxZoom: CFG.basemap.max_zoom || 16 }).addTo(m);
      maps[id] = { map: m, layer: L.layerGroup().addTo(m) };
    }
    var layer = maps[id].layer;
    layer.clearLayers();
    var max = rows.reduce(function (mx, p) { return Math.max(mx, Number(p.activities) || 0); }, 1);
    rows.forEach(function (p) {
      var n = Number(p.activities) || 0;
      var radius = Math.max(4, Math.min(24, 4 + 20 * Math.sqrt(n / max)));
      var html = '<div class="ixg-popup-title">' + esc(p.country) + '</div>' +
        '<div><strong>' + fmt(n) + '</strong> ' + esc(t('activities', 'activities').toLowerCase()) + '</div>' +
        (p.region ? '<div class="ixg-popup-meta">' + esc(p.region) + '</div>' : '');
      L.circleMarker([p.lat, p.lon], { radius: radius, fillColor: CFG.action || '#0069B4', color: '#FFFFFF', weight: 1.5, opacity: 1, fillOpacity: 0.7 })
        .bindPopup(html, { className: 'ixg-popup' })
        .addTo(layer);
    });
    setTimeout(function () { maps[id].map.invalidateSize(); }, 50);
  }

  /* ── Render de cada sección ─────────────────────────────────── */
  function tile(id, value, opts) {
    var el = document.getElementById(id);
    if (!el) { return; }
    var empty = value === null || value === undefined;
    el.textContent = empty ? '–' : fmt(value);
    el.classList.toggle('is-empty', empty);
    if (opts && opts.labelId) {
      var l = document.getElementById(opts.labelId);
      if (l && opts.label) { l.textContent = opts.label; }
    }
  }
  function activitiesLabel(base, n) {
    if (n === null || n === undefined) { return base; }
    return base + ' · ' + fmt(n) + ' ' + t('activitiesLower', 'activities');
  }

  function renderOverview(stats) {
    var ov = stats.overview || {};
    var dim = get(stats, 'scope.dimension', 'priority_area');
    tile('ixg-tile-activities', ov.activities);
    tile('ixg-tile-ms', ov.member_states_impacted);
    tile('ixg-tile-institutions', ov.institutions);
    tile('ixg-tile-pending', ov.pending);

    var fig = $('#ixg-fig-dimension');
    if (fig) {
      var items = (ov.by_dimension || []).map(function (it) { return { label: it.label || it.key, value: it.count, color: dimColor(it, dim) }; });
      doughnut(fig, 'dimension', items, { aria: t('activitiesPer', 'Activities per') + ' ' + dimLabel(dim), centerSub: t('activitiesLower', 'activities') });
    }
    fig = $('#ixg-fig-region');
    if (fig) {
      var regions = (ov.by_region || []).map(function (r) { return { key: r.key, label: r.key, member_states: r.member_states, activities: r.activities }; });
      bars(fig, 'region', regions, [{ key: 'member_states', label: t('memberStates', 'Member States'), color: CFG.action }], { labelHeader: t('region', 'Region'), aria: t('memberStatesPerRegion', 'Member States impacted per region') });
    }
    fig = $('#ixg-fig-map');
    if (fig) { map(fig, 'overview', ov.map || []); }
    fig = $('#ixg-fig-biennium');
    if (fig) {
      var bi = (ov.by_biennium || []).map(function (b) { return { key: b.key, label: b.key, count: b.count }; });
      bars(fig, 'biennium', bi, [{ key: 'count', label: t('activities', 'Activities'), color: CFG.action }], { labelHeader: t('biennium', 'Biennium'), aria: t('activitiesPerBiennium', 'Activities per biennium') });
    }
    fig = $('#ixg-fig-institutions');
    if (fig) {
      var inst = (ov.top_institutions || []).map(function (i) { return { key: i.name, label: i.name, count: i.count }; });
      bars(fig, 'institutions', inst, [{ key: 'count', label: t('activities', 'Activities'), color: CFG.action }], { labelHeader: t('institution', 'Institution'), aria: t('topInstitutions', 'Institutions with most activities') });
    }
    var unresolved = $('#ixg-unresolved');
    if (unresolved) {
      var list = ov.unresolved_member_states || [];
      unresolved.hidden = !list.length;
      if (list.length) { unresolved.textContent = t('unresolved', 'Names without a known Member State') + ': ' + list.join(', '); }
    }
  }

  function dimLabel(dim) {
    if (dim === 'output') { return t('output', 'output'); }
    if (dim === 'key_activity') { return t('keyActivity', 'key activity'); }
    return t('priorityArea', 'priority area');
  }

  function renderKpi1(stats) {
    var k = stats.kpi_1 || {};
    var dim = get(stats, 'scope.dimension', 'priority_area');
    tile('ixg-tile-kp', k.knowledge_products);
    tile('ixg-tile-sp', k.scientific_products);
    setSub('ixg-sub-kp', activitiesLabel(t('knowledgeProducts', 'Knowledge products'), k.active_knowledge_activities !== undefined ? k.active_knowledge_activities : k.active_activities));
    setSub('ixg-sub-sp', activitiesLabel(t('scientificProducts', 'Scientific products'), k.active_scientific_activities !== undefined ? k.active_scientific_activities : k.active_activities));
    var fig = $('#ixg-fig-kpi1-dim');
    if (fig) {
      bars(fig, 'kpi1dim', k.by_dimension || [], [
        { key: 'knowledge', label: t('knowledgeProducts', 'Knowledge products'), color: CFG.deep },
        { key: 'scientific', label: t('scientificProducts', 'Scientific products'), color: CFG.categorical[5] || '#0891B2' }
      ], { labelHeader: dimLabel(dim), aria: t('productsPer', 'Products per') + ' ' + dimLabel(dim), shortLabels: true });
    }
    fig = $('#ixg-fig-kpi1-kt');
    if (fig) {
      doughnut(fig, 'kpi1kt', typeItems(k.knowledge_by_type, CFG.types.knowledge_product_type), { aria: t('knowledgeProductsPerType', 'Knowledge products per type'), valueHeader: t('products', 'Products'), centerSub: t('products', 'products').toLowerCase() });
    }
    fig = $('#ixg-fig-kpi1-st');
    if (fig) {
      doughnut(fig, 'kpi1st', typeItems(k.scientific_by_type, CFG.types.scientific_product_type), { aria: t('scientificProductsPerType', 'Scientific products per type'), valueHeader: t('products', 'Products'), centerSub: t('products', 'products').toLowerCase() });
    }
  }
  function typeItems(list, canon) {
    /* Hasta 8 tipos con color propio; el resto se pliega en "Other" */
    var items = (list || []).map(function (it) {
      return { label: it.label || it.key, key: it.key, value: it.products !== undefined ? it.products : (it.individuals !== undefined ? it.individuals : (it.materials !== undefined ? it.materials : (it.groups !== undefined ? it.groups : it.count))), activities: it.activities, color: typeColor(it.key, canon) };
    }).filter(function (it) { return (Number(it.value) || 0) > 0; });
    var named = items.filter(function (it) { return it.color !== (CFG.neutral || '#94A3B8'); });
    var others = items.filter(function (it) { return it.color === (CFG.neutral || '#94A3B8'); });
    named.sort(function (a, b) { return b.value - a.value; });
    if (named.length > 8) {
      others = others.concat(named.slice(8));
      named = named.slice(0, 8);
    }
    if (others.length) {
      var sum = others.reduce(function (s, it) { return s + Number(it.value); }, 0);
      var label = others.length === 1 ? others[0].label : t('other', 'Other') + ' (' + others.length + ')';
      named.push({ label: label, key: 'Other', value: sum, color: CFG.neutral || '#94A3B8' });
    }
    return named;
  }
  function setSub(id, text) { var el = document.getElementById(id); if (el) { el.textContent = text; } }

  function renderPeopleKpi(stats, key, prefix, labels) {
    var k = stats[key] || {};
    var dim = get(stats, 'scope.dimension', 'priority_area');
    tile(prefix + '-tile', k.individuals);
    setSub(prefix + '-sub', activitiesLabel(labels.individuals, k.active_activities));
    var gf = $('#' + prefix + '-gauge-female');
    if (gf) { gauge(gf, prefix + 'gf', k.pct_female, t('women', 'women')); setSub(prefix + '-gauge-female-n', pct(k.pct_female)); setSub(prefix + '-gauge-female-l', t('women', 'women') + ' · ' + fmt(k.female)); }
    var gy = $('#' + prefix + '-gauge-youth');
    if (gy) { gauge(gy, prefix + 'gy', k.pct_youth, t('youth', 'youth')); setSub(prefix + '-gauge-youth-n', pct(k.pct_youth)); setSub(prefix + '-gauge-youth-l', t('youthRange', 'youth, 18–35') + ' · ' + fmt(k.youth)); }
    var fig = $('#' + prefix + '-fig-dim');
    if (fig) {
      bars(fig, prefix + 'dim', k.by_dimension || [], [{ key: 'individuals', label: labels.individuals, color: null }], { labelHeader: dimLabel(dim), aria: labels.individuals + ' ' + t('per', 'per') + ' ' + dimLabel(dim), colorFor: function (r) { return dimColor(r, dim); }, shortLabels: true });
    }
    fig = $('#' + prefix + '-fig-type');
    if (fig && k.by_activity_type) {
      doughnut(fig, prefix + 'type', typeItems(k.by_activity_type, CFG.types.knowledge_activity_type), { aria: t('individualsPerActivityType', 'Individuals per knowledge generating activity'), valueHeader: t('individuals', 'Individuals'), centerSub: t('individuals', 'individuals').toLowerCase(), total: k.individuals });
    }
  }

  function renderKpi34(stats) {
    var k3 = stats.kpi_3 || {};
    var k4 = stats.kpi_4 || {};
    var dim = get(stats, 'scope.dimension', 'priority_area');
    tile('ixg-tile-tm', k3.materials);
    setSub('ixg-sub-tm', activitiesLabel(t('trainingMaterials', 'Training materials and courses'), k3.active_activities));
    tile('ixg-tile-cu', k4.curricula);
    setSub('ixg-sub-cu', activitiesLabel(t('curricula', 'Curricula produced or revised'), k4.active_activities));
    var fig = $('#ixg-fig-kpi3-type');
    if (fig) {
      doughnut(fig, 'kpi3type', typeItems(k3.by_type, CFG.types.training_type), { aria: t('trainingPerType', 'Training material per type'), valueHeader: t('materials', 'Materials'), centerSub: t('materials', 'materials').toLowerCase() });
    }
    fig = $('#ixg-fig-kpi34-dim');
    if (fig) {
      var rows = mergeDims([k3.by_dimension || [], k4.by_dimension || []], ['materials', 'curricula']);
      bars(fig, 'kpi34dim', rows, [
        { key: 'materials', label: t('trainingMaterials', 'Training materials and courses'), color: CFG.deep },
        { key: 'curricula', label: t('curricula', 'Curricula'), color: CFG.categorical[1] || '#D97706' }
      ], { labelHeader: dimLabel(dim), aria: t('materialsAndCurriculaPer', 'Training materials and curricula per') + ' ' + dimLabel(dim), stacked: false, shortLabels: true });
    }
  }
  function mergeDims(lists, keys) {
    var byKey = {};
    var order = [];
    lists.forEach(function (list, li) {
      list.forEach(function (it) {
        if (!byKey[it.key]) { byKey[it.key] = { key: it.key, label: it.label || it.key }; order.push(it.key); }
        byKey[it.key][keys[li]] = it[keys[li]] !== undefined ? it[keys[li]] : it.count;
      });
    });
    return order.map(function (k) { return byKey[k]; });
  }

  function renderKpi68(stats) {
    var k6 = stats.kpi_6 || {};
    var k8 = stats.kpi_8 || {};
    tile('ixg-tile-tb', k6.member_states_reported);
    setSub('ixg-sub-tb', activitiesLabel(t('transboundaryMs', 'Member States supported in transboundary water management, as reported'), k6.active_activities));
    tile('ixg-tile-sg', k8.stakeholder_groups);
    setSub('ixg-sub-sg', activitiesLabel(t('stakeholderGroups', 'Stakeholder groups with strengthened capacity'), k8.active_activities));
    var fig = $('#ixg-fig-kpi6-map');
    if (fig) { map(fig, 'kpi6', k6.map || []); }
    fig = $('#ixg-fig-kpi8-type');
    if (fig) {
      doughnut(fig, 'kpi8type', typeItems(k8.by_type, CFG.types.stakeholder_group_type), { aria: t('stakeholderGroupsByType', 'Stakeholder groups by type'), valueHeader: t('groups', 'Groups'), centerSub: t('groups', 'groups').toLowerCase() });
    }
  }

  function renderOutputDetail(stats) {
    var fig = $('#ixg-fig-produced');
    if (fig) {
      bars(fig, 'produced', stats.produced_by_dimension || [], [
        { key: 'knowledge', label: t('knowledgeProducts', 'Knowledge products'), color: CFG.deep },
        { key: 'scientific', label: t('scientificProducts', 'Scientific products'), color: CFG.categorical[5] || '#0891B2' },
        { key: 'training', label: t('trainingMaterials', 'Training materials and courses'), color: CFG.categorical[1] || '#D97706' },
        { key: 'curricula', label: t('curricula', 'Curricula'), color: CFG.categorical[2] || '#7C3AED' }
      ], { labelHeader: t('keyActivity', 'Key activity'), aria: t('productsPerKeyActivity', 'Products per key activity'), shortLabels: true });
    }
    fig = $('#ixg-fig-reached');
    if (fig) {
      bars(fig, 'reached', stats.reached_by_dimension || [], [
        { key: 'knowledge_improved', label: t('knowledgeImproved', 'Knowledge improved'), color: CFG.deep },
        { key: 'awareness_raised', label: t('awarenessRaised', 'Awareness raised'), color: CFG.categorical[1] || '#D97706' }
      ], { labelHeader: t('keyActivity', 'Key activity'), aria: t('stakeholdersPerKeyActivity', 'Stakeholders reached per key activity'), stacked: false, shortLabels: true });
    }
    var list = $('#ixg-key-activities');
    if (list) {
      var kas = (stats.options && stats.options.key_activities) || [];
      list.innerHTML = kas.map(function (ka) { return '<li><strong>' + esc(ka.code) + '</strong> ' + esc(ka.title) + '</li>'; }).join('');
      list.parentNode.hidden = !kas.length;
    }
  }

  function renderStrip(stats) {
    var strip = $('#ixg-strip');
    if (!strip) { return; }
    var outputs = get(stats, 'overview.by_output', []);
    var bar = $('.ixg-strip-bar', strip);
    var legend = $('.ixg-strip-legend', strip);
    if (!outputs.length) { strip.hidden = true; return; }
    strip.hidden = false;
    var total = 0;
    var perPa = {};
    outputs.forEach(function (o) { total += Number(o.count) || 0; perPa[o.pa] = (perPa[o.pa] || 0) + (Number(o.count) || 0); });
    var lastPa = null;
    var alt = false;
    bar.innerHTML = outputs.map(function (o) {
      var n = Number(o.count) || 0;
      var cls = 'ixg-strip-seg' + (o.pa !== lastPa ? ' is-pa-start' : '') + (alt ? ' is-alt' : '');
      if (o.pa !== lastPa) { alt = false; } else { alt = !alt; }
      lastPa = o.pa;
      var url = (CFG.routes.output || '').replace('__CODE__', encodeURIComponent(o.key));
      return '<a class="' + cls + '" data-pa="' + esc(o.pa) + '" href="' + esc(url) + '" style="flex-grow:' + Math.max(n, 1) + '" title="' + esc(o.key + ' · ' + fmt(n) + ' ' + t('activitiesLower', 'activities')) + '" aria-label="' + esc(t('output', 'Output') + ' ' + o.key + ': ' + fmt(n) + ' ' + t('activitiesLower', 'activities')) + '"></a>';
    }).join('');
    var h2 = $('h2', strip);
    if (h2) { h2.textContent = fmt(total) + ' ' + t('activitiesAcross', 'activities across') + ' ' + outputs.length + ' ' + t('outputs', 'outputs'); }
    legend.innerHTML = (CFG.priorityAreas || []).map(function (pa) {
      var url = (CFG.routes.pa || '').replace('__CODE__', encodeURIComponent(pa.code));
      var short = (CFG.paShort && CFG.paShort[pa.code]) || pa.label || pa.code;
      return '<a href="' + esc(url) + '" style="flex-grow:' + Math.max(perPa[pa.code] || 0, 1) + '"><span class="ixg-swatch" style="background:' + paColor(pa.code) + '"></span><span class="ixg-strip-legend-text">' + esc(pa.code.replace('PA', 'PA ') + ' \u00b7 ' + short) + '</span><strong class="ixg-num">' + fmt(perPa[pa.code] || 0) + '</strong></a>';
    }).join('');
  }

  var SECTION_RENDERERS = {
    'ixg-overview': renderOverview,
    'ixg-kpi1': renderKpi1,
    'ixg-kpi2': function (s) { renderPeopleKpi(s, 'kpi_2', 'ixg-kpi2', { individuals: t('individualsImproved', 'Individuals with improved knowledge') }); },
    'ixg-kpi34': renderKpi34,
    'ixg-kpi5': function (s) { renderPeopleKpi(s, 'kpi_5', 'ixg-kpi5', { individuals: t('individualsReached', 'Individuals reached') }); },
    'ixg-kpi68': renderKpi68,
    'ixg-produced': renderOutputDetail,
    'ixg-reached': function () { /* lo pinta renderOutputDetail */ }
  };

  function render(stats) {
    DATA = stats || {};
    renderStrip(DATA);
    /* Todas las secciones de una vez: los datos ya están en la página y
       así el resultado no depende del scroll (los mapas se ajustan al
       hacerse visibles con invalidateSize). */
    $all('.ixg-section').forEach(function (sec) { renderSection(sec); });
    wireTableToggles();
    var status = $('#ixg-status');
    if (status) {
      var ov = DATA.overview || {};
      status.textContent = ov.activities === undefined ? '' : (fmt(ov.activities) + ' ' + t('activitiesLower', 'activities') + (DATA.filters && DATA.filters.biennium ? ' · ' + DATA.filters.biennium : ''));
    }
  }
  function renderSection(sec) {
    var fn = SECTION_RENDERERS[sec.id];
    if (!fn) { return; }
    try { fn(DATA); } catch (e) { if (window.console) { console.error('ihpix-progress: ' + sec.id, e); } }
    sec.__rendered = true;
    delete pending[sec.id];
  }
  function setupObserver() {
    if (!('IntersectionObserver' in window)) { observer = null; return; }
    observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) { return; }
        var sec = en.target;
        markIndex(sec.id);
        /* Leaflet necesita recalcular el tamaño si el mapa se creó fuera de pantalla */
        Object.keys(maps).forEach(function (id) {
          if (sec.contains(maps[id].map.getContainer())) { maps[id].map.invalidateSize(); }
        });
      });
    }, { rootMargin: '0px 0px -40% 0px', threshold: 0.05 });
    $all('.ixg-section').forEach(function (sec) { observer.observe(sec); });
  }
  function markIndex(id) {
    $all('.ixg-index a').forEach(function (a) {
      a.classList.toggle('is-active', a.getAttribute('href') === '#' + id);
    });
  }

  /* ── Filtros y recarga ──────────────────────────────────────── */
  function currentParams() {
    var p = { scope: CFG.scope, value: CFG.value || '' };
    var bi = $('#ixg-filter-biennium');
    var re = $('#ixg-filter-region');
    if (bi && bi.value) { p.biennium = bi.value; }
    if (re && re.value) { p.region = re.value; }
    return p;
  }
  function load(params) {
    var qs = Object.keys(params).filter(function (k) { return params[k] !== '' && params[k] !== null && params[k] !== undefined; })
      .map(function (k) { return encodeURIComponent(k) + '=' + encodeURIComponent(params[k]); }).join('&');
    var root = $('.ixg-body');
    if (root) { root.classList.add('ixg-loading'); }
    var status = $('#ixg-status');
    if (status) { status.textContent = t('loading', 'Updating…'); }
    return fetch(CFG.apiUrl + (qs ? '?' + qs : ''), { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
      .then(function (r) { if (!r.ok) { throw new Error('HTTP ' + r.status); } return r.json(); })
      .then(function (json) {
        if (!json || !json.success) { throw new Error('bad response'); }
        render(json.result);
        /* URL compartible */
        try {
          var url = window.location.pathname;
          var keep = [];
          if (params.biennium) { keep.push('biennium=' + encodeURIComponent(params.biennium)); }
          if (params.region) { keep.push('region=' + encodeURIComponent(params.region)); }
          if (keep.length) { url += '?' + keep.join('&'); }
          window.history.replaceState(null, '', url + window.location.hash);
        } catch (e) { /* nada */ }
        var dl = $('#ixg-download');
        if (dl) { dl.href = CFG.apiUrl + (qs ? '?' + qs : ''); }
      })
      .catch(function (e) {
        if (status) { status.textContent = t('loadError', 'The data could not be updated. Reload the page to try again.'); }
        if (window.console) { console.error('ihpix-progress', e); }
      })
      .then(function () { if (root) { root.classList.remove('ixg-loading'); } });
  }
  function wireFilters() {
    ['#ixg-filter-biennium', '#ixg-filter-region'].forEach(function (sel) {
      var el = $(sel);
      if (el) { el.addEventListener('change', function () { load(currentParams()); }); }
    });
    $all('[data-ixg-scope-select]').forEach(function (el) {
      el.addEventListener('change', function () {
        var opt = el.options[el.selectedIndex];
        var url = opt && opt.getAttribute('data-url');
        if (url) { window.location.href = url; }
      });
    });
    $all('.ixg-index a').forEach(function (a) {
      a.addEventListener('click', function () { markIndex(a.getAttribute('href').slice(1)); });
    });
  }

  function init() {
    CFG = readJSON('ihpix-progress-config') || {};
    CFG.categorical = CFG.categorical || [];
    CFG.types = CFG.types || {};
    CFG.routes = CFG.routes || {};
    CFG.basemap = CFG.basemap || { url: '', attribution: '' };
    /* Mapa output → PA para colorear por PA en el ámbito "pa" */
    CFG.outputPa = {};
    Object.keys(CFG.outputsByPa || {}).forEach(function (pa) {
      (CFG.outputsByPa[pa] || []).forEach(function (o) { CFG.outputPa[o.code || o] = pa; });
    });
    var stats = readJSON('ihpix-progress-data') || {};
    if (!$('.ixg')) { return; }
    setupChartDefaults();
    setupObserver();
    wireFilters();
    render(stats);
    var first = $('.ixg-section');
    if (first) { markIndex(first.id); }
    if (window.location.hash) {
      var target = document.getElementById(window.location.hash.slice(1));
      if (target && target.classList.contains('ixg-section')) { markIndex(target.id); }
    }
  }

  window.IhpixProgress = { init: init, load: load, render: render };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window, document);
