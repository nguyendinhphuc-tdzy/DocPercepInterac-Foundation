/**
 * test_agent_error_ux.mjs
 *
 * Acceptance suite for four-model provider error UX and fallback elimination.
 *
 * For every failing model (Luna, Sol, Gemini 3.6 Flash, Gemini 3.5 Flash) and
 * every provider error class (unavailable, config missing, quota exhausted,
 * auth failure), the UI must:
 *
 *   1. Show an explicit error card naming the model the user selected.
 *   2. Create NO assistant message — a failure is never dressed as an answer.
 *   3. Never name any other model, so the card cannot read as "something else
 *      already answered this".
 *   4. Preserve the user's prompt in the transcript.
 *   5. Offer [Retry <failed model>] that re-sends to the SAME model, even after
 *      the selector has been changed underneath it.
 *   6. Offer [Switch Model] that requires an explicit choice among the other
 *      three, and only then re-sends.
 *   7. Dismiss cleanly.
 */
import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const TARGET_URL = process.argv[2] || 'http://localhost:5173';
const FIXTURE_DOCX = path.resolve(__dirname, '..', 'anonymize client', 'Demo files', 'Demo files', 'Compare LF', 'Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx');

const MODELS = [
  { id: 'workbench_luna', name: 'Luna', provider: 'workbench' },
  { id: 'workbench_sol', name: 'Sol', provider: 'workbench' },
  { id: 'gemini_3_6_flash', name: 'Gemini 3.6 Flash', provider: 'gemini' },
  { id: 'gemini_3_5_flash', name: 'Gemini 3.5 Flash', provider: 'gemini' },
];
const byId = Object.fromEntries(MODELS.map((m) => [m.id, m]));

/** Mirrors the backend's normalized error vocabulary and copy. */
const ERROR_MODES = {
  unavailable: {
    status: 503,
    error_type: 'unavailable',
    message: (n) => `${n} is currently unavailable because the AI service could not be reached.`,
    headline: (n) => `${n} is temporarily unavailable`,
  },
  config_missing: {
    status: 503,
    error_type: 'config_missing',
    message: (n) => `${n} is not configured in this environment.`,
    headline: (n) => `${n} is not available in this environment`,
  },
  rate_limited: {
    status: 429,
    error_type: 'rate_limited',
    message: (n) => `${n} is temporarily unavailable because its current API quota/rate limit was reached.`,
    headline: (n) => `${n} has reached its quota`,
  },
  auth_error: {
    status: 502,
    error_type: 'auth_error',
    message: (n) => `${n} authentication failed. Please verify provider credentials.`,
    headline: (n) => `${n} could not authenticate`,
  },
};

