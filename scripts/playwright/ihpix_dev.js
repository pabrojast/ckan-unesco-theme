// Pruebas de navegador (Playwright) del ecosistema IHP-IX contra un CKAN real
// (por defecto dev). La sesión se consigue con tokens de API en la cabecera
// Authorization, sólo hacia el sitio: no se teclean contraseñas.
//
//   npm i playwright            # una vez (usa ~/.cache/ms-playwright)
//   IHPIX_PW_TOKENS=/ruta/privada/tokens.json node scripts/playwright/ihpix_dev.js
//
// tokens.json = {"editor": "<token de un editor no sysadmin>", "sysadmin": "<token>"}
// (api_token_create desde el pod; revocar al terminar). Variables opcionales:
//   IHPIX_PW_BASE   URL del sitio (default https://data.dev-wins.com)
//   IHPIX_PW_OUT    carpeta de capturas/results.json (default ./ihpix-pw-out)
//   LOCAL_KIT       ruta local de ihpix-forms.js para servirlo sobre la página
//                   (valida cambios del kit sin reconstruir la imagen)
// Crea un borrador de reporte y una publicación de prueba ("delete me"):
// limpiarlos después (ver docs/obsidian-vault/Testing.md).
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const BASE = process.env.IHPIX_PW_BASE || 'https://data.dev-wins.com';
const OUT = process.env.IHPIX_PW_OUT || path.join(process.cwd(), 'ihpix-pw-out');
fs.mkdirSync(OUT, { recursive: true });
const tokens = JSON.parse(fs.readFileSync(process.env.IHPIX_PW_TOKENS || path.join(process.cwd(), 'tokens.json'), 'utf8'));
const out = { steps: [], console_errors: {}, http_errors: {}, created: {} };
const step = (name, ok, info) => { out.steps.push({ name, ok: !!ok, info: info === undefined ? '' : info }); console.log((ok ? 'OK   ' : 'FAIL ') + name + (info !== undefined ? '  ' + JSON.stringify(info).slice(0, 300) : '')); };
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function newPage(browser, token, opts = {}) {
  const ctx = await browser.newContext({ viewport: opts.viewport || { width: 1366, height: 900 }, locale: opts.locale || 'en-US', ignoreHTTPSErrors: true });
  // Cabecera Authorization sólo hacia el sitio (no a CDNs/fuentes)
  await ctx.route('**/*', route => {
    const url = route.request().url();
    if (process.env.LOCAL_KIT && /\/webassets\/theme\/ihpix-forms\.js/.test(url)) {
      return route.fulfill({ path: process.env.LOCAL_KIT, contentType: 'application/javascript' });
    }
    if (url.startsWith(BASE)) return route.continue({ headers: { ...route.request().headers(), Authorization: token } });
    return route.continue();
  });
  const page = await ctx.newPage();
  const key = opts.key || 'page';
  out.console_errors[key] = out.console_errors[key] || [];
  out.http_errors[key] = out.http_errors[key] || [];
  page.on('console', m => { if (m.type() === 'error') out.console_errors[key].push(m.text().slice(0, 200)); });
  page.on('pageerror', e => out.console_errors[key].push('pageerror: ' + String(e).slice(0, 200)));
  page.on('response', r => { const u = r.url(); if (u.startsWith(BASE) && r.status() >= 400) out.http_errors[key].push(r.status() + ' ' + u.replace(BASE, '').slice(0, 120)); });
  return { ctx, page };
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    // ───────────── 1. Formulario de reporte (editor) ─────────────
    let { ctx, page } = await newPage(browser, tokens.editor, { key: 'report' });
    await page.goto(BASE + '/ihpix/report?output=1.3', { waitUntil: 'networkidle', timeout: 90000 });
    await page.waitForSelector('#ihpix-report-form', { timeout: 30000 });
    step('report: kit cargado (window.IhpixForms)', await page.evaluate(() => !!(window.IhpixForms && window.ihpixToast)));
    const counts = await page.evaluate(() => ({
      combobox: document.querySelectorAll('.ixf-combobox').length,
      multipicker: document.querySelectorAll('.ixf-mp').length,
      markdown: document.querySelectorAll('.ixf-md').length,
      counters: document.querySelectorAll('.ixf-counter').length,
      fieldsets: document.querySelectorAll('fieldset.ixf-fieldset').length,
      output: document.getElementById('ihpix-field-output').value,
      pa: document.getElementById('ihpix-field-pa') ? document.getElementById('ihpix-field-pa').value : document.querySelector('[name=priority_area]').value,
    }));
    step('report: componentes inicializados (contadores también en los textareas Markdown)', counts.combobox >= 2 && counts.multipicker === 1 && counts.markdown >= 3 && counts.counters >= 5, counts);
    step('report: ?output=1.3 prellena Output/PA', counts.output === '1.3' && counts.pa === 'PA1', { output: counts.output, pa: counts.pa });

    // Combobox de país: escribir y elegir con teclado
    const countryInput = page.locator('#ihpix-field-country').locator('xpath=ancestor::*[contains(@class,"ihpix-report-field")][1]').locator('.ixf-combobox-input');
    await countryInput.click(); await countryInput.fill('chil');
    await page.waitForSelector('.ixf-listbox:not([hidden]) .ixf-option[role=option]', { timeout: 10000 });
    const firstOpt = await page.locator('.ixf-listbox:not([hidden]) .ixf-option[role=option]').first().textContent();
    await countryInput.press('ArrowDown'); await countryInput.press('Enter');
    const country = await page.evaluate(() => document.getElementById('ihpix-field-country').value);
    step('report: combobox país con teclado', country === 'chile', { first: firstOpt && firstOpt.trim(), value: country });

    // MultiPicker de Member States: activar el gate Sí (regions_benefit), buscar, marcar, chip
    await page.locator('input[name=regions_benefit][value=yes]').check({ force: true });
    await page.waitForSelector('#ihpix-ms-picker .ixf-mp-search input:visible', { timeout: 10000 });
    const mp = page.locator('#ihpix-ms-picker');
    await mp.locator('.ixf-mp-search input').fill('braz');
    await mp.locator('.ixf-mp-list label:not([hidden]) input[type=checkbox]').first().check();
    const chips = await mp.locator('.ixf-chip').count();
    const msChecked = await page.evaluate(() => Array.from(document.querySelectorAll('#ihpix-ms-picker input[name=member_states]:checked')).map(i => i.value));
    step('report: MultiPicker Member States (chip + checkbox)', chips === 1 && msChecked.length === 1, { chips, msChecked });

    // Markdown: barra (negrita) + contador + preview
    const notes = page.locator('#ihpix-field-additional-notes');
    const notesId = 'ihpix-field-additional-notes';
    await page.evaluate(id => document.getElementById(id).scrollIntoView(), notesId);
    const mdWrap = notes.locator('xpath=ancestor::*[contains(@class,"ixf-md")][1]');
    await notes.click(); await notes.fill('Nota de prueba Playwright');
    await mdWrap.locator('.ixf-md-bar button').first().click();
    const notesVal = await notes.inputValue();
    const counterTxt = await mdWrap.locator('xpath=following-sibling::*[contains(@class,"ixf-counter")][1]').textContent().catch(() => '');
    await mdWrap.locator('.ixf-md-tabs [role=tab]').nth(1).click();
    await page.waitForFunction(() => { const p = document.querySelector('#ihpix-field-additional-notes').closest('.ixf-md').querySelector('.ixf-md-preview'); return p && !p.hidden && p.innerHTML.includes('<strong>'); }, null, { timeout: 15000 }).catch(() => {});
    const previewHtml = await mdWrap.locator('.ixf-md-preview').innerHTML();
    step('report: editor Markdown (negrita + preview servidor)', /\*\*/.test(notesVal) && previewHtml.includes('<strong>'), { notesVal, counter: (counterTxt || '').trim(), preview: previewHtml.slice(0, 80) });
    await mdWrap.locator('.ixf-md-tabs [role=tab]').nth(0).click();

    // Sección VII: buscar curso y adjuntar
    await page.selectOption('#ihpix-lw-type', 'course');
    const courseBoxVisible = await page.locator('#ihpix-lw-course').isVisible();
    await page.fill('#ihpix-lw-search', 'flood');
    await page.waitForSelector('#ihpix-lw-results button.ihpix-lw-result', { timeout: 20000 });
    await page.locator('#ihpix-lw-results button.ihpix-lw-result').first().click();
    let items = await page.locator('#ihpix-lw-list .ihpix-lw-item').count();
    const courseItem = await page.locator('#ihpix-lw-list .ihpix-lw-item.is-course a').first().getAttribute('href');
    step('report: Sección VII adjunta un curso del catálogo', items === 1 && courseBoxVisible && /\/learning\//.test(courseItem || ''), { items, courseItem });

    // Modal "Upload a publication": subir un PDF y ver el adjunto
    await page.locator('#ihpix-links-widget [data-ihpix-publication-open]').first().scrollIntoViewIfNeeded();
    await page.locator('#ihpix-links-widget [data-ihpix-publication-open]').first().click();
    await page.waitForSelector('#ihpix-publication-modal:not([hidden])', { timeout: 10000 });
    const modalState = await page.evaluate(() => ({
      org: document.querySelector('#ihpix-pub-field-org') && document.querySelector('#ihpix-pub-field-org').value,
      orgText: document.querySelector('#ihpix-pub-field-org option:checked') && document.querySelector('#ihpix-pub-field-org option:checked').textContent,
      email: document.querySelector('#ihpix-pub-field-contact-email').value,
      focused: document.activeElement && document.activeElement.id,
    }));
    await page.fill('#ihpix-pub-field-title', 'IHP-IX Playwright smoke publication (delete me)');
    await page.selectOption('#ihpix-pub-field-type', 'educational_material');
    await page.fill('#ihpix-pub-field-year', '2026');
    if (!modalState.email) await page.fill('#ihpix-pub-field-contact-email', 'ihp-wins-smoke@dev-wins.com');
    await page.setInputFiles('#ihpix-pub-field-file', { name: 'ihpix-playwright.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4\n% Playwright IHP-IX smoke\n') });
    const uploadChip = await page.locator('#ihpix-publication-modal .ixf-upload-name').textContent().catch(() => '');
    await page.click('#ihpix-pub-submit');
    await page.waitForSelector('#ihpix-pub-success:not([hidden])', { timeout: 90000 });
    const successText = await page.locator('#ihpix-pub-success').textContent();
    const docHref = await page.locator('#ihpix-pub-success a').first().getAttribute('href').catch(() => '');
    out.created.publication_href = docHref;
    await page.waitForSelector('#ihpix-publication-modal[hidden]', { timeout: 10000 }).catch(() => {});
    items = await page.locator('#ihpix-lw-list .ihpix-lw-item').count();
    const pubBadge = await page.locator('#ihpix-lw-list .ihpix-lw-item.is-publication .ihpix-lw-badge').first().textContent().catch(() => '');
    step('report: modal crea la publicación y la adjunta', items === 2 && /documents\//.test(docHref || ''), { modalState, uploadChip: (uploadChip || '').trim(), successText: (successText || '').trim().slice(0, 100), docHref, pubBadge });

    // Autosave por usuario: recargar y comprobar que título y adjuntos persisten
    await page.fill('#ihpix-field-title', 'Playwright IHP-IX draft (delete me)');
    await page.waitForTimeout(2500);
    const saveKey = await page.evaluate(() => Object.keys(localStorage).filter(k => k.startsWith('ihpix-report-draft-v1')));
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForSelector('#ihpix-report-form');
    await page.waitForTimeout(1500);
    const restored = await page.evaluate(() => ({ title: document.getElementById('ihpix-field-title').value, links: JSON.parse(document.getElementById('ihpix-links-json').value || '[]').length, country: document.getElementById('ihpix-field-country').value, ms: document.querySelectorAll('#ihpix-ms-picker input:checked').length, chips: document.querySelectorAll('#ihpix-ms-picker .ixf-chip').length }));
    step('report: autosave por usuario restaura tras recargar', restored.title.startsWith('Playwright') && restored.links === 2 && restored.country === 'chile' && restored.ms === 1 && restored.chips === 1, { saveKey, restored });

    // Validación en vivo: fechas invertidas
    await page.fill('#ihpix-field-start-date', '2026-06-01'); await page.fill('#ihpix-field-end-date', '2026-01-01');
    await page.locator('#ihpix-field-end-date').dispatchEvent('change'); await page.locator('#ihpix-field-end-date').blur();
    const dateErr = await page.locator('#ihpix-error-end-date').isVisible();
    await page.fill('#ihpix-field-end-date', '2026-07-01'); await page.locator('#ihpix-field-end-date').dispatchEvent('change');
    step('report: error inline fin < inicio', dateErr);

    // Guardar borrador (POST real) → el reporte queda en BD con los 2 adjuntos
    await page.fill('#ihpix-field-institution', 'Playwright Institute');
    const [resp] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/ihpix/report') && r.request().method() === 'POST', { timeout: 60000 }),
      page.click('#ihpix-report-draft-btn'),
    ]);
    const postStatus = resp.status();
    await page.waitForURL(/\/ihpix\/report\/[^/]+\/edit|\/ihpix\/my-reports|\/user\//, { timeout: 30000 }).catch(() => {});
    const finalUrl = page.url();
    const m = finalUrl.match(/\/ihpix\/report\/([^/]+)\/edit/);
    out.created.report_id = m ? m[1] : '';
    await page.waitForLoadState('networkidle').catch(() => {});
    const editState = m ? await page.evaluate(() => ({ title: (document.getElementById('ihpix-field-title') || {}).value, links: JSON.parse((document.getElementById('ihpix-links-json') || { value: '[]' }).value || '[]').length, editMode: !!document.querySelector('#ihpix-report-form') })) : {};
    step('report: guardar borrador (POST) → página de edición con los 2 adjuntos', postStatus === 200 && !!m && editState.links === 2, { postStatus, finalUrl: finalUrl.replace(BASE, ''), editState });
    await page.screenshot({ path: OUT + '/report-desktop.png', fullPage: false });
    await ctx.close();

    // ───────────── 2. Móvil y RTL ─────────────
    try {
    ({ ctx, page } = await newPage(browser, tokens.editor, { key: 'mobile', viewport: { width: 390, height: 844 } }));
    await page.goto(BASE + '/ihpix/report?output=1.3', { waitUntil: 'networkidle', timeout: 90000 });
    await page.waitForSelector('#ihpix-report-form');
    const overflow = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth, navScroll: (() => { const n = document.querySelector('.ihpix-section-nav-inner'); return n ? getComputedStyle(n).overflowX : null; })() }));
    step('móvil 390px: sin desbordamiento horizontal + nav horizontal', overflow.scrollWidth <= overflow.innerWidth + 1 && overflow.navScroll === 'auto', overflow);
    await page.screenshot({ path: OUT + '/report-mobile.png', fullPage: false });
    await ctx.close();

    ({ ctx, page } = await newPage(browser, tokens.editor, { key: 'rtl', locale: 'ar' }));
    await page.goto(BASE + '/ar/ihpix/report?output=1.3', { waitUntil: 'networkidle', timeout: 90000 });
    await page.waitForSelector('#ihpix-report-form');
    const rtl = await page.evaluate(() => ({ dir: document.documentElement.getAttribute('dir'), combobox: document.querySelectorAll('.ixf-combobox').length, chipsDir: getComputedStyle(document.querySelector('#ihpix-ms-picker')).direction, uploadBtn: (document.querySelector('[data-ihpix-publication-open]') || {}).textContent }));
    step('árabe: dir=rtl y kit inicializado', rtl.dir === 'rtl' && rtl.combobox >= 2 && rtl.chipsDir === 'rtl', { dir: rtl.dir, combobox: rtl.combobox, chipsDir: rtl.chipsDir, uploadBtn: (rtl.uploadBtn || '').trim() });
    await page.screenshot({ path: OUT + '/report-ar.png', fullPage: false });
    await ctx.close();
    } catch (e) { step('móvil/RTL: EXCEPCIÓN', false, String(e).slice(0, 300)); }

    // ───────────── 3. Workspace (editor) ─────────────
    try {
    ({ ctx, page } = await newPage(browser, tokens.editor, { key: 'workspace' }));
    await page.goto(BASE + '/ihpix/workspaces/1.3', { waitUntil: 'networkidle', timeout: 90000 });
    await page.locator('[data-ihpix-publication-open]').first().click();
    await page.waitForSelector('#ihpix-publication-modal:not([hidden])', { timeout: 10000 });
    const wsModal = await page.evaluate(() => ({ attach: !!document.getElementById('ihpix-pub-field-attach'), attachOptions: document.getElementById('ihpix-pub-field-attach') ? document.getElementById('ihpix-pub-field-attach').options.length : 0, note: !!document.querySelector('#ihpix-pub-attach-field .ihpix-report-help') }));
    await page.keyboard.press('Escape');
    const closed = await page.locator('#ihpix-publication-modal').isHidden();
    step('workspace 1.3: modal con "Attach to my report" y cierra con Esc', closed && (wsModal.attach || wsModal.note), wsModal);
    await ctx.close();
    } catch (e) { step('workspace: EXCEPCIÓN', false, String(e).slice(0, 300)); }

    // ───────────── 4. Admin (sysadmin) ─────────────
    try {
    ({ ctx, page } = await newPage(browser, tokens.sysadmin, { key: 'admin' }));
    await page.goto(BASE + '/ckan-admin/ihpix/activities', { waitUntil: 'networkidle', timeout: 90000 });
    const acc = page.locator('#ihpact-accordion [data-ihpact-accordion]').nth(1);
    const before = await acc.getAttribute('aria-expanded');
    await acc.click();
    const after = await acc.getAttribute('aria-expanded');
    const bodyVisible = await page.locator('#ihpact-section-org').isVisible();
    const adminKit = await page.evaluate(() => ({ mp: document.querySelectorAll('#ihpact-ms-widget.ixf-mp').length, grids: document.querySelectorAll('#ihpact-knowledge-product-type-group input[type=checkbox]').length }));
    step('admin actividades: acordeón accesible + MultiPicker + grids JSON', before === 'false' && after === 'true' && bodyVisible && adminKit.mp === 1 && adminKit.grids > 0, { before, after, bodyVisible, adminKit });
    await page.goto(BASE + '/ckan-admin/ihpix/workspaces', { waitUntil: 'networkidle', timeout: 90000 });
    await page.locator('.ihpwg-desc-btn').first().click();
    const descModal = await page.locator('.ixf-modal:not([hidden]) textarea[name=description]').count();
    const descMd = await page.locator('.ixf-modal:not([hidden]) .ixf-md-bar').count();
    await page.keyboard.press('Escape');
    const leadInput = page.locator('.ihpwg-lead-wrap .ixf-combobox-input').first();
    await leadInput.click(); await leadInput.fill('ihp');
    const remoteOk = await page.waitForSelector('.ixf-listbox:not([hidden]) .ixf-option[role=option]', { timeout: 15000 }).then(() => true).catch(() => false);
    const leadOpts = remoteOk ? await page.locator('.ixf-listbox:not([hidden]) .ixf-option[role=option]').count() : 0;
    await page.keyboard.press('Escape');
    step('admin workspaces: modal Markdown de descripción + autocompletado de lead', descModal === 1 && descMd === 1 && remoteOk, { descModal, descMd, leadOpts });
    await page.screenshot({ path: OUT + '/admin-workspaces.png', fullPage: false });
    await ctx.close();
    } catch (e) { step('admin: EXCEPCIÓN', false, String(e).slice(0, 300)); }
  } catch (e) {
    step('EXCEPCIÓN', false, String(e).slice(0, 400));
  } finally {
    await browser.close();
    fs.writeFileSync(OUT + '/results.json', JSON.stringify(out, null, 1));
    console.log('@@DONE ' + JSON.stringify({ created: out.created, console_errors: out.console_errors, http_errors: out.http_errors }).slice(0, 1500));
  }
})();
