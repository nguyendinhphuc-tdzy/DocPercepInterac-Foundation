/**
 * test_interaction_context.mjs
 *
 * P0-A: selecting evidence is a stateful user action, not a decorative chip.
 *
 * The production bug: the user clicked an element, the chip said
 * "Selected: …", the user typed a prompt — and by the time the request reached
 * the Agent the selection was gone, so the answer came from the prompt alone.
 *
 * This drives the real app and asserts the selection survives typing, editing
 * and sending, that it is actually in the POST body, that its element_id is the
 * one the user clicked, and that Deselect removes it from the NEXT request.
 *
 * Usage: node test_interaction_context.mjs [url]
 */
import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const TARGET_URL = process.argv[2] || 'http://localhost:5173';
const DEMO = path.resolve(__dirname, '..', 'anonymize client', 'Demo files', 'Demo files');
const FIXTURE = path.join(DEMO, 'FA&RPTS & Appendix I', 'FA&RPTs', 'HMV-FA&RPT FY2024.xlsx');
const HISTORICAL = path.join(DEMO, 'Compare LF',
  'HMV-24-Final-Local File for FY2023-EN-R0303KPMG.docx');

let passed = 0;
let failed = 0;

function check(label, condition, detail = '') {
  if (condition) { passed += 1; console.log(`  [PASS] ${label}`); }
  else { failed += 1; console.log(`  [FAIL] ${label}${detail ? ` — ${detail}` : ''}`); }
}
function section(title) { console.log(`\n>>> ${title}`); }

/** Back to the Agent layout, where the composer and its chip live. */
async function openAgentPane(page) {
  await page.locator('button[title="Change workspace layout"]').first().click();
  await page.waitForTimeout(400);
  await page.locator('span:text-is("Agent")').first().click();
  await page.locator('textarea').first().waitFor({ state: 'visible', timeout: 30000 });
}

/** Switch to the Inspect layout and expand a group so real elements render. */
async function openElementsPane(page) {
  await page.locator('button[title="Change workspace layout"]').first().click();
  await page.waitForTimeout(400);
  await page.locator('span:text-is("Inspect")').first().click();
  await page.locator('.element-tree').first().waitFor({ state: 'visible', timeout: 240000 });

  const header = page.locator('.element-tree-group-header').first();
  await header.waitFor({ state: 'visible', timeout: 240000 });
  await header.click();
  await page.waitForTimeout(600);
}

