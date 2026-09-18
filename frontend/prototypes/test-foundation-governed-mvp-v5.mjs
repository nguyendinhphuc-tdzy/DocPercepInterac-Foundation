import { createHash } from 'node:crypto';
import { spawn, spawnSync } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const htmlPath = join(here, 'foundation-governed-document-processing-mvp-v5.html');
const sourcePath = process.env.FOUNDATION_V4_SOURCE;
const html = readFileSync(htmlPath, 'utf8');
const results = [];
const check = (name, pass, detail = '') => {
  results.push({ name, result: pass ? 'PASS' : 'FAIL', detail });
  if (!pass) process.exitCode = 1;
};

const dataMatch = html.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/);
check('embedded JSON exists once', Boolean(dataMatch) && (html.match(/id="data"/g) || []).length === 1);
let fixture;
try {
  fixture = JSON.parse(dataMatch?.[1] || '');
  check('embedded JSON parses', true);
} catch (error) {
  check('embedded JSON parses', false, error.message);
}
const appScripts = [...html.matchAll(/<script(?:\s+[^>]*)?>([\s\S]*?)<\/script>/g)];
const appJs = appScripts.at(-1)?.[1] || '';
const jsPath = join(tmpdir(), `foundation-v5-${process.pid}.js`);
writeFileSync(jsPath, appJs, 'utf8');
const syntax = spawnSync(process.execPath, ['--check', jsPath], { encoding: 'utf8' });
check('application JavaScript parses', syntax.status === 0, syntax.stderr.trim());
rmSync(jsPath, { force: true });

check('source v4 remains byte-identical', !sourcePath || (existsSync(sourcePath) && createHash('sha256').update(readFileSync(sourcePath)).digest('hex') === 'aa83c3790686f0f96ca7b3d9b10ee113d1e665f48e5f1aee5bd8da08e457b35a'), sourcePath ? 'verified from FOUNDATION_V4_SOURCE' : 'set FOUNDATION_V4_SOURCE to verify the external baseline');
check('Foundation identity is generic', html.includes('Foundation · Governed Document Processing'));
check('three business spaces are present', ['Inputs & Scope', 'Review & Resolve', 'Result & Audit'].every((text) => appJs.includes(text)));
check('required target scenarios are embedded', ['period', 'ncp', 'materials', 'processing', 'template-contents', 'on-behalf', 'registration', 'workforce', 'benchmark'].every((id) => fixture?.fixture?.changes?.some((item) => item.id === id)));
check('NCP facts are exact', fixture?.fixture?.changes?.some((item) => item.id === 'ncp' && item.before === '14.18%' && item.after === '6.08%' && item.formula));
check('source conflict facts are exact', fixture?.fixture?.changes?.some((item) => item.id === 'processing' && item.verdict === 'SOURCE_CONFLICT' && item.evidence.includes('193,729,728,552') && item.evidence.includes('196,138,816,993')));
check('source request lifecycle is closed', appJs.includes("['REQUESTED','INTAKE','ASSESSMENT','EVIDENCE','REVISED_PROPOSAL','IN_REVIEW']"));
check('CSP blocks external runtime requests', html.includes("connect-src 'none'") && html.includes("default-src 'none'"));
check('no external assets are declared', !/<(?:script|iframe)[^>]+src=["']https?:|<link[^>]+href=["']https?:|<img[^>]+src=["']https?:/i.test(html));
check('final DOCX is always disabled', appJs.includes("'download'") && appJs.includes('disabled title='));
check('localStorage persistence is explicit', appJs.includes('localStorage.setItem') && appJs.includes('localStorage.getItem'));
check('AI authority limit is explicit', appJs.includes('AI has zero approval and execution authority'));
check('Golden isolation is explicit', appJs.includes('Golden remained isolated from workflow evidence'));
check('partial reassessment is implemented', appJs.includes('PARTIAL_REASSESSMENT_STARTED') && appJs.includes('unaffected targets retain'));

