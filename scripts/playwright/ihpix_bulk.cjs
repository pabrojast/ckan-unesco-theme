// Prueba destructiva solo sobre el CKAN local aislado indicado por IHPIX_QA_BASE.
const {chromium}=require('playwright');
const fs=require('fs'),assert=require('assert/strict'),path=require('path');
const base=process.env.IHPIX_QA_BASE||'http://127.0.0.1:5013';
assert(['localhost','127.0.0.1'].includes(new URL(base).hostname));
const root=process.env.IHPIX_QA_FILES,out=process.env.IHPIX_QA_OUTPUT;
assert(root&&out&&process.env.IHPIX_QA_TOKENS);
const tokens=JSON.parse(fs.readFileSync(process.env.IHPIX_QA_TOKENS));
fs.mkdirSync(out,{recursive:true});let checks=[],errors=[];
function ok(name,value=true){assert(value,name);checks.push(name);console.log('PASS',checks.length,name);}
(async()=>{
 const browser=await chromium.launch();
 const context=await browser.newContext({viewport:{width:1440,height:1000}});
 await context.route(base+'/**',r=>r.continue({headers:{...r.request().headers(),Authorization:tokens.author}}));
 const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 async function api(name,data={},token=tokens.author){const r=await context.request.post(base+'/api/3/action/'+name,{headers:{Authorization:token},data});return r.json();}
 async function upload(file){await page.locator('#workbook').setInputFiles(path.join(root,file));await page.locator('#ix-import-upload button').click();await page.waitForURL(/\/ihpix\/import\?id=/);return new URL(page.url()).searchParams.get('id');}
 try{
  await page.goto(base+'/ihpix/import');
  ok('Two distinct workbook downloads',await page.locator('a[href$="template.xlsx"]').count()===1&&await page.locator('a[href$="example.xlsx"]').count()===1);
  ok('Draft navigation uses the profile draft filter',(await page.locator('.ix-import-header a').getAttribute('href')).includes('status=draft'));
  const downloadPromise=page.waitForEvent('download');await page.locator('a[href$="template.xlsx"]').click();const download=await downloadPromise;
  await download.saveAs(path.join(out,'downloaded-template.xlsx'));ok('Template downloads as flat v3 XLSX',download.suggestedFilename()==='ihpix-import-v3.xlsx');
  await page.screenshot({path:path.join(out,'prepare-desktop.png'),fullPage:true});
  const invalid=await upload('invalid.xlsx');
  ok('Invalid number points to actual flat cell',(await page.locator('.ix-import-review').innerText()).includes(fs.readFileSync(path.join(root,'invalid-cell.txt'),'utf8')));
  ok('Technical field names are absent',!(await page.locator('.ix-import-review').innerText()).includes('num_knowledge_products'));
  ok('Invalid file cannot be confirmed',await page.locator('[name=confirm]').count()===0);
  ok('API also rejects invalid import',!(await api('ihpix_import_create',{id:invalid,confirm:true})).success);
  await page.screenshot({path:path.join(out,'errors-desktop.png'),fullPage:true});
  const id=await upload('en-example.xlsx');
  ok('Example previews three activities',await page.locator('.ix-import-activity').count()===3);
  ok('Example is explicitly identified',(await page.locator('.ix-import-review').innerText()).includes('fictional examples'));
  ok('Another user cannot inspect this preview',!(await api('ihpix_import_show',{id},tokens.other)).success);
  ok('Another user cannot create its drafts',!(await api('ihpix_import_create',{id,confirm:true},tokens.other)).success);
  const otherResponse=await context.request.post(base+'/ihpix/import',{headers:{Authorization:tokens.other},form:{id,confirm:'1'}});ok('Failed confirmation never exposes another owner preview',[403,404].includes(otherResponse.status())&&!(await otherResponse.text()).includes('[EXAMPLE] River monitoring study'));

  await page.locator('[name=confirm]').click();await page.waitForSelector('.ix-import-created');
  const created=(await api('ihpix_import_show',{id})).result.created;
  ok('Confirmation creates exactly three drafts',created.length===3);
  const expected=JSON.parse(fs.readFileSync(path.join(root,'expected.json')));
  for(let i=0;i<created.length;i++){
   const report=(await api('ihpix_report_show',{id:created[i].id})).result;
   ok('Imported activity '+(i+1)+' remains a draft',report.status==='draft');
   const arrays=new Set(['flagships','cross_cutting_wg','regions','member_states','knowledge_product_type','scientific_product_type','knowledge_activity_type','training_type','stakeholder_group_type','contributions_json','synergies_json','supporters_json','partner_org_ids']);
   for(const [field,value] of Object.entries(expected[i])){
    let actual=report[field];
    if(arrays.has(field)&&typeof actual!=='string')actual=JSON.stringify(actual);
    if(arrays.has(field)){const decode=v=>typeof v==='string'?(v?JSON.parse(v):[]):v||[];assert.deepEqual(decode(actual),decode(value),field);}
    else assert.deepEqual(actual,value,field);
   }
   ok('All fields of activity '+(i+1)+' survive save');
   if(i===2)ok('Both external resources are saved',report.links.length===2);
  }
  const repeated=await api('ihpix_import_create',{id,confirm:true});
  ok('Repeated confirmation returns the same drafts',repeated.result.repeated&&JSON.stringify(repeated.result.created)===JSON.stringify(created));
  await page.locator('.ix-import-created a').first().click();await page.waitForURL('**/ihpix/report/'+created[0].id+'/edit');await page.waitForFunction(title=>document.querySelector('[name=title]')?.value===title,created[0].title);ok('Created draft opens in the editor',await page.locator('[name=title]').inputValue()===created[0].title);
  await page.goto(base+'/ihpix/import');const minimal=await upload('minimal.xlsx');
  ok('Missing answers allow creation of a draft',await page.locator('[name=confirm]').count()===1&&await page.locator('.ix-import-pending').count()===1);
  ok('Pending answers are collapsed initially',await page.locator('.ix-import-pending').getAttribute('open')===null);
  await page.locator('[name=confirm]').click();await page.waitForSelector('.ix-import-created');ok('Minimal draft is created',await page.locator('.ix-import-created a').count()===1);
  await page.goto(base+'/ihpix/import');await upload('legacy.xlsx');await page.locator('[name=confirm]').click();await page.waitForSelector('.ix-import-created');ok('Legacy v1 workbook still imports');
  await page.goto(base+'/ihpix/import');await upload('legacy-v2.xlsx');await page.locator('[name=confirm]').click();await page.waitForSelector('.ix-import-created');ok('Previous guided v2 workbook still imports');
  await page.goto(base+'/ihpix/import');await page.locator('#workbook').setInputFiles({name:'broken.xlsx',mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer:Buffer.from('not a workbook')});await page.locator('#ix-import-upload button').click();await page.waitForSelector('[role=alert]');ok('Broken file has an inline error and retry form',await page.locator('#ix-import-upload').count()===1);
  await page.goto(base+'/ihpix/import');const rollback=await upload('rollback.xlsx');
  try{
   const archive=await api('ihpix_working_group_update',{id:'1.10',status:'archived'},tokens.admin);assert(archive.success);
   await page.locator('[name=confirm]').click();await page.waitForSelector('[role=alert]');
   ok('Failed confirmation retains the reviewed activities',await page.locator('.ix-import-activity').count()===2&&(await page.locator('[role=alert]').first().innerText()).includes('Drafts could not be created'));
   ok('Failed confirmation remains a preview',(await api('ihpix_import_show',{id:rollback})).result.status==='preview');
   const reports=(await api('ihpix_my_reports_list',{limit:100})).result.results;
   ok('Failure on second row leaves no partial drafts',!reports.some(r=>r.title.startsWith('Rollback activity')));
  }finally{const restored=await api('ihpix_working_group_update',{id:'1.10',status:'active'},tokens.admin);assert(restored.success);}
  await page.locator('[name=confirm]').click();await page.waitForSelector('.ix-import-created');ok('Same preview can be retried after failure',await page.locator('.ix-import-created a').count()===2);
  const labels=JSON.parse(fs.readFileSync(path.join(root,'ui-labels.json')));
  for(const locale of ['en','es','fr','ar']){
   const prefix=locale==='en'?'':'/'+locale;
   await page.goto(base+prefix+'/ihpix/import');const localized=await upload(locale+'-review.xlsx');
   ok(locale+' actual heading is translated',await page.locator('.ix-import h1').innerText()===labels[locale]);
   ok(locale+' example has no blocking errors',await page.locator('[name=confirm]').count()===1);
   for(const width of [1440,768,390,320]){
    await page.setViewportSize({width,height:1000});
    await page.goto(base+prefix+'/ihpix/import');
    ok(locale+' prepare '+width+' fits screen',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    const color=await page.locator('.ix-import .btn-primary').first().evaluate(e=>getComputedStyle(e).color);ok(locale+' button text visible '+width,color==='rgb(255, 255, 255)');
    await page.goto(base+prefix+'/ihpix/import?id='+localized);
    ok(locale+' preview '+width+' fits screen',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    if(width===390||width===1440)await page.screenshot({path:path.join(out,locale+'-preview-'+width+'.png'),fullPage:true});
   }
  }
  const admin=await browser.newContext();
  await admin.route(base+'/**',r=>r.continue({headers:{...r.request().headers(),Authorization:tokens.admin}}));
  const adminPage=await admin.newPage();
  for(const width of [1440,768,390,320]){
   await adminPage.setViewportSize({width,height:1000});await adminPage.goto(base+'/ar/ihpix/import');
   ok('Arabic admin toolbar '+width+' fits screen',await adminPage.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  }
  await admin.close();
  ok('No browser JavaScript exceptions' ,errors.length===0);
  fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({checks,errors},null,2));
 }catch(e){await page.screenshot({path:path.join(out,'failure.png'),fullPage:true});throw e;}finally{fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({checks,errors},null,2));await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
