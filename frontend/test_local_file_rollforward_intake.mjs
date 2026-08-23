/**
 * test_local_file_rollforward_intake.mjs
 *
 * Real user flow for the Local File Roll-Forward structured intake (Phase PROD-UX-1):
 *
 *   Start workflow from Home
 *     -> upload the historical Local File
 *     -> upload FA&RPT
 *     -> upload Appendix I
 *     -> upload the master template
 *     -> grouped document panel shows the three roles
 *     -> readiness summary appears
 *     -> domains with no source stay blocked
 *     -> execution gate opens only when all three inputs are present
 *     -> the Agent receives structured workflow context (ids per role)
 *
 * Then, with an intentionally wrong fixture:
 *     -> a current-year final Local File in the historical slot is a ROLE MISMATCH
 *     -> the mismatch names Expected vs Detected and offers Replace / Keep for review
 *     -> "Keep for Manual Review" is recorded, never silent
 *
 * Requires the Flask API (foundation/api/app.py) and the Vite dev server.
 * Usage: node test_local_file_rollforward_intake.mjs [url]
 */
import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const TARGET_URL = process.argv[2] || 'http://localhost:5173';
const API_URL = process.env.VITE_API_BASE_URL || 'http://localhost:5000';

const DEMO = path.resolve(__dirname, '..', 'anonymize client', 'Demo files', 'Demo files');
const FIXTURES = {
  historical: path.join(DEMO, 'Compare LF', 'HMV-24-Final-Local File for FY2023-EN-R0303KPMG.docx'),
  wrongHistorical: path.join(DEMO, 'Compare LF', 'HMV-26-Final-Local File for FY2024-EN-R2901KPMG.docx'),
  template: path.join(DEMO, 'Compare LF',
    'Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx'),
  faRpt: path.join(DEMO, 'FA&RPTS & Appendix I', 'FA&RPTs', 'HMV-FA&RPT FY2024.xlsx'),
  appendixI: path.join(DEMO, 'FA&RPTS & Appendix I', 'Appendix I',
    'HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx'),
};

const UPLOAD_TIMEOUT = 120000;

let passed = 0;
let failed = 0;

function check(label, condition, detail = '') {
  if (condition) {
    passed += 1;
    console.log(`  [PASS] ${label}`);
  } else {
    failed += 1;
    console.log(`  [FAIL] ${label}${detail ? ` — ${detail}` : ''}`);
  }
}

function section(title) {
  console.log(`\n>>> ${title}`);
}

/** Uploads one file into a named slot and waits for its role verdict to land.
 *
 * A single-file slot replaces its occupant rather than growing, so this waits
 * for the set of assignment ids to change rather than for the count to rise.
 */
async function assignmentIds(page, slotId) {
  return page.locator(`[data-testid="workflow-slot-${slotId}"] [data-testid^="slot-assignment-"]`)
    .evaluateAll((nodes) => nodes.map((n) => n.getAttribute('data-testid')));
}

async function uploadToSlot(page, slotId, filePath) {
  const before = await assignmentIds(page, slotId);
  const chooserPromise = page.waitForEvent('filechooser');
  await page.locator(`[data-testid="slot-add-${slotId}"]`).first().click();
  (await chooserPromise).setFiles(filePath);

  // Profiling a large workbook is synchronous server-side; wait for the card.
  await page.waitForFunction(
    ({ slot, previous }) => {
      const ids = Array.from(document.querySelectorAll(
        `[data-testid="workflow-slot-${slot}"] [data-testid^="slot-assignment-"]`))
        .map((n) => n.getAttribute('data-testid'));
      return ids.length !== previous.length || ids.some((id) => !previous.includes(id));
    },
    { slot: slotId, previous: before },
    { timeout: UPLOAD_TIMEOUT },
  );
}

async function slotValidation(page, slotId) {
  return page.locator(`[data-testid="workflow-slot-${slotId}"]`).first().getAttribute('data-validation');
}

async function readinessStatuses(page) {
  const rows = page.locator('[data-testid^="readiness-row-"]');
  const count = await rows.count();
  const statuses = {};
  for (let i = 0; i < count; i++) {
    const row = rows.nth(i);
    const id = (await row.getAttribute('data-testid')).replace('readiness-row-', '');
    statuses[id] = await row.getAttribute('data-status');
  }
  return statuses;
}

