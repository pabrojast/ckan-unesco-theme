// Capturas y comprobaciones del formulario de reporte rediseñado y de los
// dashboards de progreso IHP-IX contra un CKAN real (dev por defecto, o un
// `ckan run` en el pod expuesto por `kubectl port-forward`).
//
//   NODE_PATH=/ruta/privada/node_modules IHPIX_PW_TOKENS=/ruta/privada/tokens.json \
//     IHPIX_PW_BASE=http://127.0.0.1:5001 node scripts/playwright/ihpix_progress.js
//
// tokens.json = {"editor": "<token>", "sysadmin": "<token>"} (api_token_create
// desde el pod; revocar al terminar). Sólo hace GET: no crea datos.
// Variables opcionales: IHPIX_PW_OUT (carpeta de capturas, default ./ihpix-pw-out);
// IHPIX_PW_TUNNEL (comando que abre el túnel, p. ej. "kubectl … port-forward pod/X 5001:5001")
// e IHPIX_PW_SERVER (comando que (re)arranca el servidor en el pod): si el sitio
// deja de responder, el script los relanza solo (el port-forward se cae con
// muchas peticiones en paralelo).
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const TUNNEL_CMD = process.env.IHPIX_PW_TUNNEL || '';
const SERVER_CMD = process.env.IHPIX_PW_SERVER || '';
let tunnelProc = null;
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
async function healthy() {
  try { const r = await fetch(BASE_URL() + '/ihpix', { signal: AbortSignal.timeout(20000), redirect: 'manual' }); return r.status === 200; } catch (e) { return false; }
}
function startProc(cmd, label) {
  const p = spawn(cmd, { shell: true, stdio: ['ignore', 'ignore', 'pipe'] });
  p.stderr.on('data', () => {});
  p.on('exit', c => console.log('   [' + label + ' terminó con código ' + c + ']'));
  return p;
}
async function ensureUp() {
  if (await healthy()) return true;
  console.log('   [sitio sin respuesta: relanzando túnel' + (SERVER_CMD ? ' y, si hace falta, servidor' : '') + ']');
  if (TUNNEL_CMD) { if (tunnelProc) { try { tunnelProc.kill(); } catch (e) {} } await sleep(1000); tunnelProc = startProc(TUNNEL_CMD, 'túnel'); await sleep(4000); }
  for (let i = 0; i < 30; i++) {
    if (await healthy()) return true;
    if (i === 5 && SERVER_CMD) { startProc(SERVER_CMD, 'servidor'); }
    if (i === 12 && TUNNEL_CMD) { try { tunnelProc.kill(); } catch (e) {} tunnelProc = startProc(TUNNEL_CMD, 'túnel'); }
    await sleep(6000);
  }
  return false;
}
function BASE_URL() { return BASE; }
const BASE = process.env.IHPIX_PW_BASE || 'https://data.dev-wins.com';
const OUT = process.env.IHPIX_PW_OUT || path.join(process.cwd(), 'ihpix-pw-out');
fs.mkdirSync(OUT, { recursive: true });
const tokens = JSON.parse(fs.readFileSync(process.env.IHPIX_PW_TOKENS || path.join(process.cwd(), 'tokens.json'), 'utf8'));
const out = { base: BASE, steps: [], console_errors: {}, http_errors: {} };
const step = (name, ok, info) => { out.steps.push({ name, ok: !!ok, info: info === undefined ? '' : info }); console.log((ok ? 'OK   ' : 'FAIL ') + name + (info !== undefined ? '  ' + JSON.stringify(info).slice(0, 300) : '')); };