async function run() {
  console.log('='.repeat(70));
  console.log('INTERACTION CONTEXT — SELECTION SURVIVES AND TRAVELS');
  console.log('='.repeat(70));

  const browser = await chromium.launch({ headless: true });
  const page = await (await browser.newContext({ viewport: { width: 1500, height: 1000 } })).newPage();

  // Capture the actual request bodies — the only way to prove what was sent.
  const chatRequests = [];
  page.on('request', (request) => {
    if (request.url().includes('/api/agent/chat') && request.method() === 'POST') {
      try { chatRequests.push(JSON.parse(request.postData() ?? '{}')); } catch { /* ignore */ }
    }
  });

  try {
    await page.goto(TARGET_URL);
    await page.waitForLoadState('networkidle');

    // ------------------------------------------------------------------
    section('1. UPLOAD A REAL DOCUMENT AND SELECT A REAL ELEMENT');
    // ------------------------------------------------------------------
    await page.locator('button:has-text("Open Workspace")').click();
    const chooser = page.waitForEvent('filechooser');
    await page.locator('button[title="Add documents"]').click();
    (await chooser).setFiles(FIXTURE);
    await page.locator('.file-rail-item').first().waitFor({ state: 'visible', timeout: 180000 });

    await openElementsPane(page);
    const element = page.locator('[data-element-id]').first();
    await element.waitFor({ state: 'visible', timeout: 180000 });
    const elementId = await element.getAttribute('data-element-id');
    await element.click();
    check('An element was clicked', Boolean(elementId), String(elementId));

    // The composer lives in the Agent layout. Switching layout is not a context
    // change, so the selection must survive it.
    await openAgentPane(page);

    // ------------------------------------------------------------------
    section('2. THE CHIP APPEARS, AND SURVIVES TYPING');
    // ------------------------------------------------------------------
    const chip = page.locator('[data-testid="selection-chip"]');
    await chip.waitFor({ state: 'visible', timeout: 15000 });
    check('Selection chip is shown', await chip.isVisible());
    check('The chip names the element that was clicked',
      (await chip.getAttribute('data-element-id')) === elementId,
      `${await chip.getAttribute('data-element-id')} vs ${elementId}`);

    const composer = page.locator('textarea').first();
    await composer.click();
    await composer.type('Explain this value', { delay: 15 });
    check('Selection survives typing', await chip.isVisible());
    check('The chip still names the same element',
      (await chip.getAttribute('data-element-id')) === elementId);

    await composer.press('Backspace');
    await composer.type('s please', { delay: 15 });
    check('Selection survives editing the prompt', await chip.isVisible());

    // ------------------------------------------------------------------
    section('3. THE REQUEST CARRIES THE SELECTION');
    // ------------------------------------------------------------------
    await composer.press('Enter');
    await page.waitForTimeout(2500);

    const first = chatRequests[0];
    check('A chat request was sent', Boolean(first));
    const context = first?.interaction_context;
    check('interaction_context is present', Boolean(context));
    check('interaction_context.selected_elements is non-empty',
      (context?.selected_elements?.length ?? 0) > 0,
      JSON.stringify(context?.selected_elements ?? []));
    check('the selected element_id is the one clicked',
      context?.selected_elements?.[0]?.element_id === elementId,
      `${context?.selected_elements?.[0]?.element_id} vs ${elementId}`);
    check('the selection carries its own document_id',
      Boolean(context?.selected_elements?.[0]?.document_id));
    check('the selection carries location metadata',
      typeof context?.selected_elements?.[0]?.location === 'object');

    // ------------------------------------------------------------------
    section('4. THE SELECTION SURVIVES THE SEND');
    // ------------------------------------------------------------------
    check('Selection is still shown after sending', await chip.isVisible());
    check('It is still the same element',
      (await chip.getAttribute('data-element-id')) === elementId);

    // ------------------------------------------------------------------
    section('5. DESELECT REMOVES IT FROM THE NEXT REQUEST');
    // ------------------------------------------------------------------
    await page.locator('[data-testid="composer-deselect"]').click();
    await page.waitForTimeout(300);
    check('Chip disappears after Deselect', (await chip.count()) === 0);

    const beforeSecond = chatRequests.length;
    // This environment has no provider credentials, so the first turn ends in an
    // explicit model-failure card. Dismissing it is what a user would do; the
    // selection state under test is unaffected either way.
    const dismiss = page.locator('button[aria-label="Dismiss error"]').first();
    if (await dismiss.count()) await dismiss.click().catch(() => {});
    await page.waitForTimeout(500);
    const composerAgain = page.locator('textarea').first();
    await composerAgain.click();
    await composerAgain.type('Summarise the workspace', { delay: 10 });
    await composerAgain.press('Enter');
    await page.waitForFunction(() => true);
    await page.waitForTimeout(4000);

    const second = chatRequests[beforeSecond];
    check('A second request was sent', Boolean(second));
    check('the second request carries no selected elements',
      (second?.interaction_context?.selected_elements?.length ?? 0) === 0,
      JSON.stringify(second?.interaction_context?.selected_elements ?? []));

    // ------------------------------------------------------------------
    section('6. WORKFLOW + SELECTION TRAVEL TOGETHER');
    // ------------------------------------------------------------------
    // A fresh visit: clear the remembered session so Home (and the workflow
    // starter) is what loads, rather than the restored workspace.
    await page.evaluate(() => localStorage.clear());
    await page.goto(TARGET_URL);
    await page.waitForLoadState('networkidle');
    await page.locator('[data-testid="start-workflow-LOCAL_FILE_ROLL_FORWARD"]')
      .waitFor({ state: 'visible', timeout: 30000 });
    await page.locator('[data-testid="start-workflow-LOCAL_FILE_ROLL_FORWARD"]').click();
    await page.locator('[data-testid="workflow-intake-panel"]').waitFor({ state: 'visible' });

    const slotChooser = page.waitForEvent('filechooser');
    await page.locator('[data-testid="slot-add-HISTORICAL_LOCAL_FILE"]').click();
    (await slotChooser).setFiles(HISTORICAL);
    const slotCard = page.locator('[data-testid^="slot-assignment-"]').first();
    await slotCard.waitFor({ state: 'visible', timeout: 240000 });
    // Open the slot's document in the viewer — until it is active, the elements
    // pane has nothing to list.
    await slotCard.locator('button').first().click();
    await page.waitForTimeout(2000);
    await openElementsPane(page);
    const workflowGroup = page.locator('.element-tree-group, button:has(.element-group-name)').first();
    if (await workflowGroup.count()) await workflowGroup.click().catch(() => {});
    await page.waitForTimeout(500);
    const workflowElement = page.locator('[data-element-id]').first();
    await workflowElement.waitFor({ state: 'visible', timeout: 240000 });
    const workflowElementId = await workflowElement.getAttribute('data-element-id');
    await workflowElement.click();
    await openAgentPane(page);
    await page.locator('[data-testid="selection-chip"]').waitFor({ state: 'visible', timeout: 20000 });

    const before = chatRequests.length;
    const workflowComposer = page.locator('textarea').first();
    await workflowComposer.click();
    await workflowComposer.type('Explain this selected item.', { delay: 10 });
    await workflowComposer.press('Enter');
    await page.waitForTimeout(3000);

    const workflowRequest = chatRequests[before];
    check('A request was sent inside the workflow', Boolean(workflowRequest));
    const workflowContext = workflowRequest?.interaction_context;
    check('workflow_type travels with the selection',
      workflowContext?.workflow_type === 'LOCAL_FILE_ROLL_FORWARD',
      String(workflowContext?.workflow_type));
    check('the selected element travels with the workflow',
      workflowContext?.selected_elements?.[0]?.element_id === workflowElementId,
      `${workflowContext?.selected_elements?.[0]?.element_id} vs ${workflowElementId}`);

    await page.screenshot({ path: path.join(__dirname, 'interaction_context_evidence.png') });
  } catch (error) {
    failed += 1;
    console.log(`\n  [ERROR] ${error.message}`);
    await page.screenshot({ path: path.join(__dirname, 'interaction_context_failure.png') })
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
