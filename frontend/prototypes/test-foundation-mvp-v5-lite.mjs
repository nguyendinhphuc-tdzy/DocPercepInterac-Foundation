import { createHash } from 'node:crypto';
import { spawn, spawnSync } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here=dirname(fileURLToPath(import.meta.url));
const htmlPath=join(here,'foundation-document-processing-mvp-v5-lite.html');
const html=readFileSync(htmlPath,'utf8');
const sourcePath=process.env.FOUNDATION_V4_SOURCE;
const results=[];
const check=(name,pass,detail='')=>{results.push({name,result:pass?'PASS':'FAIL',detail});if(!pass)process.exitCode=1};

const dataMatch=html.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/);
let data;
try{data=JSON.parse(dataMatch?.[1]||'');check('embedded JSON parses',true)}catch(error){check('embedded JSON parses',false,error.message)}
const scripts=[...html.matchAll(/<script(?:\s+[^>]*)?>([\s\S]*?)<\/script>/g)],appJs=scripts.at(-1)?.[1]||'';
const jsPath=join(tmpdir(),`foundation-lite-${process.pid}.js`);writeFileSync(jsPath,appJs,'utf8');
const syntax=spawnSync(process.execPath,['--check',jsPath],{encoding:'utf8'});rmSync(jsPath,{force:true});
check('application JavaScript parses',syntax.status===0,syntax.stderr.trim());
check('source v4 remains byte-identical',!sourcePath||(existsSync(sourcePath)&&createHash('sha256').update(readFileSync(sourcePath)).digest('hex')==='aa83c3790686f0f96ca7b3d9b10ee113d1e665f48e5f1aee5bd8da08e457b35a'),sourcePath?'verified from FOUNDATION_V4_SOURCE':'optional source check skipped');
check('MVP visual shell remains',html.includes('class="top"')&&html.includes('class="global"')&&html.includes('class="rail"')&&html.includes('class="main"')&&html.includes('class="viewer"'));
check('Local File is the Workflow Profile',appJs.includes('Local File Roll-Forward')&&appJs.includes("screen:'home'")&&appJs.includes("screen:'workflow'"));
check('extraction and generation are not competing task choices',!appJs.includes('choose-task')&&!appJs.includes("taskType:'extraction'")&&!appJs.includes("taskType:'generation'"));
check('blank workspace has three generic inputs',['Document inputs','Output template','Processing request'].every(x=>appJs.includes(x)));
check('all GTPS Local File cases remain',data?.fixture?.changes?.length===21&&['ncp','processing','benchmark','on-behalf','protected'].every(id=>data.fixture.changes.some(x=>x.id===id)));
check('offline CSP remains strict',html.includes("default-src 'none'")&&html.includes("connect-src 'none'"));
check('no external resources are declared',!/<(?:script|iframe)[^>]+src=["']https?:|<link[^>]+href=["']https?:|<img[^>]+src=["']https?:/i.test(html));
check('final DOCX remains disabled',appJs.includes("'download-docx'")&&appJs.includes('disabled title='));
check('embedded source reader remains',Boolean(data?.sourceData?.documents&&data?.sourceData?.workbook));