async function run() {
  console.log('============================================================');
  console.log('AGENT PROVIDER ERROR UX SUITE (FOUR MODELS)');
  console.log(`Target: ${TARGET_URL}`);
  console.log('============================================================\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  let passedCount = 0;
  let failedCount = 0;
  const requestedModels = [];

  function assert(condition, desc) {
    if (condition) {
      console.log(`  [PASS] ${desc}`);
      passedCount++;
    } else {
      console.error(`  [FAIL] ${desc}`);
      failedCount++;
    }
  }

  // Which error every model should currently return. `null` means succeed.
  let failureMode = 'unavailable';
  let succeedForModels = new Set();

  try {
    await page.route('**/api/agent/chat', async (route) => {
      const postData = route.request().postDataJSON();
      const modelId = postData?.model_id || 'workbench_luna';
      const model = byId[modelId] ?? byId.workbench_luna;
      requestedModels.push(modelId);

      if (succeedForModels.has(modelId)) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'success',
            intent: 'general_query',
            response: `Response generated using ${model.name}.`,
            model_id: modelId,
            provider: model.provider,
            run_id: 'mock-run-' + Date.now(),
            steps: [],
            citations: [],
            proposed_actions: [],
          }),
        });
        return;
      }

      const mode = ERROR_MODES[failureMode];
      await route.fulfill({
        status: mode.status,
        contentType: 'application/json',
        body: JSON.stringify({
          error: mode.message(model.name),
          status: 'error',
          error_type: mode.error_type,
          model_id: modelId,
          provider: model.provider,
          run_id: null,
          steps: [],
          citations: [],
          proposed_actions: [],
        }),
      });
    });

    await page.goto(TARGET_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);

    const openWsBtn = page.locator('button:has-text("Open Workspace"), a:has-text("Open Workspace")');
    if (await openWsBtn.isVisible()) {
      await openWsBtn.click();
      await page.waitForTimeout(300);
    }

    console.log('>>> SETUP: Uploading DOCX fixture...');
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.locator('button[title="Add documents"], .btn:has-text("Add")').first().click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(FIXTURE_DOCX);
    await page.locator('.doc-badge.ready, span:has-text("Ready")').first().waitFor({ state: 'visible', timeout: 30000 });
    console.log('  [+] Fixture loaded & ready.\n');

    const modelTrigger = page.locator('[data-testid="agent-model-selector-trigger"]');
    const dropdown = page.locator('[data-testid="agent-model-selector-dropdown"]');
    const chatInput = page.locator('.agent-composer textarea');
    const sendBtn = page.locator('.agent-composer .send-btn');
    const errorCard = page.locator('[data-testid="agent-provider-error-card"]');
    const dismissBtn = page.locator('[data-testid="agent-error-dismiss-btn"]');

    async function selectModel(id) {
      await modelTrigger.click();
      await dropdown.waitFor({ state: 'visible', timeout: 3000 });
      await page.locator(`[data-testid="model-option-${id}"]`).click();
      await page.waitForTimeout(200);
    }

    // Dismiss only — never reload, because a reload would drop the uploaded
    // document and disable the composer for the rest of the suite.
    async function dismissError() {
      if (await errorCard.isVisible()) {
        await dismissBtn.click();
        await page.waitForTimeout(250);
      }
    }

    // ------------------------------------------------------------------------
    // TEST 1: Default is Luna
    // ------------------------------------------------------------------------
    console.log('>>> TEST 1: Default model...');
    await modelTrigger.waitFor({ state: 'visible', timeout: 5000 });
    const initialText = await modelTrigger.textContent();
    assert(initialText.includes('Luna'), `Initial model is Luna (saw: '${initialText.trim()}')`);

    // ------------------------------------------------------------------------
    // TEST 2: Each of the four models fails as itself
    // ------------------------------------------------------------------------
    console.log('\n>>> TEST 2: Explicit Failure Per Model...');
    for (const model of MODELS) {
      failureMode = 'unavailable';
      succeedForModels = new Set();

      await selectModel(model.id);
      const prompt = `Summarize the document with ${model.name}.`;
      await chatInput.fill(prompt);
      await sendBtn.click();

      await errorCard.waitFor({ state: 'visible', timeout: 10000 });
      const cardText = await errorCard.textContent();

      assert(cardText.includes(model.name), `[${model.name}] Error card names the failed model`);
      assert(
        cardText.includes(ERROR_MODES.unavailable.headline(model.name)),
        `[${model.name}] Headline reads "${ERROR_MODES.unavailable.headline(model.name)}"`
      );

      // The card must not name any other model — that would read as if another
      // model had stepped in.
      const otherNames = MODELS.filter((m) => m.id !== model.id).map((m) => m.name);
      const leaked = otherNames.filter((n) => cardText.includes(n));
      assert(leaked.length === 0, `[${model.name}] No other model named in the card (leaked: ${JSON.stringify(leaked)})`);

      const assistantCount = await page.locator('.agent-message.assistant').count();
      assert(assistantCount === 0, `[${model.name}] No assistant message created (saw ${assistantCount})`);

      const userText = await page.locator('.agent-message.user').last().textContent();
      assert(userText.includes(prompt), `[${model.name}] User prompt preserved in transcript`);

      const retryText = await page.locator('[data-testid="agent-error-retry-btn"]').textContent();
      assert(retryText.includes(model.name), `[${model.name}] Retry button targets the same model`);

      await dismissError();
    }

    // ------------------------------------------------------------------------
    // TEST 3: Quota exhausted wording (Gemini 3.6 Flash)
    // ------------------------------------------------------------------------
    console.log('\n>>> TEST 3: Gemini Quota Exhausted...');
    failureMode = 'rate_limited';
    await selectModel('gemini_3_6_flash');
    await chatInput.fill('Summarize under quota exhaustion.');
    await sendBtn.click();
    await errorCard.waitFor({ state: 'visible', timeout: 10000 });

    const quotaText = await errorCard.textContent();
    assert(
      quotaText.includes('quota/rate limit was reached'),
      `Quota message explains the API quota/rate limit`
    );
    assert(quotaText.includes('Gemini 3.6 Flash'), `Quota card names Gemini 3.6 Flash`);
    assert(!quotaText.includes('Gemini 3.5 Flash'), `Quota card does NOT name Gemini 3.5 Flash as a substitute`);
    assert(
      !/api[_ ]?key|Bearer|https?:\/\/|Traceback|x-goog/i.test(quotaText),
      `No credentials, endpoints or stack traces in the card`
    );
    await dismissError();

    // ------------------------------------------------------------------------
    // TEST 4: Auth failure and config-missing wording
    // ------------------------------------------------------------------------
    console.log('\n>>> TEST 4: Auth Failure & Not Configured...');
    for (const [mode, modelId] of [['auth_error', 'gemini_3_5_flash'], ['config_missing', 'workbench_sol']]) {
      failureMode = mode;
      await selectModel(modelId);
      await chatInput.fill(`Trigger ${mode}.`);
      await sendBtn.click();
      await errorCard.waitFor({ state: 'visible', timeout: 10000 });

      const text = await errorCard.textContent();
      const name = byId[modelId].name;
      assert(text.includes(ERROR_MODES[mode].headline(name)), `[${mode}] Headline for ${name}`);
      assert(
        !/api[_ ]?key\s*[:=]|Traceback|https?:\/\//i.test(text),
        `[${mode}] No secrets or endpoints surfaced`
      );
      await dismissError();
    }

    // ------------------------------------------------------------------------
    // TEST 5: Retry uses the SAME model even after the selector changed
    // ------------------------------------------------------------------------
    console.log('\n>>> TEST 5: Retry Targets the Failed Model...');
    failureMode = 'unavailable';
    succeedForModels = new Set();

    await selectModel('gemini_3_6_flash');
    await chatInput.fill('Retry semantics check.');
    await sendBtn.click();
    await errorCard.waitFor({ state: 'visible', timeout: 10000 });

    // Change the selector to a different model *before* retrying.
    await selectModel('workbench_luna');
    const triggerBeforeRetry = await modelTrigger.textContent();
    assert(triggerBeforeRetry.includes('Luna'), `Selector changed to Luna after the failure`);

    const retryBtnText = await page.locator('[data-testid="agent-error-retry-btn"]').textContent();
    assert(
      retryBtnText.includes('Gemini 3.6 Flash'),
      `Retry button still targets Gemini 3.6 Flash (saw: '${retryBtnText.trim()}')`
    );

    const countBeforeRetry = requestedModels.length;
    await page.locator('[data-testid="agent-error-retry-btn"]').click();
    await page.waitForTimeout(1200);

    const retriedModel = requestedModels[countBeforeRetry];
    assert(
      retriedModel === 'gemini_3_6_flash',
      `Retry re-sent to gemini_3_6_flash despite the selector showing Luna (saw: '${retriedModel}')`
    );

    // ------------------------------------------------------------------------
    // TEST 6: Switch Model requires an explicit choice among the other three
    // ------------------------------------------------------------------------
    console.log('\n>>> TEST 6: Switch Model Requires an Explicit Choice...');
    await errorCard.waitFor({ state: 'visible', timeout: 10000 });

    const switchBtn = page.locator('[data-testid="agent-error-switch-btn"]');
    const switchBtnText = await switchBtn.textContent();
    assert(
      switchBtnText.includes('Switch Model'),
      `Switch button is a neutral "Switch Model" (saw: '${switchBtnText.trim()}')`
    );

    const switchList = page.locator('[data-testid="agent-error-switch-list"]');
    assert(!(await switchList.isVisible()), `No model is offered until the user asks to switch`);

    const countBeforeSwitchOpen = requestedModels.length;
    await switchBtn.click();
    await switchList.waitFor({ state: 'visible', timeout: 3000 });

    assert(
      requestedModels.length === countBeforeSwitchOpen,
      `Opening the switch list sends no request on its own`
    );

    const choiceCount = await switchList.locator('button').count();
    assert(choiceCount === 3, `Exactly the other three models are offered (saw ${choiceCount})`);

    const failedStillOffered = await page
      .locator('[data-testid="agent-error-switch-to-gemini_3_6_flash"]').count();
    assert(failedStillOffered === 0, `The failed model is not offered as a "switch" target`);

    // Explicitly choose Sol; only now may a request go out, and only to Sol.
    succeedForModels = new Set(['workbench_sol']);
    const countBeforeChoice = requestedModels.length;
    await page.locator('[data-testid="agent-error-switch-to-workbench_sol"]').click();
    await page.waitForTimeout(1500);

    const switchedTo = requestedModels.slice(countBeforeChoice);
    assert(
      switchedTo.length === 1 && switchedTo[0] === 'workbench_sol',
      `Exactly one request, to the explicitly chosen model (saw: ${JSON.stringify(switchedTo)})`
    );

    const triggerAfterSwitch = await modelTrigger.textContent();
    assert(triggerAfterSwitch.includes('Sol'), `Selector reflects the explicit choice`);

    const finalTag = await page.locator('.agent-message.assistant').last()
      .locator('[data-testid="agent-message-model-tag"]').textContent();
    assert(finalTag.trim() === 'Sol', `Successful response is attributed to Sol`);
    assert(!(await errorCard.isVisible()), `Error card cleared after the successful explicit switch`);

    // The only assistant message in the whole suite so far is this one — every
    // other turn failed and produced no bubble.
    const assistantAfterExplicitSwitch = await page.locator('.agent-message.assistant').count();
    assert(
      assistantAfterExplicitSwitch === 1,
      `Exactly one assistant message exists across the suite: the successful Sol turn ` +
      `(saw ${assistantAfterExplicitSwitch})`
    );

    // ------------------------------------------------------------------------
    // TEST 7: Dismiss
    // ------------------------------------------------------------------------
    console.log('\n>>> TEST 7: Dismiss...');
    succeedForModels = new Set();
    failureMode = 'unavailable';
    await selectModel('gemini_3_5_flash');
    await chatInput.fill('Dismiss check.');
    await sendBtn.click();
    await errorCard.waitFor({ state: 'visible', timeout: 10000 });

    await dismissBtn.click();
    await page.waitForTimeout(400);
    assert(!(await errorCard.isVisible()), `Error card dismissed cleanly`);

    const assistantAfterDismiss = await page.locator('.agent-message.assistant').count();
    assert(
      assistantAfterDismiss === assistantAfterExplicitSwitch,
      `Dismissing never leaves a fabricated assistant message ` +
      `(expected ${assistantAfterExplicitSwitch}, saw ${assistantAfterDismiss})`
    );

  } catch (err) {
    console.error('\n[FATAL SUITE ERROR]:', err);
    failedCount++;
  } finally {
    await browser.close();
  }

  console.log('\n============================================================');
  console.log(`SUMMARY: ${passedCount} PASSED, ${failedCount} FAILED`);
  console.log('============================================================\n');

  if (failedCount > 0) {
    process.exit(1);
  }
}

run();