async function run() {
  console.log('='.repeat(64));
  console.log('LOCAL FILE ROLL-FORWARD — STRUCTURED INTAKE');
  console.log(`Target: ${TARGET_URL}  API: ${API_URL}`);
  console.log('='.repeat(64));

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 } });
  const page = await context.newPage();

  let sessionId = null;
  page.on('request', (request) => {
    const match = /\/api\/workflow\/([^/]+)\/slots\//.exec(request.url());
    if (match) sessionId = decodeURIComponent(match[1]);
  });
  page.on('console', (msg) => {
    if (msg.type() === 'error') console.log(`  [browser error] ${msg.text()}`);
  });

  try {
    await page.goto(TARGET_URL);
    await page.waitForLoadState('networkidle');

    // ------------------------------------------------------------------
    section('1. WORKFLOW STARTER ON HOME');
    // ------------------------------------------------------------------
    const starter = page.locator('[data-testid="workflow-starter-LOCAL_FILE_ROLL_FORWARD"]');
    check('Home offers the Local File Roll-Forward starter', await starter.isVisible());
    check('Starter states what the workflow does',
      (await starter.innerText()).includes("Update last year's Local File"));

    await page.locator('[data-testid="start-workflow-LOCAL_FILE_ROLL_FORWARD"]').click();
    await page.locator('[data-testid="workflow-intake-panel"]').waitFor({ state: 'visible', timeout: 15000 });

    // innerText reflects the panel's uppercase styling, so compare case-insensitively.
    const stepHeader = await page.locator('[data-testid="workflow-step-header"]').innerText();
    check('Lands on "Step 1 / 4 — Input Documents"',
      /step 1 \/ 4 — input documents/i.test(stepHeader), stepHeader);

    // ------------------------------------------------------------------
    section('2. NO GENERIC BLANK DOCUMENT WORKSPACE');
    // ------------------------------------------------------------------
    check('The role-less document list is not shown',
      (await page.locator('[aria-label="Documents collection"]').count()) === 0);
    for (const slot of ['HISTORICAL_LOCAL_FILE', 'CURRENT_YEAR_SOURCES', 'MASTER_TEMPLATE']) {
      check(`Slot ${slot} is presented up front`,
        await page.locator(`[data-testid="workflow-slot-${slot}"]`).first().isVisible());
    }
    check('Execution is blocked with an actionable message',
      (await page.locator('[data-testid="workflow-gate-message"]').innerText())
        .includes('Upload Previous Local File to continue.'));

    // ------------------------------------------------------------------
    section('3. HISTORICAL LOCAL FILE');
    // ------------------------------------------------------------------
    await uploadToSlot(page, 'HISTORICAL_LOCAL_FILE', FIXTURES.historical);
    check('FY2023 Local File is confirmed in the historical slot',
      (await slotValidation(page, 'HISTORICAL_LOCAL_FILE')) === 'ROLE_CONFIRMED');
    check('Its detected period comes from the content',
      (await page.locator('[data-testid="workflow-slot-HISTORICAL_LOCAL_FILE"]').innerText()).includes('FY2023'));
    check('Gate now asks for the current-year sources',
      (await page.locator('[data-testid="workflow-gate-message"]').innerText()).includes('Current-Year Sources'));

    // ------------------------------------------------------------------
    section('4. CURRENT-YEAR SOURCES (MULTI-FILE)');
    // ------------------------------------------------------------------
    await uploadToSlot(page, 'CURRENT_YEAR_SOURCES', FIXTURES.faRpt);
    await uploadToSlot(page, 'CURRENT_YEAR_SOURCES', FIXTURES.appendixI);

    const sourceCards = page.locator(
      '[data-testid="workflow-slot-CURRENT_YEAR_SOURCES"] [data-testid^="slot-assignment-"]');
    check('Both sources are held in the one slot', (await sourceCards.count()) === 2);
    check('The slot still offers [Add Source] for further files',
      await page.locator('[data-testid="slot-add-CURRENT_YEAR_SOURCES"]').isVisible());
    check('Both sources are confirmed',
      (await slotValidation(page, 'CURRENT_YEAR_SOURCES')) === 'ROLE_CONFIRMED');

    const panelText = await page.locator('[data-testid="workflow-intake-panel"]').innerText();
    check('Cards state format, perception and content version',
      panelText.includes('XLSX') && panelText.includes('Perceived') && panelText.includes('v·'));

    // ------------------------------------------------------------------
    section('5. READINESS SUMMARY');
    // ------------------------------------------------------------------
    const readiness = await readinessStatuses(page);
    check('Readiness summary is shown', Object.keys(readiness).length === 5, JSON.stringify(readiness));
    check('Related-party transactions is supported',
      readiness.RELATED_PARTY_TRANSACTIONS === 'SUPPORTED', readiness.RELATED_PARTY_TRANSACTIONS);
    check('Financial information is supported',
      readiness.FINANCIAL_INFORMATION === 'SUPPORTED', readiness.FINANCIAL_INFORMATION);
    check('Benchmarking stays blocked — no source supplies it',
      readiness.BENCHMARKING === 'BLOCKED', readiness.BENCHMARKING);
    check('FAR stays blocked — no source supplies it', readiness.FAR === 'BLOCKED', readiness.FAR);
    check('Organisation stays blocked — no source supplies it',
      readiness.ORGANISATION === 'BLOCKED', readiness.ORGANISATION);
    check('No internals leak into the summary',
      !/DATASET_ROLE|BLOCKED_MISSING_SOURCE|EvidencePolicy/i.test(
        await page.locator('[data-testid="readiness-summary"]').innerText()));

    // ------------------------------------------------------------------
    section('6. GATING UNTIL THE TEMPLATE ARRIVES');
    // ------------------------------------------------------------------
    check('Roll-forward is still blocked',
      (await page.locator('[data-testid="workflow-gate-message"]').getAttribute('data-execution-allowed')) === 'false');
    check('The block names the missing input',
      (await page.locator('[data-testid="workflow-gate-message"]').innerText())
        .includes('Upload Master Template to continue.'));

    await uploadToSlot(page, 'MASTER_TEMPLATE', FIXTURES.template);
    check('The blank template is confirmed by its content',
      (await slotValidation(page, 'MASTER_TEMPLATE')) === 'ROLE_CONFIRMED');
    check('All three inputs present — the gate opens',
      (await page.locator('[data-testid="workflow-gate-message"]').getAttribute('data-execution-allowed')) === 'true');

    // ------------------------------------------------------------------
    section('7. AGENT RECEIVES STRUCTURED WORKFLOW CONTEXT');
    // ------------------------------------------------------------------
    check('A workflow session id was established', Boolean(sessionId), String(sessionId));
    if (sessionId) {
      const agentContext = await page.evaluate(async ({ api, sid }) => {
        const response = await fetch(`${api}/api/workflow/${sid}/agent-context`);
        return response.json();
      }, { api: API_URL, sid: sessionId });

      check('Workflow is named, not inferred', agentContext.workflow === 'LOCAL_FILE_ROLL_FORWARD');
      check('Historical document id is carried', Boolean(agentContext.historical_document_id));
      check('Both current-year source ids are carried',
        Array.isArray(agentContext.current_source_document_ids)
        && agentContext.current_source_document_ids.length === 2);
      check('Template document id is carried', Boolean(agentContext.template_document_id));
      check('Periods come from content', agentContext.target_fiscal_year === 2024
        && agentContext.historical_fiscal_year === 2023,
        `${agentContext.historical_fiscal_year} -> ${agentContext.target_fiscal_year}`);
      check('Inputs are reported complete', agentContext.inputs_complete === true);
    }

    // ------------------------------------------------------------------
    section('8. ROLE MISMATCH WITH AN INTENTIONALLY WRONG FIXTURE');
    // ------------------------------------------------------------------
    await uploadToSlot(page, 'HISTORICAL_LOCAL_FILE', FIXTURES.wrongHistorical);
    // The single-file slot replaces its occupant, so the new card is the only one.
    const wrongCard = page.locator(
      '[data-testid="workflow-slot-HISTORICAL_LOCAL_FILE"] [data-testid^="slot-assignment-"]').first();
    await wrongCard.waitFor({ state: 'visible' });

    check('The same-period Local File is rejected, not silently accepted',
      (await wrongCard.getAttribute('data-validation')) === 'ROLE_MISMATCH');

    const mismatchText = await wrongCard.innerText();
    check('The mismatch is stated explicitly', mismatchText.includes('File role mismatch'));
    check('Expected role is shown', mismatchText.includes('Historical Local File'));
    check('Detected role is shown', mismatchText.includes('FY2024 Final Local File'));

    const docId = (await wrongCard.getAttribute('data-testid')).replace('slot-assignment-', '');
    check('[Replace File] is offered',
      await page.locator(`[data-testid="replace-file-${docId}"]`).isVisible());
    check('[Keep for Manual Review] is offered',
      await page.locator(`[data-testid="keep-for-review-${docId}"]`).isVisible());
    check('Execution is blocked again',
      (await page.locator('[data-testid="workflow-gate-message"]').getAttribute('data-execution-allowed')) === 'false');
    check('The valid sources were not blamed for it',
      (await slotValidation(page, 'CURRENT_YEAR_SOURCES')) === 'ROLE_CONFIRMED');

    // ------------------------------------------------------------------
    section('9. KEEPING A FLAGGED FILE IS RECORDED, NOT SILENT');
    // ------------------------------------------------------------------
    await page.locator(`[data-testid="keep-for-review-${docId}"]`).click();
    await page.waitForFunction(
      (id) => document.querySelector(`[data-testid="slot-assignment-${id}"]`)
        ?.getAttribute('data-validation') === 'HUMAN_REVIEW',
      docId,
      { timeout: 30000 },
    );
    check('The file is now flagged for human review',
      (await wrongCard.getAttribute('data-validation')) === 'HUMAN_REVIEW');
    check('The decision is visible on the card',
      (await wrongCard.innerText()).toLowerCase().includes('kept for manual review'));
  } catch (error) {
    failed += 1;
    console.log(`\n  [ERROR] ${error.message}`);
    await page.screenshot({ path: path.join(__dirname, 'rollforward_intake_failure.png') })
      .catch(() => {});
  } finally {
    console.log(`\n${'='.repeat(64)}`);
    console.log(`RESULT: ${passed} passed, ${failed} failed`);
    console.log('='.repeat(64));
    await browser.close();
    process.exit(failed === 0 ? 0 : 1);
  }
}

run();