const chrome=['C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe','C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'].find(existsSync);
check('browser runtime available',Boolean(chrome),chrome||'Chrome/Edge not found');
if(chrome){
 const profile=mkdtempSync(join(tmpdir(),'foundation-lite-cdp-')),port=9700+(process.pid%200),url=pathToFileURL(resolve(htmlPath)).href;
 const browser=spawn(chrome,['--headless=new','--disable-gpu','--no-first-run','--disable-default-apps',`--remote-debugging-port=${port}`,`--user-data-dir=${profile}`,'--window-size=1366,768',url],{stdio:'ignore'});
 const sleep=ms=>new Promise(r=>setTimeout(r,ms));let ws;
 try{
  let page;for(let i=0;i<80;i++){try{const pages=await fetch(`http://127.0.0.1:${port}/json/list`).then(r=>r.json());page=pages.find(x=>x.type==='page');if(page)break}catch{}await sleep(100)}if(!page)throw new Error('Browser page unavailable');
  ws=new WebSocket(page.webSocketDebuggerUrl);await new Promise((ok,bad)=>{ws.addEventListener('open',ok,{once:true});ws.addEventListener('error',bad,{once:true})});
  let seq=0;const pending=new Map(),runtimeErrors=[];
  ws.addEventListener('message',event=>{const m=JSON.parse(event.data);if(m.method==='Runtime.exceptionThrown')runtimeErrors.push(m.params.exceptionDetails?.exception?.description||m.params.exceptionDetails?.text||'runtime exception');if(m.method==='Log.entryAdded'&&m.params.entry.level==='error')runtimeErrors.push(m.params.entry.text);if(!m.id||!pending.has(m.id))return;const p=pending.get(m.id);pending.delete(m.id);m.error?p.bad(new Error(m.error.message)):p.ok(m.result)});
  const send=(method,params={})=>new Promise((ok,bad)=>{const id=++seq;pending.set(id,{ok,bad});ws.send(JSON.stringify({id,method,params}))});
  const evaluate=async expression=>{const a=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(a.exceptionDetails)throw new Error(a.exceptionDetails.exception?.description||a.exceptionDetails.text||'Uncaught');return a.result.value};
  await send('Runtime.enable');await send('Log.enable');for(let i=0;i<50;i++){if(await evaluate("document.readyState==='complete'&&Boolean(window.__foundationLite)"))break;await sleep(100)}
  check('page loads without console errors',runtimeErrors.length===0,runtimeErrors.join('; '));
  check('Home is the initial screen',await evaluate("window.__foundationLite.getState().screen==='home'&&document.querySelector('#main').textContent.includes('Document Intelligence Workspace')"));
  check('Home offers one Local File workflow starter',await evaluate("document.querySelectorAll('[data-action=start-workflow]').length>=1&&document.querySelector('.workflow-start h2').textContent==='Local File Roll-Forward'"));
  check('Home offers blank workspace separately',await evaluate("Boolean(document.querySelector('[data-action=open-blank]'))"));
  check('Home does not offer Extraction and Generation as task cards',await evaluate("document.querySelectorAll('.task-choice,.choice').length===0&&!document.querySelector('#main').textContent.includes('Extract information')&&!document.querySelector('#main').textContent.includes('Generate / Update document')"));

  const homeExpanded=await evaluate("document.querySelector('.main').getBoundingClientRect().width");
  await evaluate("document.querySelector('.home-nav-toggle').click()");
  check('Home navigation sidebar collapses',await evaluate(`document.querySelector('.shell').classList.contains('left-collapsed')&&getComputedStyle(document.querySelector('.global')).display==='none'&&document.querySelector('.main').getBoundingClientRect().width>${homeExpanded}`));
  check('Home keeps a reachable expand control',await evaluate("document.querySelector('.home-nav-toggle').offsetParent!==null&&document.querySelector('.home-nav-toggle').textContent.includes('Expand')"));
  await evaluate("document.querySelector('.home-nav-toggle').click()");
  check('Home navigation sidebar expands again',await evaluate("!document.querySelector('.shell').classList.contains('left-collapsed')&&getComputedStyle(document.querySelector('.global')).display!=='none'"));

  await evaluate("document.querySelector('[data-action=open-blank]').click()");
  check('Open Workspace reaches a blank workspace',await evaluate("window.__foundationLite.getState().screen==='blank'&&document.querySelectorAll('.intake-zone').length===3"));
  check('blank workspace exposes the three intended inputs',await evaluate("['Document inputs','Output template','Processing request'].every(x=>document.querySelector('#main').textContent.includes(x))"));
  check('blank workspace does not inject GTPS business targets',await evaluate("!document.querySelector('#main').textContent.includes('Net Cost Plus')&&!document.querySelector('#main').textContent.includes('Processing services')&&!document.querySelector('#main').textContent.includes('Benchmark')"));
  check('template is optional with keyboard-accessible explanation',await evaluate("document.querySelector('.optional-mark').textContent==='Optional'&&document.querySelector('.info-tip').tabIndex===0&&document.querySelector('.tip-content').textContent.includes('flexible')"));
  check('empty intake cannot run',await evaluate("document.querySelector('[data-action=blank-run]').disabled"));
  await evaluate("document.querySelector('[data-action=blank-sample]').click();document.querySelector('[data-action=blank-region][data-id=customer]').click()");
  check('region selection sets explicit scope',await evaluate("state.blank.regions.length===1&&document.querySelectorAll('.region-card.selected').length===1"));
  await evaluate("document.querySelector('[data-action=blank-run]').click()");
  check('extraction enters review without a template',await evaluate("state.blank.stage==='review'&&state.blank.rows.length===1&&state.blank.rows[0].decision==='PENDING'"));
  await evaluate("document.querySelector('[data-action=blank-accept]').click();document.querySelector('[data-action=undo]').click()");
  check('Undo restores pending acceptance',await evaluate("state.blank.rows[0].decision==='PENDING'"));
  await evaluate("document.querySelector('[data-action=blank-skip]').click();document.dispatchEvent(new KeyboardEvent('keydown',{key:'z',ctrlKey:true,bubbles:true}))");
  check('Ctrl+Z reverses Skip',await evaluate("state.blank.rows[0].decision==='PENDING'"));
  await evaluate("document.querySelector('[data-action=blank-edit]').click();document.querySelector('#blank-edit-value').value='Reviewer draft';document.querySelector('[data-action=blank-save-edit]').click()");
  check('edited value requires acceptance and retains source',await evaluate("state.blank.rows[0].value==='Reviewer draft'&&state.blank.rows[0].decision==='PENDING'&&state.blank.rows[0].original==='Northwind Studio'"));
  await evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{key:'z',metaKey:true,bubbles:true}))");
  check('Cmd+Z reverses Edit',await evaluate("state.blank.rows[0].value==='Northwind Studio'"));
  await evaluate("document.querySelector('[data-action=blank-accept]').click();document.querySelector('[data-action=blank-output]').click()");
  check('output previews only accepted scope with no fake DOCX',await evaluate("state.blank.stage==='output'&&document.querySelectorAll('.blank-result').length===1&&document.querySelector('#main').textContent.includes('No DOCX')"));
  await evaluate("document.querySelector('[data-action=blank-input]').click();document.querySelector('[data-action=blank-region][data-id=total]').click()");
  check('scope change invalidates prior review and Undo',await evaluate("state.blank.rows.length===0&&state.blank.undo.length===0"));
  await evaluate("document.querySelector('[data-action=blank-run]').click();document.querySelector('[data-action=blank-accept]').click();document.querySelectorAll('[data-action=blank-skip]')[1].click();document.querySelector('[data-action=blank-output]').click()");
  check('skipped content is excluded from output',await evaluate("document.querySelectorAll('.blank-result').length===1&&!document.querySelector('.blank-output').textContent.includes('1,250.00')"));
  await evaluate("document.querySelector('[data-action=blank-input]').click();const dt=new DataTransfer();dt.items.add(new File(['example'],'uploaded.docx'));const input=document.querySelector('#blank-docs');input.files=dt.files;input.dispatchEvent(new Event('change',{bubbles:true}))");
  check('uploaded file never inherits sample extraction',await evaluate("!state.blank.sample&&state.blank.rows.length===0&&state.blank.regions.length===0&&document.querySelector('[data-action=blank-run]').disabled"));
  await evaluate("document.querySelector('[data-action=home]').click()");
  check('blank workspace can return Home',await evaluate("window.__foundationLite.getState().screen==='home'"));

  await evaluate("document.querySelector('[data-action=start-workflow]').click()");
  check('Local File starter opens the Workflow Profile',await evaluate("window.__foundationLite.getState().screen==='workflow'&&window.__foundationLite.getState().stage==='input'"));
  check('profile intake has exactly three named document roles',await evaluate("document.querySelectorAll('.profile-slot').length===3&&['Previous Local File','Current-year sources','Master template'].every(x=>document.querySelector('#main').textContent.includes(x))"));
  check('profile explicitly covers the retained GTPS scope',await evaluate("['NCP 14.18% → 6.08%','Processing Services conflict','Current benchmark missing','FAR matrix','Current regulatory wording'].every(x=>document.querySelector('#main').textContent.includes(x))"));
  await evaluate("document.querySelector('[data-action=prepare]').click()");
  check('assessment prepares all 21 GTPS targets',await evaluate("window.__foundationLite.getState().prepared&&window.__foundationLite.getState().stage==='review'&&window.__foundationLite.getState().items.length===21&&document.querySelectorAll('.stage-button').length===3"));
  check('known cases retain fail-closed evidence states',await evaluate("(()=>{const s=window.__foundationLite.getState(),by=id=>s.items.find(x=>x.id===id);return by('ncp').status==='READY'&&by('processing').status==='BLOCKED'&&by('benchmark').status==='BLOCKED'&&by('on-behalf').status==='NEEDS_REVIEW'&&by('protected').status==='PROTECTED'})()"));
  await evaluate("document.querySelector('[data-action=stage][data-id=review]').click()");
  check('evidence view continues to explicit human review',await evaluate("window.__foundationLite.getState().stage==='review'&&Boolean(document.querySelector('.decision-bar'))"));

  await evaluate("document.querySelector('.task[data-id=ncp]').click();document.querySelector('[data-action=open-viewer]').click()");
  check('NCP source viewer navigates to exact formula context',await evaluate("document.querySelector('#viewer-body').textContent.includes('FS!D65')&&document.querySelector('#viewer-body').textContent.includes('D61')"));
  await evaluate("document.querySelector('[data-action=approve]').click()");
  check('NCP can be approved from verified evidence',await evaluate("window.__foundationLite.getState().items.find(x=>x.id==='ncp').decision==='APPROVED'"));
  await evaluate("document.querySelector('[data-action=undo]').click()");
  check('Local File Undo restores approval',await evaluate("state.items.find(x=>x.id==='ncp').decision==='PENDING'"));
  await evaluate("document.querySelector('[data-action=approve]').click()");


  await evaluate("document.querySelector('.task[data-id=processing]').click()");
  check('Processing Services conflict requires explicit source choice',await evaluate("document.querySelectorAll('.conflict-option').length===2&&!document.querySelector('[data-action=approve]')"));
  await evaluate("document.querySelector('.conflict-option[data-id=summary]').click()");
  check('Processing Services conflict resolves only after human choice',await evaluate("(()=>{const x=window.__foundationLite.getState().items.find(x=>x.id==='processing');return x.status==='READY'&&x.selectedOption==='summary'&&x.value==='VND 193,729,728,552'})()"));
  await evaluate("document.querySelector('[data-action=approve]').click()");

  await evaluate("document.querySelector('.task[data-id=benchmark]').click()");
  check('missing benchmark cannot be approved',await evaluate("!document.querySelector('[data-action=approve]')&&Boolean(document.querySelector('[data-action=request-source]'))"));
  await evaluate("document.querySelector('[data-action=request-source]').click()");
  check('missing benchmark becomes an explicit source request',await evaluate("window.__foundationLite.getState().items.find(x=>x.id==='benchmark').decision==='REQUEST_MORE_SOURCE'"));

  await evaluate("document.querySelector('.task[data-id=on-behalf]').click()");
  check('ambiguous mapping cannot be approved before confirmation',await evaluate("!document.querySelector('[data-action=approve]')&&Boolean(document.querySelector('[data-action=resolve-mapping]'))"));
  await evaluate("document.querySelector('[data-action=resolve-mapping]').click();document.querySelector('[data-action=approve]').click()");
  check('mapping approval follows explicit mapping confirmation',await evaluate("(()=>{const x=window.__foundationLite.getState().items.find(x=>x.id==='on-behalf');return x.status==='READY'&&x.decision==='APPROVED'})()"));

  const expandedLayout=await evaluate("document.querySelector('.main').getBoundingClientRect().width");
  await evaluate("document.querySelector('#sidebar-toggle').click()");
  check('workflow navigation sidebar collapses without hiding stage rail',await evaluate(`document.querySelector('.shell').classList.contains('left-collapsed')&&getComputedStyle(document.querySelector('.global')).display==='none'&&document.querySelector('.rail').offsetParent!==null&&document.querySelector('.main').getBoundingClientRect().width>${expandedLayout}`));
  await evaluate("document.querySelector('#sidebar-toggle').click()");

  await evaluate("document.querySelector('[data-action=output]').click()");
  check('output includes only explicitly approved changes',await evaluate("(()=>{const s=window.__foundationLite.getState();return s.stage==='output'&&s.output.included.length===3&&['ncp','processing','on-behalf'].every(id=>s.output.included.some(x=>x.id===id))&&!s.output.included.some(x=>x.id==='benchmark')})()"));
  check('whole-workflow release remains withheld',await evaluate("document.querySelector('#main').textContent.includes('Release withheld')&&document.querySelector('[data-action=download-docx]').disabled"));
  check('right panel previews approved output without claiming a DOCX',await evaluate("document.querySelectorAll('.preview-change').length===3&&document.querySelector('#viewer-body').textContent.includes('No DOCX has been generated or modified')"));

  const viewerExpandedWidth=await evaluate("document.querySelector('.main').getBoundingClientRect().width");
  await evaluate("document.querySelector('#viewer-collapse').click()");
  check('right preview panel collapses and returns space',await evaluate(`document.querySelector('.shell').classList.contains('viewer-collapsed')&&getComputedStyle(document.querySelector('.viewer')).display==='none'&&document.querySelector('.main').getBoundingClientRect().width>${viewerExpandedWidth}`));
  const openerMetrics=await evaluate("(()=>{const fixed=document.querySelector('#viewer-reopen'),header=document.querySelector('#open-viewer'),visible=x=>{const s=getComputedStyle(x),r=x.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};return{visibleCount:[fixed,header].filter(visible).length,fixedVisible:visible(fixed),headerVisible:visible(header)}})()");
  check('desktop exposes exactly one right-panel opener',openerMetrics.visibleCount===1&&openerMetrics.fixedVisible&&!openerMetrics.headerVisible,JSON.stringify(openerMetrics));
  check('desktop panel collapse has no gray overlay',await evaluate("!document.querySelector('.drawer-shade').classList.contains('open')&&getComputedStyle(document.querySelector('.drawer-shade')).display==='none'"));
  await evaluate("document.querySelector('#viewer-reopen').click()");
  check('right preview panel reopens',await evaluate("!document.querySelector('.shell').classList.contains('viewer-collapsed')&&getComputedStyle(document.querySelector('.viewer')).display!=='none'"));
  await evaluate("document.querySelector('#main').click()");
  check('workspace clicks do not close the reopened desktop panel',await evaluate("!document.querySelector('.shell').classList.contains('viewer-collapsed')&&getComputedStyle(document.querySelector('.viewer')).display!=='none'"));

  await evaluate("document.querySelector('[data-action=stage][data-id=review]').click();document.querySelector('.task[data-id=ncp]').click();document.querySelector('[data-action=open-viewer]').click();const grid=document.querySelector('.grid');grid.scrollLeft=80;grid.dispatchEvent(new Event('scroll'))");await sleep(40);
  check('scrollbar appears only while a source surface scrolls',await evaluate("document.querySelector('.grid').classList.contains('is-scrolling')"));
  await sleep(720);
  check('source scrollbar returns to hidden resting state',await evaluate("!document.querySelector('.grid').classList.contains('is-scrolling')"));

  await evaluate("document.querySelector('#nav0').click()");
  check('workflow always has a clear route back Home',await evaluate("window.__foundationLite.getState().screen==='home'"));
  const sourceBefore=await evaluate("D.sourceData.documents.prior.elements.find(x=>x.text)?.text||''");await evaluate("document.querySelector('[data-action=lang][data-id=vi]').click()");const sourceAfter=await evaluate("D.sourceData.documents.prior.elements.find(x=>x.text)?.text||''");
  check('EN/VI changes UI without changing source content',sourceBefore===sourceAfter&&await evaluate("document.querySelector('#main').textContent.includes('Không gian xử lý tài liệu thông minh')"));

  for(const [width,height] of [[1920,1080],[1366,768],[1024,768],[390,844]]){
   await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width===390});await evaluate('layoutProbe()');
   check(`no horizontal overflow at ${width}×${height}`,await evaluate("document.body.dataset.horizontalOverflow==='NONE'"));
   check(`visible controls fit at ${width}×${height}`,await evaluate("[...document.querySelectorAll('button')].filter(x=>x.offsetParent).every(x=>{const r=x.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth})"));
   if(process.env.FOUNDATION_LITE_SCREENSHOT_DIR){const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});writeFileSync(join(process.env.FOUNDATION_LITE_SCREENSHOT_DIR,`foundation-lite-${width}.png`),Buffer.from(shot.data,'base64'))}
  }

  await evaluate("state.lang='en';openBlank();blankSample();blankRegion('customer');blankRegion('total')");
  for(const [width,height] of [[1920,1080],[1366,768],[1024,768],[390,844]]){
   await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width===390});
   await evaluate("state.blank.stage='input';render();document.querySelector('.info-tip').focus()");
   check(`blank tooltip fits at ${width}`,await evaluate("(()=>{const r=document.querySelector('.tip-content').getBoundingClientRect();return r.width>0&&r.left>=0&&r.right<=innerWidth})()"));
   await evaluate("document.querySelector('.info-tip').blur()");
   for(const stage of ['input','review','output']){
    if(stage==='review')await evaluate('blankRun()');
    if(stage==='output')await evaluate("blankDecision('customer','ACCEPTED');blankDecision('total','SKIPPED');blankOutput()");
    check(`blank ${stage} controls and footer fit at ${width}`,await evaluate("(()=>{const r=document.querySelector('#footer').getBoundingClientRect();return r.bottom<=innerHeight+1&&r.top>=0&&document.documentElement.scrollWidth<=innerWidth&&[...document.querySelectorAll('#main button,#footer button')].filter(x=>x.offsetParent).every(x=>{const b=x.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth})})()"));
    check(`blank ${stage} content can scroll to its end at ${width}`,await evaluate("(()=>{const m=document.querySelector('#main');m.scrollTop=m.scrollHeight;return m.scrollHeight-m.clientHeight-m.scrollTop<2&&getComputedStyle(m).overflowY==='auto'})()"));
    if(process.env.FOUNDATION_LITE_SCREENSHOT_DIR){await evaluate("document.querySelector('#main').scrollTop=0");const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});writeFileSync(join(process.env.FOUNDATION_LITE_SCREENSHOT_DIR,`foundation-blank-${stage}-${width}.png`),Buffer.from(shot.data,'base64'))}
   }
  }
  await evaluate("state.blank.stage='input';render();(()=>{const dt=new DataTransfer();dt.items.add(new File(['template'],'layout.docx'));const input=document.querySelector('#blank-template');input.files=dt.files;input.dispatchEvent(new Event('change',{bubbles:true}))})()");
  check('arbitrary template invalidates review and cannot be applied as sample',await evaluate("state.blank.rows.length===0&&document.querySelector('[data-action=blank-run]').disabled"));
  await evaluate("document.querySelector('[data-action=blank-remove-template]').click()");
  check('removing optional template restores sample execution',await evaluate("!document.querySelector('[data-action=blank-run]').disabled"));
  await evaluate("blankRun();blankDecision('customer','ACCEPTED');state.blank.stage='input';render();const field=document.querySelector('#blank-instruction');field.value='Changed request';field.dispatchEvent(new Event('input',{bubbles:true}))");
  check('request change invalidates accepted rows and undo history',await evaluate("state.blank.rows.length===0&&state.blank.undo.length===0"));
  check('blank hides unrelated source viewer control',await evaluate("getComputedStyle(document.querySelector('#open-viewer')).display==='none'"));
  await evaluate("document.querySelector('.mainhead>.mobile-only').click()");
  check('mobile blank workspace returns Home',await evaluate("state.screen==='home'"));
  check('browser interaction run has no runtime errors' ,runtimeErrors.length===0,runtimeErrors.join('; '));
 }catch(error){check('browser interaction suite completed',false,error.stack||error.message)}finally{try{ws?.close()}catch{}browser.kill();await new Promise(ok=>browser.once('exit',ok)).catch(()=>{});await sleep(500);try{rmSync(profile,{recursive:true,force:true,maxRetries:4,retryDelay:200})}catch{}}
}
const pass=results.filter(x=>x.result==='PASS').length;console.log(`Foundation MVP v5 lite acceptance: ${pass}/${results.length} PASS`);for(const x of results)console.log(`${x.result.padEnd(4)}  ${x.name}${x.detail?` — ${x.detail}`:''}`);if(process.exitCode)process.exit(process.exitCode);