const chromeCandidates = [
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
];
const chrome = chromeCandidates.find(existsSync);
check('browser runtime available', Boolean(chrome), chrome || 'Chrome/Edge not found');

if (chrome) {
  const profile = mkdtempSync(join(tmpdir(), 'foundation-v5-cdp-'));
  const port = 9400 + (process.pid % 300);
  const url = pathToFileURL(resolve(htmlPath)).href;
  const browser = spawn(chrome, [
    '--headless=new', '--disable-gpu', '--no-first-run', '--disable-default-apps',
    `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, '--window-size=1366,900', url,
  ], { stdio: 'ignore' });

  const sleep = (ms) => new Promise((resolvePromise) => setTimeout(resolvePromise, ms));
  let ws;
  try {
    let page;
    for (let attempt = 0; attempt < 80; attempt += 1) {
      try {
        const pages = await fetch(`http://127.0.0.1:${port}/json/list`).then((response) => response.json());
        page = pages.find((item) => item.type === 'page');
        if (page) break;
      } catch {}
      await sleep(100);
    }
    if (!page) throw new Error('Chrome DevTools page did not become available');
    ws = new WebSocket(page.webSocketDebuggerUrl);
    await new Promise((resolvePromise, reject) => {
      ws.addEventListener('open', resolvePromise, { once: true });
      ws.addEventListener('error', reject, { once: true });
    });
    let sequence = 0;
    const pending = new Map();
    ws.addEventListener('message', (event) => {
      const message = JSON.parse(event.data);
      if (!message.id || !pending.has(message.id)) return;
      const { resolve: done, reject } = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) reject(new Error(message.error.message)); else done(message.result);
    });
    const send = (method, params = {}) => new Promise((done, reject) => {
      const id = ++sequence;
      pending.set(id, { resolve: done, reject });
      ws.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async (expression) => {
      const answer = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
      if (answer.exceptionDetails) throw new Error(answer.exceptionDetails.text || 'Runtime evaluation failed');
      return answer.result.value;
    };
    await send('Runtime.enable');
    for (let attempt = 0; attempt < 50; attempt += 1) {
      if (await evaluate("document.readyState === 'complete' && Boolean(window.__foundationV5)")) break;
      await sleep(100);
    }
    const internal = await evaluate('window.__foundationV5.runSelfTests()');
    check('in-browser self-test suite', internal.result === 'PASS', JSON.stringify(internal.checks.filter((item) => item.result !== 'PASS')));

    await evaluate("window.__foundationV5.reset(); document.querySelector('[data-action=analyze]').click()");
    check('Analyze routes to target queue', await evaluate("window.__foundationV5.getState().space === 'review' && window.__foundationV5.getState().analyzed"));
    await evaluate("document.querySelector('[data-action=select-target][data-id=ncp]').click()");
    check('NCP detail renders complete lineage', await evaluate("window.__foundationV5.getState().selectedTarget==='ncp' && document.querySelectorAll('#main .lineage-card').length===3 && document.querySelector('#main').textContent.includes('14.18%') && document.querySelector('#main').textContent.includes('6.08%')"));
    const sourceBefore = await evaluate("D.sourceData.documents.prior.elements.find(x=>x.text)?.text || ''");
    await evaluate("document.querySelector('[data-action=lang][data-id=vi]').click()");
    const sourceAfter = await evaluate("D.sourceData.documents.prior.elements.find(x=>x.text)?.text || ''");
    check('EN/VI changes UI without translating source content', sourceBefore === sourceAfter && await evaluate("document.querySelector('#main').innerText.includes('Tỷ suất lợi nhuận') && document.querySelector('#main').innerText.includes('Workbook chứa công thức NCP')"));
    await evaluate("document.querySelector('[data-action=lang][data-id=en]').click(); document.querySelector('[data-action=back-queue]').click(); document.querySelector('[data-action=select-target][data-id=processing]').click(); document.querySelector('[data-action=request-source]').click()");
    for (let step = 0; step < 5; step += 1) await evaluate("document.querySelector('[data-action=advance-source]').click()");
    check('source request completes at IN_REVIEW', await evaluate("window.__foundationV5.getState().requests.processing.status === 'IN_REVIEW'"));
    check('new evidence does not auto-approve', await evaluate("window.__foundationV5.getState().targets.find(x=>x.id==='processing').decision === 'PENDING'"));
    check('processing conflict remains unresolved', await evaluate("window.__foundationV5.getState().targets.find(x=>x.id==='processing').verdict === 'SOURCE_CONFLICT'"));

    await evaluate("window.__foundationV5.reset(); document.querySelector('[data-action=analyze]').click(); document.querySelector('[data-action=select-target][data-id=ncp]').click(); document.querySelector('[data-action=edit-proposal]').click(); document.querySelector('#edited-proposal').value='6.08% reviewed'; document.querySelector('#edit-rationale').value='Reviewer wording clarification'; document.querySelector('[data-action=save-edit]').click()");
    check('reviewer edit creates revision and invalidates verification', await evaluate("(()=>{const x=window.__foundationV5.getState().targets.find(x=>x.id==='ncp'); return x.revision===2 && x.verdict==='REASSESSMENT_REQUIRED' && x.decision==='PENDING'})()"));
    await evaluate("document.querySelector('[data-action=reassess]').click()");
    check('edited proposal passes through reassessment', await evaluate("window.__foundationV5.getState().targets.find(x=>x.id==='ncp').verdict !== 'REASSESSMENT_REQUIRED'"));

    await evaluate("window.__foundationV5.reset(); document.querySelector('[data-action=analyze]').click(); document.querySelector('[data-action=select-target][data-id=on-behalf]').click(); document.querySelector('[data-action=resolve-mapping]').click(); document.querySelector('#mapping-rationale').value='Classified by transaction direction'; document.querySelector('[data-action=save-mapping]').click()");
    check('mapping decision requires reassessment', await evaluate("window.__foundationV5.getState().targets.find(x=>x.id==='on-behalf').verdict === 'REASSESSMENT_REQUIRED'"));
    await evaluate("document.querySelector('[data-action=reassess]').click()");
    check('mapping reassessment returns to review', await evaluate("(()=>{const x=window.__foundationV5.getState().targets.find(x=>x.id==='on-behalf'); return x.verdict==='VERIFIED' && x.decision==='PENDING'})()"));

    await evaluate("document.querySelector('[data-action=approve-ready]').click(); document.querySelector('#batch-rationale').value='Reviewed against cited evidence'; document.querySelector('[data-action=save-approve-ready]').click(); document.querySelector('[data-action=space][data-id=result]').click(); document.querySelector('[data-action=seal]').click(); document.querySelector('[data-action=simulate]').click(); document.querySelector('[data-action=validate]').click()");
    check('Approved ChangeSet contains only eligible targets', await evaluate("(()=>{const s=window.__foundationV5.getState(); const set=s.sealedSets.find(x=>x.id===s.activeSetId); return set.changes.length>0 && set.changes.every(c=>!['processing','registration','workforce','benchmark'].includes(c.target_id))})()"));
    check('partial completion and release withholding are independent', await evaluate("processingOutcome()==='PARTIALLY_COMPLETED' && releaseDecision()==='WITHHELD'"));
    check('validation is independent from simulated execution', await evaluate("(()=>{const s=window.__foundationV5.getState(); return s.output.replay_engine===undefined && Boolean(s.validation.validator) && s.validation.replay_engine==='Separate simulated executor'})()"));
    check('Final DOCX remains disabled', await evaluate("document.querySelector('[data-action=download]').disabled"));
    const conflictBefore = await evaluate("window.__foundationV5.getState().targets.find(x=>x.id==='processing').verdict");
    await evaluate("document.querySelector('[data-action=golden]').click()");
    const conflictAfter = await evaluate("window.__foundationV5.getState().targets.find(x=>x.id==='processing').verdict");
    check('Golden comparison preserves root cause', conflictBefore === 'SOURCE_CONFLICT' && conflictAfter === conflictBefore);
    await evaluate("document.querySelector('[data-action=close]').click(); document.querySelector('[data-action=space][data-id=review]').click(); document.querySelector('[data-action=partial-rerun]').click()");
    check('partial rerun invalidates affected target only', await evaluate("(()=>{const s=window.__foundationV5.getState(); return s.targets.find(x=>x.id==='ncp').verdict==='REASSESSMENT_REQUIRED' && s.targets.find(x=>x.id==='regulatory').decision==='APPROVED' && Boolean(s.partialNotice)})()"));
    await evaluate("document.querySelector('[data-action=select-target][data-id=regulatory]').click(); document.querySelector('[data-action=flag-rule]').click()");
    check('Flag processing rule suspends reuse', await evaluate("window.__foundationV5.getState().targets.find(x=>x.id==='regulatory').flagged"));
    const auditCount = await evaluate('window.__foundationV5.getState().audit.length');
    await evaluate('location.reload()');
    await sleep(500);
    check('refresh restores persisted workflow state', await evaluate(`window.__foundationV5.getState().audit.length === ${auditCount} && window.__foundationV5.getState().targets.find(x=>x.id==='regulatory').flagged`));

    for (const width of [1600, 1366, 1024, 768, 390]) {
      await send('Emulation.setDeviceMetricsOverride', { width, height: width === 390 ? 844 : 900, deviceScaleFactor: 1, mobile: width === 390 });
      await evaluate('updateLayoutProbe()');
      check(`no horizontal page overflow at ${width}px`, await evaluate("document.body.dataset.horizontalOverflow === 'NONE'"));
      check(`primary controls fit at ${width}px`, await evaluate("[...document.querySelectorAll('#main .btn.primary,#footer .btn')].filter(x=>x.offsetParent).every(x=>{const r=x.getBoundingClientRect(); return r.left>=0 && r.right<=innerWidth})"));
      if (process.env.FOUNDATION_V5_SCREENSHOT_DIR) {
        const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
        writeFileSync(join(process.env.FOUNDATION_V5_SCREENSHOT_DIR, `review-${width}-exact.png`), Buffer.from(shot.data, 'base64'));
      }
    }
    check('mobile rail and evidence controls are explicit', await evaluate("getComputedStyle(document.querySelector('[data-action=toggle-rail]')).display!=='none' && getComputedStyle(document.querySelector('[data-action=open-viewer]')).display!=='none'"));
    await evaluate("document.querySelector('[data-action=toggle-rail]').click(); document.querySelector('.mobile-utilities [data-action=assistant]').click()");
    check('mobile dialog stays inside viewport', await evaluate("(()=>{const r=document.querySelector('dialog').getBoundingClientRect(); return r.left>=0 && r.right<=innerWidth && r.top>=0 && r.bottom<=innerHeight})()"));
  } catch (error) {
    check('browser interaction suite completed', false, error.stack || error.message);
  } finally {
    try { ws?.close(); } catch {}
    browser.kill();
    await new Promise((resolvePromise) => browser.once('exit', resolvePromise)).catch(() => {});
    await sleep(500);
    try { rmSync(profile, { recursive: true, force: true, maxRetries: 4, retryDelay: 200 }); } catch {}
  }
}

const passed = results.filter((item) => item.result === 'PASS').length;
console.log(`Foundation MVP v5 acceptance: ${passed}/${results.length} PASS`);
for (const item of results) console.log(`${item.result.padEnd(4)}  ${item.name}${item.detail ? ` — ${item.detail}` : ''}`);
if (process.exitCode) process.exit(process.exitCode);