async function newPage(browser, token, opts = {}) {
  await ensureUp();
  const ctx = await browser.newContext({ viewport: opts.viewport || { width: 1366, height: 900 }, locale: opts.locale || 'en-US', ignoreHTTPSErrors: true, reducedMotion: 'reduce' });
  await ctx.route('**/*', route => {
    const url = route.request().url();
    if (/blob\.core\.windows\.net/.test(url)) return route.abort();
    if (url.startsWith(BASE)) return route.continue({ headers: { ...route.request().headers(), Authorization: token } });
    return route.continue();
  });
  const page = await ctx.newPage();
  const key = opts.key || 'page';
  out.console_errors[key] = out.console_errors[key] || [];
  out.http_errors[key] = out.http_errors[key] || [];
  page.on('console', m => {
    if (m.type() !== 'error') return;
    const loc = (m.location() || {}).url || '';
    if (/blob\.core\.windows\.net/.test(loc) || /blob\.core\.windows\.net|net::ERR_ABORTED/.test(m.text())) return;   // avatar externo con SAS caducada
    out.console_errors[key].push(m.text().slice(0, 200) + (loc ? '  @ ' + loc.slice(0, 100) : ''));
  });
  page.on('pageerror', e => out.console_errors[key].push('pageerror: ' + String(e).slice(0, 200)));
  page.on('response', r => { const u = r.url(); if (u.startsWith(BASE) && r.status() >= 400) out.http_errors[key].push(r.status() + ' ' + u.replace(BASE, '').slice(0, 140)); });
  page.on('requestfailed', r => { const u = r.url(); if (u.startsWith(BASE)) out.http_errors[key].push('failed ' + (r.failure() || {}).errorText + ' ' + u.replace(BASE, '').slice(0, 140)); });

  return { ctx, page };
}
async function scrollThrough(page) {
  await page.evaluate(async () => {
    const h = document.body.scrollHeight;
    for (let y = 0; y < h; y += 500) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 120)); }
    window.scrollTo(0, 0);
  });
  await page.waitForTimeout(600);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    // ───────────── 1. Formulario de reporte (editor) ─────────────
    let { ctx, page } = await newPage(browser, tokens.editor, { key: 'report' });
    await page.goto(BASE + '/ihpix/report?output=1.3', { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.waitForSelector('#ihpix-report-form', { timeout: 60000 });
    await page.waitForFunction(() => window.IhpixReport && window.IhpixForms, null, { timeout: 60000 }).catch(() => {});
    await page.waitForTimeout(800);
    const info = await page.evaluate(() => ({
      progress: (document.getElementById('ihpix-progress-text') || {}).textContent,
      flagships: document.querySelectorAll('input[name="flagships"]').length,
      trainingTypes: document.querySelectorAll('input[name="training_type"]').length,
      knowledgeTypes: document.querySelectorAll('input[name="knowledge_product_type"]').length,
      gatesChecked: document.querySelectorAll('[id^="ihpix-gate-"] .ihpix-yesno input:checked').length,
      gates: document.querySelectorAll('fieldset[id^="ihpix-gate-"]').length,
      kaOptions: Array.from(document.querySelectorAll('#ihpix-field-key-activity-code option')).filter(o => o.value).length,
      outputValue: (document.getElementById('ihpix-field-output') || {}).value,
      reviewRows: document.querySelectorAll('#ihpix-review-body tr').length,
      navItems: document.querySelectorAll('.ihpix-section-nav a').length,
      numbered: document.querySelectorAll('.ihpix-qnum').length
    }));
    step('report: carga y prefill output 1.3', info.outputValue === '1.3', info);
    step('report: 23 obligatorios en el progreso', /\/ 23/.test(info.progress || ''), info.progress);
    step('report: 18 flagships', info.flagships === 18, info.flagships);
    step('report: 12 tipos de formación', info.trainingTypes === 12, info.trainingTypes);
    step('report: 9 tipos de producto de conocimiento', info.knowledgeTypes === 9, info.knowledgeTypes);
    step('report: 13 puertas Sí/No (5 generales + 8 KPI) sin valor por defecto', info.gates === 13 && info.gatesChecked === 0, { gates: info.gates, checked: info.gatesChecked });
    step('report: key activities filtradas por output 1.3', info.kaOptions > 0 && info.kaOptions < 20, info.kaOptions);
    step('report: tabla de revisión con 7 secciones', info.reviewRows === 7, info.reviewRows);
    step('report: carril con 8 entradas', info.navItems === 8, info.navItems);
    // Interacción: una puerta en "sí" abre la subpregunta y la revisión cambia
    await page.click('#ihpix-gate-kpi-2 label.is-yes');
    await page.waitForTimeout(300);
    const kpi2 = await page.evaluate(() => ({
      shown: !!document.querySelector('[data-conditional-on="kpi_2_active"].show'),
      reviewText: (document.getElementById('ihpix-review-summary') || {}).textContent
    }));
    step('report: "sí" en KPI 2 abre la subpregunta', kpi2.shown, kpi2);
    // Envío sin completar → resumen de errores con las puertas
    await page.click('#ihpix-report-submit-btn');
    await page.waitForTimeout(600);
    const errs = await page.evaluate(() => ({
      summaryShown: !!document.querySelector('#ihpix-error-summary.show'),
      items: document.querySelectorAll('#ihpix-error-summary li').length,
      gateErrors: Array.from(document.querySelectorAll('.ihpix-yesno-group.ihpix-report-field-error')).length
    }));
    step('report: envío incompleto muestra resumen y puertas en error', errs.summaryShown && errs.items > 0 && errs.gateErrors > 0, errs);
    await page.screenshot({ path: OUT + '/report-desktop.png', fullPage: true });
    await page.evaluate(() => { const r = document.getElementById('section-review'); if (r) r.scrollIntoView(); });
    await page.waitForTimeout(300);
    await page.screenshot({ path: OUT + '/report-review.png', fullPage: false });
    await ctx.close();

    // Móvil
    ({ ctx, page } = await newPage(browser, tokens.editor, { key: 'mobile', viewport: { width: 390, height: 844 } }));
    await page.goto(BASE + '/ihpix/report?output=1.3', { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.waitForSelector('#ihpix-report-form', { timeout: 60000 });
    await page.waitForTimeout(800);
    const mobile = await page.evaluate(() => ({ overflow: document.documentElement.scrollWidth - window.innerWidth, actionsSticky: getComputedStyle(document.querySelector('.ihpix-report-actions')).position }));
    step('report móvil: sin scroll horizontal', mobile.overflow <= 1, mobile);
    await page.screenshot({ path: OUT + '/report-mobile.png', fullPage: false });
    await page.evaluate(() => { const r = document.getElementById('section-5'); if (r) r.scrollIntoView(); });
    await page.waitForTimeout(300);
    await page.screenshot({ path: OUT + '/report-mobile-kpi.png', fullPage: false });
    await ctx.close();

    // RTL (árabe)
    ({ ctx, page } = await newPage(browser, tokens.editor, { key: 'rtl', locale: 'ar' }));
    await page.goto(BASE + '/ar/ihpix/report?output=1.3', { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.waitForSelector('#ihpix-report-form', { timeout: 60000 });
    await page.waitForTimeout(800);
    const rtl = await page.evaluate(() => ({ dir: document.documentElement.getAttribute('dir') || getComputedStyle(document.body).direction, overflow: document.documentElement.scrollWidth - window.innerWidth }));
    step('report RTL: dirección rtl y sin desbordes', rtl.dir === 'rtl' && rtl.overflow <= 1, rtl);
    await page.screenshot({ path: OUT + '/report-ar.png', fullPage: false });
    await ctx.close();

    // ───────────── 2. Dashboards de progreso ─────────────
    const scopes = [
      ['overall', '/ihpix/progress'],
      ['pa', '/ihpix/progress/pa/PA1'],
      ['output', '/ihpix/progress/output/1.3'],
      ['flagship', '/ihpix/progress/flagship/friend'],
      ['ctwg', '/ihpix/progress/ctwg/ecohydrology-and-water-quality']
    ];
    for (const [name, url] of scopes) {
      ({ ctx, page } = await newPage(browser, tokens.sysadmin, { key: 'progress-' + name }));
      await page.goto(BASE + url, { waitUntil: 'domcontentloaded', timeout: 90000 });
      await page.waitForSelector('.ixg', { timeout: 60000 });
      await page.waitForFunction(() => window.IhpixProgress && window.Chart && window.L, null, { timeout: 60000 }).catch(() => {});
      await scrollThrough(page);
      const p = await page.evaluate(() => ({
        canvases: document.querySelectorAll('canvas').length,
        activities: (document.getElementById('ixg-tile-activities') || {}).textContent,
        memberStates: (document.getElementById('ixg-tile-ms') || {}).textContent,
        kpi2: (document.getElementById('ixg-kpi2-tile') || {}).textContent,
        strip: document.querySelectorAll('.ixg-strip-seg').length,
        maps: document.querySelectorAll('.leaflet-container').length,
        markers: document.querySelectorAll('.leaflet-interactive').length,
        tables: document.querySelectorAll('.ixg-table').length,
        empties: document.querySelectorAll('.ixg-empty').length,
        produced: !!document.getElementById('ixg-produced')
      }));
      step('progress ' + name + ': tiles y gráficos', p.canvases >= 8 && /\d/.test(p.activities || '') && /\d/.test(p.kpi2 || ''), p);
      if (name === 'overall') step('progress overall: franja de 34 outputs', p.strip === 34, p.strip);
      if (name === 'output') step('progress output: paneles de key activity', p.produced, p.produced);
      step('progress ' + name + ': mapa con marcadores', p.maps >= 1 && p.markers > 0, { maps: p.maps, markers: p.markers });
      await page.screenshot({ path: OUT + '/progress-' + name + '.png', fullPage: true });
      if (name === 'overall') {
        // Filtro de bienio → fetch a la API y actualización de tiles
        const before = p.activities;
        const [resp] = await Promise.all([
          page.waitForResponse(r => r.url().indexOf('ihpix_progress_stats') !== -1, { timeout: 60000 }),
          page.selectOption('#ixg-filter-biennium', '2024-2025')
        ]);
        await page.waitForTimeout(800);
        const after = await page.evaluate(() => (document.getElementById('ixg-tile-activities') || {}).textContent);
        step('progress overall: filtro de bienio recarga vía API', resp.status() === 200 && after !== before, { status: resp.status(), before, after, url: page.url().replace(BASE, '') });
        // Tabla accesible
        await page.click('#ixg-fig-dimension [data-ixg-toggle-table]');
        const tableShown = await page.evaluate(() => { const w = document.querySelector('#ixg-fig-dimension .ixg-table-wrap'); return !!w && !w.hidden && w.querySelectorAll('tbody tr').length > 0; });
        step('progress overall: "Show as table" muestra la tabla', tableShown);
        await page.screenshot({ path: OUT + '/progress-overall-filtered.png', fullPage: false });
      }
      await ctx.close();
    }

    // Redirección del dashboard antiguo (sin seguirla: el Location lleva el
    // site_url absoluto, que en un túnel local no es el host de pruebas)
    ({ ctx, page } = await newPage(browser, tokens.sysadmin, { key: 'redirect' }));
    const r = await ctx.request.get(BASE + '/ihpix/dashboard?pa=PA2', { maxRedirects: 0, headers: { Authorization: tokens.sysadmin } });
    const loc = (r.headers() || {}).location || '';
    step('dashboard antiguo redirige al progreso de PA2', r.status() === 302 && /\/ihpix\/progress\/pa\/PA2$/.test(loc), { status: r.status(), location: loc.slice(0, 120) });
    await ctx.close();
  } catch (e) {
    step('excepción', false, String(e).slice(0, 300));
  } finally {
    await browser.close();
    if (tunnelProc) { try { tunnelProc.kill(); } catch (e) {} }
  }
  const consoleErrs = Object.values(out.console_errors).reduce((n, a) => n + a.length, 0);
  const httpErrs = Object.values(out.http_errors).reduce((n, a) => n + a.length, 0);
  step('sin errores de consola', consoleErrs === 0, out.console_errors);
  step('sin respuestas HTTP >= 400 ni peticiones fallidas', httpErrs === 0, out.http_errors);
  fs.writeFileSync(OUT + '/results.json', JSON.stringify(out, null, 2));
  const fails = out.steps.filter(s => !s.ok).length;
  console.log('\n' + (out.steps.length - fails) + '/' + out.steps.length + ' pasos OK · capturas en ' + OUT);
  process.exit(fails ? 1 : 0);
})();
