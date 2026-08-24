/**
 * test_rollforward_agent_dispatch.mjs
 *
 * Production acceptance for the P0 defect: inside an active Local File
 * Roll-Forward workflow, the request
 *
 *     "roll forward local file từ 2023 lên 2024 đi"
 *
 * came back as a long model-written report claiming the roll-forward was done,
 * while nothing had been executed. The answer had come from the GENERAL QUERY
 * path — the model had been asked to classify a workflow the server already knew.
 *
 * This test uploads the four real workflow files, sends that exact message, and
 * requires the FIRST answer to be deterministic workflow state: readiness or a
 * governed plan, never a generated result. It also verifies that approval is
 * refused rather than simulated when there is no governed plan to approve.
 *
 * Requires the Flask API and the Vite dev server.
 * Usage: node test_rollforward_agent_dispatch.mjs [url]
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
  template: path.join(DEMO, 'Compare LF',
    'Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx'),
  faRpt: path.join(DEMO, 'FA&RPTS & Appendix I', 'FA&RPTs', 'HMV-FA&RPT FY2024.xlsx'),
  appendixI: path.join(DEMO, 'FA&RPTS & Appendix I', 'Appendix I',
    'HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx'),
};

const PRODUCTION_MESSAGE = 'roll forward local file từ 2023 lên 2024 đi';
const UPLOAD_TIMEOUT = 180000;

let passed = 0;
let failed = 0;

function check(label, condition, detail = '') {
  if (condition) { passed += 1; console.log(`  [PASS] ${label}`); }
  else { failed += 1; console.log(`  [FAIL] ${label}${detail ? ` — ${detail}` : ''}`); }
}

function section(title) { console.log(`\n>>> ${title}`); }

async function uploadToSlot(page, slotId, filePath) {
  const before = await page.locator(
    `[data-testid="workflow-slot-${slotId}"] [data-testid^="slot-assignment-"]`)
    .evaluateAll((nodes) => nodes.map((n) => n.getAttribute('data-testid')));
  const chooser = page.waitForEvent('filechooser');
  await page.locator(`[data-testid="slot-add-${slotId}"]`).first().click();
  (await chooser).setFiles(filePath);
  await page.waitForFunction(({ slot, previous }) => {
    const ids = Array.from(document.querySelectorAll(
      `[data-testid="workflow-slot-${slot}"] [data-testid^="slot-assignment-"]`))
      .map((n) => n.getAttribute('data-testid'));
    return ids.length !== previous.length || ids.some((id) => !previous.includes(id));
  }, { slot: slotId, previous: before }, { timeout: UPLOAD_TIMEOUT });
}

async function run() {
  console.log('='.repeat(70));
  console.log('ROLL-FORWARD REQUEST DISPATCH — PRODUCTION ACCEPTANCE');
  console.log('='.repeat(70));

  const browser = await chromium.launch({ headless: true });
  const page = await (await browser.newContext({ viewport: { width: 1500, height: 1000 } })).newPage();

  // Every agent response, so the intent can be read from the wire rather than
  // inferred from the rendering.
  const agentResponses = [];
  page.on('response', async (res) => {
    if (!/\/api\/agent\/(chat|rollforward)/.test(res.url())) return;
    try { agentResponses.push({ url: res.url(), status: res.status(), body: await res.json() }); }
    catch { /* non-json */ }
  });

  try {
    await page.goto(TARGET_URL);
    await page.waitForLoadState('networkidle');

    // ------------------------------------------------------------------
    section('1. SET UP THE WORKFLOW WITH FOUR REAL FILES');
    // ------------------------------------------------------------------
    await page.locator('[data-testid="start-workflow-LOCAL_FILE_ROLL_FORWARD"]').click();
    await page.locator('[data-testid="workflow-intake-panel"]').waitFor({ state: 'visible' });

    await uploadToSlot(page, 'HISTORICAL_LOCAL_FILE', FIXTURES.historical);
    await uploadToSlot(page, 'CURRENT_YEAR_SOURCES', FIXTURES.faRpt);
    await uploadToSlot(page, 'CURRENT_YEAR_SOURCES', FIXTURES.appendixI);
    await uploadToSlot(page, 'MASTER_TEMPLATE', FIXTURES.template);
    check('All four workflow inputs are in their slots',
      (await page.locator('[data-testid^="slot-assignment-"]').count()) === 4);

    // ------------------------------------------------------------------
    section('2. SEND THE EXACT PRODUCTION MESSAGE');
    // ------------------------------------------------------------------
    const composer = page.locator('textarea, input[type="text"]').filter({
      hasNot: page.locator('[data-testid="rf-approver-input"]'),
    }).first();
    await composer.fill(PRODUCTION_MESSAGE);

    const started = Date.now();
    await composer.press('Enter');
    await page.locator('[data-testid="roll-forward-state"]').first()
      .waitFor({ state: 'visible', timeout: 120000 });
    const elapsed = Date.now() - started;

    const chat = agentResponses.find((r) => r.url.includes('/api/agent/chat'));
    check('The Agent answered', Boolean(chat), JSON.stringify(agentResponses.map(r => r.url)));

    // ------------------------------------------------------------------
    section('3. THE ANSWER IS WORKFLOW STATE, NOT A GENERATED REPORT');
    // ------------------------------------------------------------------
    check('intent is roll_forward', chat?.body?.intent === 'roll_forward', chat?.body?.intent);
    check('intent is NOT general_query', chat?.body?.intent !== 'general_query');
    check('no roll_forward_result is claimed', !chat?.body?.roll_forward_result);
    check('a deterministic assessment is attached', Boolean(chat?.body?.roll_forward_assessment));

    const assessment = chat?.body?.roll_forward_assessment ?? {};
    check('the assessment names the workflow',
      assessment.workflow === 'LOCAL_FILE_ROLL_FORWARD', assessment.workflow);
    check('periods were read from the documents, not the request',
      assessment.periods?.historical_period === 'FY2023'
      && assessment.periods?.current_period === 'FY2024',
      `${assessment.periods?.historical_period} -> ${assessment.periods?.current_period}`);

    const usedDocs = [
      assessment.historical_document_id,
      ...(assessment.current_source_document_ids ?? []),
      assessment.template_document_id,
    ].filter(Boolean);
    check('only the workflow slot documents are used', usedDocs.length === 4, String(usedDocs.length));

    // ------------------------------------------------------------------
    section('4. NO FABRICATED COMPLETION, NO FABRICATED SOURCES');
    // ------------------------------------------------------------------
    const answer = (chat?.body?.response ?? '').toLowerCase();
    check('the answer does not claim completion',
      !/completed successfully|roll-forward completed|đã hoàn thành/.test(answer),
      answer.slice(0, 80));
    check('the answer states nothing was modified',
      answer.includes('no document has been modified') || answer.includes('plan'),
      answer.slice(0, 80));
    for (const invented of ['industry report', 'annual report', 'benchmarking dataset']) {
      check(`the answer does not cite an invented "${invented}"`, !answer.includes(invented));
    }

    // ------------------------------------------------------------------
    section('5. THE UI SHOWS THE DETERMINISTIC STATE');
    // ------------------------------------------------------------------
    const card = page.locator('[data-testid="roll-forward-state"]').first();
    const stage = await card.getAttribute('data-stage');
    check('the card reflects the server stage', ['BLOCKED', 'PLAN_UNAVAILABLE', 'PLAN_READY'].includes(stage), stage);

    const uiState = assessment.ui_state;
    check('the card carries a real UI state',
      ['NOT_READY', 'REQUIRES_MANUAL_REVIEW', 'PLAN_READY'].includes(uiState), uiState);
    check('PLAN_UNAVAILABLE is no longer a user-facing state', uiState !== 'PLAN_UNAVAILABLE');

    if (stage === 'PLAN_READY') {
      check('the plan shows real counts',
        (await page.locator('[data-testid="rf-plan-tables"]').count()) === 1);
      check('the plan shows where its values come from',
        (await page.locator('[data-testid="rf-plan-provenance"]').count()) === 1);
      check('[Review Plan] is offered',
        (await page.locator('[data-testid="rf-review-plan"]').count()) === 1);
      check('[Approve & Execute] is offered only with executable regions',
        (await page.locator('[data-testid="rf-approve-execute"]').count()) === 1);
      check('the plan is not approved yet', assessment.plan?.approved === false);
    } else {
      check('blockers are listed', (await page.locator('[data-testid^="rf-blocker-"]').count()) > 0);
      check('the blockers come from planning, not from a guess',
        (assessment.blockers ?? []).some((b) => ['NO_EXECUTABLE_REGION', 'MISSING_SOURCE',
          'HUMAN_REVIEW', 'UNSUPPORTED_DOMAIN'].includes(b.code)),
        JSON.stringify((assessment.blockers ?? []).map((b) => b.code)));
      check('[Approve & Execute] is NOT offered without executable regions',
        (await page.locator('[data-testid="rf-approve-execute"]').count()) === 0);
      check('no completed-output card is shown',
        (await page.locator('[data-testid="roll-forward-result"]').count()) === 0);
    }

    // ------------------------------------------------------------------
    section('6. TIMING — DETERMINISTIC DISPATCH IS NOT AN LLM ROUND TRIP');
    // ------------------------------------------------------------------
    check('the first answer arrived without an LLM round trip (< 12s, was ~18s of model time)',
      elapsed < 12000, `${elapsed}ms`);
    check('planning time is reported per stage',
      Object.keys(assessment.timings_ms ?? {}).some((k) => k.startsWith('plan')),
      JSON.stringify(assessment.timings_ms));
    const timings = assessment.timings_ms ?? {};
    console.log(`      stage timings: ${JSON.stringify(timings)}  |  end-to-end: ${elapsed}ms`);

    // ------------------------------------------------------------------
    section('7. APPROVAL IS REFUSED WITHOUT A GOVERNED PLAN');
    // ------------------------------------------------------------------
    const sessionId = await page.evaluate(
      () => JSON.parse(localStorage.getItem('foundation_active_session') || '{}').sessionId);
    const approval = await page.evaluate(async ({ api, sid }) => {
      const res = await fetch(`${api}/api/agent/rollforward/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sid, approver: 'partner@firm.com' }),
      });
      return { status: res.status, body: await res.json() };
    }, { api: API_URL, sid: sessionId });

    check('approval without a governed plan is refused, not simulated',
      approval.status === 409, String(approval.status));
    check('the refusal explains itself',
      /no governed roll-forward plan|not executable/i.test(approval.body?.error ?? ''),
      approval.body?.error);
    check('the refusal carries no result', !approval.body?.roll_forward_result);
  } catch (error) {
    failed += 1;
    console.log(`\n  [ERROR] ${error.message}`);
    await page.screenshot({ path: path.join(__dirname, 'rollforward_dispatch_failure.png') })
      .catch(() => {});
  } finally {
    console.log(`\n${'='.repeat(70)}`);
    console.log(`RESULT: ${passed} passed, ${failed} failed`);
    console.log('='.repeat(70));
    await browser.close();
    process.exit(failed === 0 ? 0 : 1);
  }
}

run();
