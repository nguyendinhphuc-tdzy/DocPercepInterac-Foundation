/**
 * test_agent_model_selection.mjs
 *
 * E2E Playwright acceptance suite for the four-model Agent selector
 * (Luna / Sol / Gemini 3.6 Flash / Gemini 3.5 Flash):
 *
 *  - Test 1: Default model is Luna on a new conversation
 *  - Test 2: Selector exposes exactly four options, grouped by provider
 *  - Test 3: Each of the four models can be selected and tags its own response
 *  - Test 4: Switching among all four preserves conversation + per-message tags
 *  - Test 5: Context invariance (document, selected element) across switches
 *  - Test 6: Governed write proposal & confirmation invariance under Gemini
 *  - Test 7: Split view / zoom orthogonality during model switching
 *  - Test 8: Keyboard accessibility & ARIA semantics (incl. provider groups)
 *  - Test 9: Responsive layout across viewports
 *  - Test 10: Changing the selector mid-flight does not retarget the running request
 */
import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const TARGET_URL = process.argv[2] || 'http://localhost:5173';
const FIXTURE_DOCX = path.resolve(__dirname, '..', 'anonymize client', 'Demo files', 'Demo files', 'Compare LF', 'Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx');
const FIXTURE_XLSX = path.resolve(__dirname, '..', 'anonymize client', 'Demo files', 'Demo files', 'FA&RPTS & Appendix I', 'FA&RPTs', 'HMV-FA&RPT FY2024.xlsx');

/** Mirrors the backend registry — the same four application-level ids. */
const MODELS = [
  { id: 'workbench_luna', name: 'Luna', provider: 'workbench', group: 'Workbench' },
  { id: 'workbench_sol', name: 'Sol', provider: 'workbench', group: 'Workbench' },
  { id: 'gemini_3_6_flash', name: 'Gemini 3.6 Flash', provider: 'gemini', group: 'Gemini' },
  { id: 'gemini_3_5_flash', name: 'Gemini 3.5 Flash', provider: 'gemini', group: 'Gemini' },
];

const byId = Object.fromEntries(MODELS.map((m) => [m.id, m]));

