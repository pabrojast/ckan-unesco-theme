// Pruebas de filtros y navegación contra una base CKAN aislada con fixtures QA.
const {chromium} = require('playwright');
const fs = require('fs');
const assert = require('assert/strict');
const base = process.env.IHPIX_QA_BASE || 'http://127.0.0.1:5011';
assert(['localhost', '127.0.0.1'].includes(new URL(base).hostname));
const tokens = JSON.parse(fs.readFileSync(process.env.IHPIX_QA_TOKENS));
const fixture = JSON.parse(fs.readFileSync(process.env.IHPIX_QA_FIXTURE));
const out = process.env.IHPIX_QA_OUTPUT;
assert(out);fs.mkdirSync(out,{recursive:true});
let checks = 0;
function ok(name, value=true) {assert(value,name);console.log('PASS',++checks,name);}
(async()=>{
 const browser=await chromium.launch({args:['--disable-quic']});
 const ctx=await browser.newContext({viewport:{width:1440,height:1000}});
 await ctx.route(base+'/**',r=>r.continue({headers:{...r.request().headers(),Authorization:tokens.admin}}));
 const page=await ctx.newPage();page.setDefaultTimeout(15000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 async function go(path){const r=await page.goto(base+path);assert.equal(r.status(),200,path);}
 async function country(value){await page.selectOption('#ixg-filter-country',value);await page.waitForFunction(v=>new URL(location.href).searchParams.get('country')===v,value);await page.locator('.ixg-loading').waitFor({state:'hidden'});}
 async function count(n){await page.waitForFunction(n=>window.IhpixProgress && document.querySelector('#ixg-tile-activities')?.textContent===String(n),n);}
 try {
  await go('/ihpix/progress?country=CL');await count(2);
  ok('ISO country bookmarks use the canonical selection',await page.locator('#ixg-filter-country').inputValue()==='Chile');
  await go('/ihpix/progress');await count(3);
  ok('Unique total ignores repeated outputs', (await page.locator('#ixg-strip h2').innerText()).startsWith('3 '));
  ok('PA1 counts each activity once', (await page.locator('.ixg-strip-legend a').first().innerText()).endsWith('3'));
  const input=page.locator('.ixg-filter--country .ixf-combobox-input');
  await input.fill('chi');await page.locator('.ixf-option[role=option]').first().waitFor();
  ok('Country autocomplete shows names only',await page.locator('.ixf-option small').count()===0);
  await input.press('ArrowDown');await input.press('Enter');await count(2);
  ok('Keyboard selection updates the dashboard',new URL(page.url()).searchParams.get('country')==='Chile');
  for(const id of ['#ixg-download','#ixg-presentation','#ixg-narrative'])ok(id+' keeps country',new URL(await page.locator(id).getAttribute('href'),base).searchParams.get('country')==='Chile');
  ok('Country selection explains international totals',await page.locator('#ixg-selection').isVisible());
  await page.locator('#ixg-clear-country').click();await count(3);
  await page.locator('#ixg-fig-map').scrollIntoViewIfNeeded();
  await page.locator('#ixg-fig-map path[data-country=Egypt]').click();await count(1);
  ok('Map selects activities where the country supports',new URL(page.url()).searchParams.get('country')==='Egypt');
  await page.locator('#ixg-fig-map [data-ixg-toggle-table]').click();
  await page.locator('#ixg-fig-map [data-ixg-country=Kenya]').click();await count(2);
  ok('Accessible map table filters the dashboard',new URL(page.url()).searchParams.get('country')==='Kenya');
  await page.goBack();await count(1);ok('Back restores the country filter',await page.locator('#ixg-filter-country').inputValue()==='Egypt');
  await page.goForward();await count(2);ok('Forward restores the country filter',await page.locator('#ixg-filter-country').inputValue()==='Kenya');
  await page.reload();await count(2);ok('Reload preserves country');
  await page.locator('.ixg-scope-tabs a').filter({hasText:'Output',exact:true}).click();await count(2);
  ok('Switching scope keeps country',new URL(page.url()).searchParams.get('country')==='Kenya');
  const button=page.locator('.ixg-btn--primary');ok('Primary action has visible white text',await button.evaluate(e=>getComputedStyle(e).color==='rgb(255, 255, 255)'));
  await page.selectOption('#ixg-filter-biennium','2022-2023');await count(0);
  ok('Empty filters keep selection and controls',await page.locator('#ixg-filter-country').inputValue()==='Kenya' && await page.locator('#ixg-selection').isVisible());
  await page.selectOption('#ixg-filter-biennium','');await count(2);
  // La petición más antigua responde después de la última selección.
  await page.route('**/api/3/action/ihpix_progress_stats*',async r=>{
   if(new URL(r.request().url()).searchParams.get('country')==='Chile')await new Promise(resolve=>setTimeout(resolve,600));
   await r.continue();
  });
  await page.selectOption('#ixg-filter-country','Chile');await page.selectOption('#ixg-filter-country','France');await count(1);await page.waitForTimeout(900);
  ok('Rapid selections cannot overwrite the latest result',await page.locator('#ixg-filter-country').inputValue()==='France' && new URL(page.url()).searchParams.get('country')==='France');
  await page.unroute('**/api/3/action/ihpix_progress_stats*');
  await page.route('**/api/3/action/ihpix_progress_stats*',r=>r.fulfill({status:503,body:'unavailable'}));
  await page.selectOption('#ixg-filter-country','Chile');await page.locator('#ixg-load-error').waitFor({state:'visible'});
  ok('Failed update keeps the previous result and filters',await page.locator('#ixg-filter-country').inputValue()==='France' && await page.locator('#ixg-tile-activities').innerText()==='1');
  await page.unroute('**/api/3/action/ihpix_progress_stats*');await page.locator('#ixg-retry').click();await count(2);
  ok('Retry applies the requested filter',await page.locator('#ixg-filter-country').inputValue()==='Chile');
  await country('Afghanistan');await count(0);ok('Country without coordinates can still be selected');
  await country('Chile');
  const api=await ctx.request.get(base+await page.locator('#ixg-download').getAttribute('href'),{headers:{Authorization:tokens.admin}});
  const stats=(await api.json()).result;ok('Download matches the dashboard',stats.overview.activities===2 && stats.kpi_2.individuals===300);
  await page.locator('#ixg-presentation').click();ok('Presentation includes current country', (await page.locator('.filters').first().innerText()).includes('Chile'));
  await page.locator('.ix-slide-controls a').click();await count(2);ok('Presentation return preserves scope and filters',page.url().includes('/output/1.1') && page.url().includes('country=Chile'));
  for(const [scope,value] of [['overall',''],['pa','PA1'],['output','1.1'],['flagship','FRIEND'],['ctwg','Ecohydrology and Water Quality'],['organization',fixture.organization]]){
   await go('/ihpix/reports/generate?'+new URLSearchParams({scope,value,country:'Chile'}));
   ok('Narrative '+scope+' has the same two sources',await page.locator('.ix-narrative-source').count()===2);
   ok('Narrative '+scope+' restores selectors',await page.locator('#report-scope').inputValue()===scope && await page.locator('#report-country').inputValue()==='Chile');
  }
  await go('/ihpix/reports/generate?scope=overall&country=Kenya&biennium=2022-2023');ok('Empty narrative has no inferred sources',await page.locator('.ix-narrative-source').count()===0);
  // Gráficos SVG en servidor y secciones seleccionables (ihpix_report_sections)
  await go('/ihpix/reports/generate?scope=overall&country=Chile');
  ok('Narrative renders server-side SVG charts',await page.locator('.ix-doc svg[role=img]').count()>0 && await page.locator('.ix-doc-section:not(.ix-doc-appendix)').count()===12);
  await go('/ihpix/reports/generate?'+new URLSearchParams({scope:'pa',value:'PA1',country:'Chile',sections_given:'1',sections:'kpi_1'}));
  ok('Narrative honours the section selection without the appendix',await page.locator('.ix-doc-section:not(.ix-doc-appendix)').count()===1 && await page.locator('.ix-narrative-source').count()===0 && await page.locator('#section-kpi_1 svg[role=img]').count()>0);
  ok('Section checkboxes reflect the selection',await page.locator('.ix-sections-grid input:checked').count()===1 && !(await page.locator('input[name=sources]').isChecked()));
  await go('/ihpix/presentation?scope=pa&value=PA1&country=Chile&sections=overview&sections=kpi_1');
  ok('Presentation slides carry SVG charts and the section filter',await page.locator('.ix-slide svg[role=img]').count()>0 && (await page.locator('#page-count').innerText()).trim().endsWith('/ 2'));
  await go('/ihpix/outputs?pa=PA1&region=Latin+America+and+the+Caribbean');
  const explorer=page.locator('#ihpix-out-country').locator('..').locator('.ixf-combobox-input');await explorer.fill('Chil');await page.locator('.ixf-option').first().click();await page.locator('.ox-filter-actions button[type=submit]').click();
  ok('Explorer applies autocomplete while preserving filters',new URL(page.url()).searchParams.get('country')==='Chile' && new URL(page.url()).searchParams.get('pa')==='PA1');
  // Un clic antes de los 900 ms debe guardar también la última respuesta.
  await go('/ihpix/report');await page.locator('#ihpix-field-title').fill('QA unsaved navigation');await page.locator('#ihpix-my-drafts').click();
  ok('My drafts opens the filtered user tab',new URL(page.url()).searchParams.get('status')==='draft');
  await go('/ihpix/report');ok('Latest answer survives immediate navigation',await page.locator('#ihpix-field-title').inputValue()==='QA unsaved navigation');
  await page.evaluate(()=>{Storage.prototype.setItem=function(){throw new Error('quota');};});
  await page.locator('#ihpix-field-title').fill('QA changed with unavailable storage');
  let message='';page.once('dialog',async d=>{message=d.message();await d.accept();});await page.locator('#ihpix-my-drafts').click();
  ok('Storage failure prevents accidental navigation',page.url().endsWith('/ihpix/report') && message.includes('Save as draft'));
  // Cobertura visual: contenido largo, RTL administrador y pantallas estrechas.
  for(const locale of ['en','es','fr','ar'])for(const width of [1440,768,390,320]){
   await page.setViewportSize({width,height:1000});
   for(const route of ['/ihpix/progress','/ihpix/progress/output/1.1','/ihpix/priority-area/PA1','/ihpix/outputs','/ihpix/report']){
    await go((locale==='en'?'':'/'+locale)+route);await page.waitForTimeout(120);
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
    ok(locale+' '+width+' '+route+' has no horizontal overflow',overflow<=1);
    if(width===1440&&locale==='en'||width===390&&locale==='ar')await page.screenshot({path:out+'/'+locale+'-'+width+'-'+route.replaceAll('/','-')+'.png',fullPage:true});
    if(route.includes('priority-area'))ok(locale+' '+width+' banner text is white',await page.locator('.ixp-header p').evaluate(e=>getComputedStyle(e).color==='rgb(255, 255, 255)'));
   }
  }
  ok('No JavaScript exceptions',errors.length===0);fs.writeFileSync(out+'/results.json',JSON.stringify({checks,errors},null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