async function runModelSelectionSuite() {
  console.log(`============================================================`);
  console.log(`AGENT FOUR-MODEL SELECTION ACCEPTANCE SUITE`);
  console.log(`Target: ${TARGET_URL}`);
  console.log(`============================================================\n`);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  let failedCount = 0;
  let passedCount = 0;
  /** Every model id the mocked backend was actually asked for, in order. */
  const requestedModels = [];
  let responseDelayMs = 0;

  function assert(condition, desc) {
    if (condition) {
      console.log(`  [PASS] ${desc}`);
      passedCount++;
    } else {
      console.error(`  [FAIL] ${desc}`);
      failedCount++;
    }
  }

  try {
    await page.route('**/api/agent/chat', async (route) => {
      const postData = route.request().postDataJSON();
      const modelId = postData?.model_id || 'workbench_luna';
      const model = byId[modelId] ?? byId.workbench_luna;
      const msg = postData?.message || '';
      requestedModels.push(modelId);

      const isEditProposal = msg.toLowerCase().includes('change')
        || msg.toLowerCase().includes('edit')
        || msg.toLowerCase().includes('propos');

      const responsePayload = {
        status: 'success',
        intent: isEditProposal ? 'propose_edit' : 'general_query',
        response: `Response generated using ${model.name}.`,
        model_id: modelId,
        provider: model.provider,
        run_id: 'mock-run-' + Date.now(),
        steps: [{ label: `Processed by ${model.name}`, status: 'done' }],
        citations: [],
        proposed_actions: isEditProposal
          ? [
              {
                action_id: 'act-' + Date.now(),
                doc_id: postData?.context?.active_doc_id || 'mock-doc',
                doc_name: 'test.xlsx',
                element_id: postData?.context?.selected_element_id || 'mock-el',
                element_name: 'Cell',
                current_value: 'ORIGINAL_VALUE',
                proposed_value: 'AGENT_PROPOSAL_2026',
                rationale: 'Reasoning update',
                requires_confirmation: true,
                status: 'proposed',
              },
            ]
          : [],
      };

      if (responseDelayMs > 0) {
        await new Promise((resolve) => setTimeout(resolve, responseDelayMs));
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(responsePayload),
      });
    });

    await page.goto(TARGET_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    const openWsBtn = page.locator('button:has-text("Open Workspace"), a:has-text("Open Workspace")');
    if (await openWsBtn.isVisible()) {
      await openWsBtn.click();
      await page.waitForTimeout(300);
    }

    // ------------------------------------------------------------------------
    // SETUP: Upload DOCX and XLSX fixtures
    // ------------------------------------------------------------------------
    console.log(`>>> UPLOADING FIXTURES...`);
    const fileChooserPromise1 = page.waitForEvent('filechooser');
    await page.locator('button[title="Add documents"], .btn:has-text("Add")').first().click();
    const fileChooser1 = await fileChooserPromise1;
    await fileChooser1.setFiles(FIXTURE_DOCX);
    await page.locator('.doc-badge.ready, span:has-text("Ready")').first().waitFor({ state: 'visible', timeout: 30000 });

    const fileChooserPromise2 = page.waitForEvent('filechooser');
    await page.locator('button[title="Add documents"], .btn:has-text("Add")').first().click();
    const fileChooser2 = await fileChooserPromise2;
    await fileChooser2.setFiles(FIXTURE_XLSX);
    await page.locator('.doc-badge.ready, span:has-text("Ready")').nth(1).waitFor({ state: 'visible', timeout: 30000 });
    console.log(`  [+] Both fixtures loaded & perceived.\n`);

    const modelTrigger = page.locator('[data-testid="agent-model-selector-trigger"]');
    const dropdown = page.locator('[data-testid="agent-model-selector-dropdown"]');
    const chatInput = page.locator('.agent-composer textarea');
    const sendBtn = page.locator('.agent-composer .send-btn');

    async function selectModel(id) {
      await modelTrigger.click();
      await dropdown.waitFor({ state: 'visible', timeout: 3000 });
      await page.locator(`[data-testid="model-option-${id}"]`).click();
      await page.waitForTimeout(200);
    }

    async function ask(text, expectedIndex) {
      await chatInput.fill(text);
      await sendBtn.click();
      await page.locator('.agent-message.assistant').nth(expectedIndex)
        .waitFor({ state: 'visible', timeout: 15000 });
    }

    // ------------------------------------------------------------------------
    // TEST 1: Default model is Luna
    // ------------------------------------------------------------------------
    console.log(`>>> TEST 1: Default Model Verification (Luna)...`);
    await modelTrigger.waitFor({ state: 'visible', timeout: 5000 });
    const initialModelText = await modelTrigger.textContent();
    assert(initialModelText.includes('Luna'), `Initial selector shows 'Luna' (saw: '${initialModelText.trim()}')`);

    await ask('Summarize this document structure.', 0);
    const firstAssistantMsg = page.locator('.agent-message.assistant').first();
    const firstModelTag = await firstAssistantMsg.locator('[data-testid="agent-message-model-tag"]').textContent();
    assert(firstModelTag.includes('Luna'), `First response tagged 'Luna' (saw: '${firstModelTag.trim()}')`);
    assert(requestedModels[0] === 'workbench_luna', `Backend received model_id 'workbench_luna' (saw: '${requestedModels[0]}')`);

    // ------------------------------------------------------------------------
    // TEST 2: Exactly four options, grouped by provider
    // ------------------------------------------------------------------------
    console.log(`\n>>> TEST 2: Four Options, Provider Grouping...`);
    await modelTrigger.click();
    await dropdown.waitFor({ state: 'visible', timeout: 3000 });

    const optionCount = await dropdown.locator('[role="option"]').count();
    assert(optionCount === 4, `Selector exposes exactly 4 options (saw: ${optionCount})`);

    for (const model of MODELS) {
      const visible = await page.locator(`[data-testid="model-option-${model.id}"]`).isVisible();
      assert(visible, `Option present: ${model.name}`);
    }

    const groupLabels = await dropdown.locator('[role="group"]').evaluateAll(
      (nodes) => nodes.map((n) => n.getAttribute('aria-label'))
    );
    assert(
      groupLabels.length === 2 && groupLabels[0] === 'Workbench' && groupLabels[1] === 'Gemini',
      `Provider groups are Workbench then Gemini (saw: ${JSON.stringify(groupLabels)})`
    );

    const orderedIds = await dropdown.locator('[role="option"]').evaluateAll(
      (nodes) => nodes.map((n) => n.getAttribute('data-testid'))
    );
    assert(
      JSON.stringify(orderedIds) === JSON.stringify(MODELS.map((m) => `model-option-${m.id}`)),
      `Order is Luna, Sol, Gemini 3.6, Gemini 3.5 (saw: ${JSON.stringify(orderedIds)})`
    );

    await page.keyboard.press('Escape');
    await page.waitForTimeout(150);

    // ------------------------------------------------------------------------
    // TEST 3 + 4: Select each model in turn; tags and history are preserved
    // ------------------------------------------------------------------------
    console.log(`\n>>> TEST 3/4: Selecting and Switching Among All Four Models...`);
    const switchSequence = ['workbench_sol', 'gemini_3_6_flash', 'gemini_3_5_flash', 'workbench_luna'];
    let assistantIndex = 0;

    for (const modelId of switchSequence) {
      const model = byId[modelId];
      await selectModel(modelId);

      const triggerText = await modelTrigger.textContent();
      assert(triggerText.includes(model.name), `Selector shows '${model.name}' (saw: '${triggerText.trim()}')`);

      assistantIndex += 1;
      await ask(`Question routed to ${model.name}.`, assistantIndex);

      const tag = await page.locator('.agent-message.assistant').nth(assistantIndex)
        .locator('[data-testid="agent-message-model-tag"]').textContent();
      assert(tag.trim() === model.name, `Response ${assistantIndex} tagged '${model.name}' (saw: '${tag.trim()}')`);

      const sentId = requestedModels[requestedModels.length - 1];
      assert(sentId === modelId, `Backend received model_id '${modelId}' (saw: '${sentId}')`);
    }

    // Historical messages keep the model that actually answered them.
    const firstTagAfterSwitches = await firstAssistantMsg
      .locator('[data-testid="agent-message-model-tag"]').textContent();
    assert(firstTagAfterSwitches.includes('Luna'), `Historical first message retained its 'Luna' tag`);

    const solTag = await page.locator('.agent-message.assistant').nth(1)
      .locator('[data-testid="agent-message-model-tag"]').textContent();
    assert(solTag.trim() === 'Sol', `Historical Sol message retained its tag after 3 further switches`);

    const totalAssistant = await page.locator('.agent-message.assistant').count();
    assert(totalAssistant === 5, `Conversation preserved across all switches (5 responses, saw ${totalAssistant})`);

    // ------------------------------------------------------------------------
    // TEST 5: Context invariance across model switches
    // ------------------------------------------------------------------------
    console.log(`\n>>> TEST 5: Context Invariance (Document + Selection)...`);
    const docCountBefore = await page.locator('.doc-badge.ready, span:has-text("Ready")').count();

    const targetElement = page.locator('.docx-preview-wrapper p, p, td, [data-el-id]').first();
    if (await targetElement.isVisible()) {
      await targetElement.click();
      await page.waitForTimeout(300);
    }
    const selectionBefore = await page.locator('.agent-composer-context').textContent();

    await selectModel('gemini_3_6_flash');
    await selectModel('workbench_sol');
    await selectModel('gemini_3_5_flash');

    const docCountAfter = await page.locator('.doc-badge.ready, span:has-text("Ready")').count();
    const selectionAfter = await page.locator('.agent-composer-context').textContent();

    assert(docCountBefore === docCountAfter, `Loaded documents unchanged by model switching`);
    assert(
      selectionBefore.replace(/Model.*$/, '') === selectionAfter.replace(/Model.*$/, ''),
      `Selected element context unchanged by model switching`
    );

    // ------------------------------------------------------------------------
    // TEST 6: Governed write proposal under a Gemini model
    // ------------------------------------------------------------------------
    console.log(`\n>>> TEST 6: Governed Write Invariance under Gemini...`);
    await selectModel('gemini_3_6_flash');
    await chatInput.fill('Change this cell to "AGENT_PROPOSAL_2026"');
    await sendBtn.click();

    const proposalCard = page.locator('text=Governed Action Proposal').last();
    await proposalCard.waitFor({ state: 'visible', timeout: 15000 });
    assert(await proposalCard.isVisible(), `Governed proposal card rendered for a Gemini request`);

    const confirmBtn = page.locator('button:has-text("Confirm & Apply"), button:has-text("Confirm")').last();
    assert(await confirmBtn.isVisible(), `Confirmation still required (no governance bypass for Gemini)`);

    // ------------------------------------------------------------------------
    // TEST 7: Split view & zoom orthogonality
    // ------------------------------------------------------------------------
    console.log(`
>>> TEST 7: Split View & Zoom Orthogonality...`);

    // Zoom first, while the zoom controls are visible (they are hidden in split view).
    const zoomInBtn = page.locator('button[aria-label="Zoom in"]').first();
    const zoomLabel = page.locator('button[title="Reset zoom to 100%"]').first();
    await zoomInBtn.click();
    await zoomInBtn.click();
    await page.waitForTimeout(200);
    const zoomBefore = (await zoomLabel.textContent()).trim();
    assert(zoomBefore !== '100%', `Zoom changed away from the default (saw: '${zoomBefore}')`);

    await selectModel('gemini_3_5_flash');
    await selectModel('workbench_sol');

    const zoomAfter = (await zoomLabel.textContent()).trim();
    assert(zoomBefore === zoomAfter, `Zoom preserved across model switches (${zoomBefore} -> ${zoomAfter})`);

    // Now split view. Split mode nests a per-pane switcher inside each pane, so
    // scope the outer control explicitly.
    const outerSwitch = page.locator('.view-mode-switch').first();
    await outerSwitch.locator('.view-mode-btn:has-text("Split")').click();
    await page.waitForTimeout(600);

    const activeBefore = (await outerSwitch.locator('.view-mode-btn.active').textContent()).trim();
    const paneSwitchersBefore = await page.locator('.view-mode-switch').count();
    assert(activeBefore.includes('Split'), `Split view active before switching (saw: '${activeBefore}')`);
    assert(paneSwitchersBefore > 1, `Split view rendered its panes (saw ${paneSwitchersBefore} switchers)`);

    await selectModel('gemini_3_6_flash');
    await selectModel('workbench_luna');

    const activeAfter = (await outerSwitch.locator('.view-mode-btn.active').textContent()).trim();
    const paneSwitchersAfter = await page.locator('.view-mode-switch').count();
    assert(activeAfter === activeBefore, `Split view mode unaffected by model switching`);
    assert(
      paneSwitchersBefore === paneSwitchersAfter,
      `Split pane configuration unaffected by model switching (${paneSwitchersBefore} -> ${paneSwitchersAfter})`
    );

    // Return to the original view for the remaining tests.
    await outerSwitch.locator('.view-mode-btn:has-text("Original")').click();
    await page.waitForTimeout(400);

    // ------------------------------------------------------------------------
    // TEST 8: Keyboard accessibility & ARIA semantics
    // ------------------------------------------------------------------------
    console.log(`\n>>> TEST 8: Keyboard Accessibility & ARIA Semantics...`);
    await modelTrigger.focus();
    await page.keyboard.press('Enter');
    await page.waitForTimeout(150);
    assert(await dropdown.isVisible(), `Dropdown opened via Enter key`);
    assert(
      (await modelTrigger.getAttribute('aria-expanded')) === 'true',
      `Trigger reports aria-expanded="true" while open`
    );

    const selectedStates = await dropdown.locator('[role="option"]').evaluateAll(
      (nodes) => nodes.map((n) => n.getAttribute('aria-selected'))
    );
    assert(
      selectedStates.filter((s) => s === 'true').length === 1,
      `Exactly one option reports aria-selected="true" (saw: ${JSON.stringify(selectedStates)})`
    );

    // Keyboard-select a Gemini option without using the mouse.
    const geminiOption = page.locator('[data-testid="model-option-gemini_3_6_flash"]');
    await geminiOption.focus();
    await page.keyboard.press('Enter');
    await page.waitForTimeout(200);
    const keyboardTrigger = await modelTrigger.textContent();
    assert(keyboardTrigger.includes('Gemini 3.6 Flash'), `Gemini 3.6 Flash selectable by keyboard`);

    await modelTrigger.focus();
    await page.keyboard.press('Enter');
    await page.waitForTimeout(150);
    await page.keyboard.press('Escape');
    await page.waitForTimeout(150);
    assert(!(await dropdown.isVisible()), `Dropdown closed via Escape key`);
    assert(
      (await modelTrigger.getAttribute('aria-expanded')) === 'false',
      `Trigger reports aria-expanded="false" while closed`
    );

    await selectModel('workbench_luna');

    // ------------------------------------------------------------------------
    // TEST 9: Responsive layout
    // ------------------------------------------------------------------------
    console.log(`\n>>> TEST 9: Responsive Layout Checks...`);
    const viewports = [
      { width: 1440, height: 900 },
      { width: 1280, height: 800 },
      { width: 1024, height: 768 },
      { width: 900, height: 700 },
      { width: 768, height: 1024 },
    ];

    for (const vp of viewports) {
      await page.setViewportSize(vp);
      await page.waitForTimeout(200);

      // Longest label is the worst case for the composer row.
      await selectModel('gemini_3_6_flash');

      const triggerBox = await modelTrigger.boundingBox();
      const sendBox = await sendBtn.boundingBox();
      const bodyScrollsX = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1
      );

      const sendOnScreen = sendBox && sendBox.x >= 0 && sendBox.x + sendBox.width <= vp.width + 1;
      const triggerOnScreen = triggerBox && triggerBox.x >= 0 && triggerBox.x + triggerBox.width <= vp.width + 1;

      assert(
        triggerOnScreen && sendOnScreen && !bodyScrollsX,
        `Composer, Send and selector all fit at ${vp.width}x${vp.height} with the longest model name`
      );

      // Dropdown must stay inside the viewport too.
      await modelTrigger.click();
      await dropdown.waitFor({ state: 'visible', timeout: 3000 });
      const ddBox = await dropdown.boundingBox();
      assert(
        ddBox && ddBox.x >= 0 && ddBox.x + ddBox.width <= vp.width + 1,
        `Dropdown fits within ${vp.width}px viewport`
      );
      await page.keyboard.press('Escape');
      await page.waitForTimeout(100);
    }

    await page.setViewportSize({ width: 1440, height: 900 });
    await selectModel('workbench_luna');

    // ------------------------------------------------------------------------
    // TEST 10: Changing the selector mid-flight does not retarget the request
    // ------------------------------------------------------------------------
    console.log(`\n>>> TEST 10: In-Flight Request Is Not Retargeted...`);
    const beforeInFlight = requestedModels.length;
    responseDelayMs = 1500;

    await selectModel('workbench_sol');
    await chatInput.fill('Long running question for Sol.');
    await sendBtn.click();
    await page.waitForTimeout(300);

    // Switch while the Sol request is still in flight.
    await selectModel('gemini_3_6_flash');

    await page.waitForTimeout(2500);
    responseDelayMs = 0;

    const inFlightModel = requestedModels[beforeInFlight];
    assert(inFlightModel === 'workbench_sol', `In-flight request stayed on 'workbench_sol' (saw: '${inFlightModel}')`);
    assert(
      requestedModels.length === beforeInFlight + 1,
      `Switching mid-flight did not fire an extra request (saw ${requestedModels.length - beforeInFlight})`
    );

    const lastTag = await page.locator('.agent-message.assistant').last()
      .locator('[data-testid="agent-message-model-tag"]').textContent();
    assert(lastTag.trim() === 'Sol', `Completed response is attributed to Sol, not the newly selected model`);

    const triggerAfterInFlight = await modelTrigger.textContent();
    assert(
      triggerAfterInFlight.includes('Gemini 3.6 Flash'),
      `Selector still shows the new choice for the NEXT request`
    );

  } catch (err) {
    console.error(`\n[FATAL SUITE ERROR]:`, err);
    failedCount++;
  } finally {
    await browser.close();
  }

  console.log(`\n============================================================`);
  console.log(`SUMMARY: ${passedCount} PASSED, ${failedCount} FAILED`);
  console.log(`============================================================\n`);

  if (failedCount > 0) {
    process.exit(1);
  }
}

runModelSelectionSuite();
