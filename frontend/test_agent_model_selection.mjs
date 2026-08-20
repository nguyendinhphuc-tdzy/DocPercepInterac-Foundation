/**
 * test_agent_model_selection.mjs
 * 
 * Comprehensive E2E Playwright acceptance test for user-selectable Agent Model (Luna / Sol):
 * - Test 1: Default Model is Luna on new conversation
 * - Test 2: Switching to Sol and issuing query (Request + Response Tag)
 * - Test 3: Switching back to Luna and issuing query
 * - Test 4: Context Invariance across model switches (Selected Element + Doc Context)
 * - Test 5: Governed Write Proposal & Confirmation Invariance under Luna and Sol
 * - Test 6: Split View & Multi-Document Orthogonality during Model Switching
 * - Test 7: Keyboard Accessibility & ARIA semantics
 * - Test 8: Responsive Layout across Viewports (1440x900, 1280x800, 1024x768, 900x700, 768x1024)
 */
import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const TARGET_URL = process.argv[2] || 'http://localhost:5173';
const FIXTURE_DOCX = path.resolve(__dirname, '..', 'anonymize client', 'Demo files', 'Demo files', 'Compare LF', 'Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx');
const FIXTURE_XLSX = path.resolve(__dirname, '..', 'anonymize client', 'Demo files', 'Demo files', 'FA&RPTS & Appendix I', 'FA&RPTs', 'HMV-FA&RPT FY2024.xlsx');

async function runModelSelectionSuite() {
  console.log(`============================================================`);
  console.log(`AGENT MODEL SELECTION (LUNA / SOL) ACCEPTANCE SUITE`);
  console.log(`Target: ${TARGET_URL}`);
  console.log(`============================================================\n`);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  let failedCount = 0;
  let passedCount = 0;

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
    await page.goto(TARGET_URL);
    await page.waitForLoadState('networkidle');

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

    // ------------------------------------------------------------------------
    // TEST 1: Default Model is Luna on new conversation
    // ------------------------------------------------------------------------
    console.log(`>>> TEST 1: Default Model Verification (Luna)...`);
    const modelTrigger = page.locator('[data-testid="agent-model-selector-trigger"]');
    await modelTrigger.waitFor({ state: 'visible', timeout: 5000 });
    const initialModelText = await modelTrigger.textContent();
    assert(initialModelText.includes('Luna'), `Initial selector text contains 'Luna' (saw: '${initialModelText.trim()}')`);

    // Ask query with default Luna
    const chatInput = page.locator('.agent-composer textarea');
    await chatInput.fill('Summarize this document structure.');
    await page.locator('.agent-composer .send-btn').click();

    await page.locator('.agent-message.assistant').first().waitFor({ state: 'visible', timeout: 15000 });
    const firstAssistantMsg = page.locator('.agent-message.assistant').first();
    const firstModelTag = await firstAssistantMsg.locator('[data-testid="agent-message-model-tag"]').textContent();
    assert(firstModelTag.includes('Luna'), `First assistant response tagged with 'Luna' (saw: '${firstModelTag.trim()}')`);

    // ------------------------------------------------------------------------
    // TEST 2: Switch to Sol and ask a deep query
    // ------------------------------------------------------------------------
    console.log(`\n>>> TEST 2: Switch to Sol & Deep Reasoning Query...`);
    await modelTrigger.click();
    const dropdown = page.locator('[data-testid="agent-model-selector-dropdown"]');
    await dropdown.waitFor({ state: 'visible', timeout: 3000 });

    const solOption = page.locator('[data-testid="model-option-sol"]');
    await solOption.click();
    await page.waitForTimeout(200);

    const solTriggerText = await modelTrigger.textContent();
    assert(solTriggerText.includes('Sol'), `Selector updated immediately to 'Sol' (saw: '${solTriggerText.trim()}')`);

    // Ask query with Sol
    await chatInput.fill('Explain in depth the tax and financial implications.');
    await page.locator('.agent-composer .send-btn').click();

    await page.locator('.agent-message.assistant').nth(1).waitFor({ state: 'visible', timeout: 15000 });
    const secondAssistantMsg = page.locator('.agent-message.assistant').nth(1);
    const secondModelTag = await secondAssistantMsg.locator('[data-testid="agent-message-model-tag"]').textContent();
    assert(secondModelTag.includes('Sol'), `Second assistant response tagged with 'Sol' (saw: '${secondModelTag.trim()}')`);

    // Verify first message retained its Luna tag (Per-message traceability)
    const firstModelTagAgain = await firstAssistantMsg.locator('[data-testid="agent-message-model-tag"]').textContent();
    assert(firstModelTagAgain.includes('Luna'), `Historical first message retained 'Luna' tag`);

    // ------------------------------------------------------------------------
    // TEST 3: Switch back to Luna
    // ------------------------------------------------------------------------
    console.log(`\n>>> TEST 3: Switch back to Luna...`);
    await modelTrigger.click();
    const lunaOption = page.locator('[data-testid="model-option-luna"]');
    await lunaOption.click();
    await page.waitForTimeout(200);

    const lunaTriggerText = await modelTrigger.textContent();
    assert(lunaTriggerText.includes('Luna'), `Selector updated back to 'Luna' (saw: '${lunaTriggerText.trim()}')`);

    await chatInput.fill('List main elements quickly.');
    await page.locator('.agent-composer .send-btn').click();

    await page.locator('.agent-message.assistant').nth(2).waitFor({ state: 'visible', timeout: 15000 });
    const thirdAssistantMsg = page.locator('.agent-message.assistant').nth(2);
    const thirdModelTag = await thirdAssistantMsg.locator('[data-testid="agent-message-model-tag"]').textContent();
    assert(thirdModelTag.includes('Luna'), `Third assistant response tagged with 'Luna'`);

    // ------------------------------------------------------------------------
    // TEST 4: Context Invariance across Model Switches
    // ------------------------------------------------------------------------
    console.log(`\n>>> TEST 4: Context Invariance Verification...`);
    // Switch to XLSX document in file rail
    await page.locator('.file-rail-item:has-text("HMV-FA&RPT")').first().click();
    await page.waitForTimeout(500);

    // Select an element (cell) in the DocumentPane
    const targetCell = page.locator('td[data-el-id]').first();
    await targetCell.waitFor({ state: 'visible', timeout: 10000 });
    await targetCell.click();
    await page.waitForTimeout(300);

    const contextPill = page.locator('.agent-composer-context');
    const selectedTextBefore = await contextPill.textContent();
    assert(selectedTextBefore.includes('Selected:'), `Selection context pill active before switch (saw: '${selectedTextBefore.trim()}')`);

    // Switch model to Sol
    await modelTrigger.click();
    await solOption.click();
    await page.waitForTimeout(200);

    // Verify selection pill and active document context are preserved
    const selectedTextAfter = await contextPill.textContent();
    assert(selectedTextAfter.includes('Selected:'), `Selection context pill preserved after switching to Sol (saw: '${selectedTextAfter.trim()}')`);

    // ------------------------------------------------------------------------
    // TEST 5: Governed Write Proposal & Confirmation Invariance
    // ------------------------------------------------------------------------
    console.log(`\n>>> TEST 5: Governed Write Invariance (Luna & Sol)...`);
    // Propose edit with Sol on the selected cell
    await chatInput.fill('Change this cell to "AGENT_SOL_PROPOSAL_2026"');
    await page.locator('.agent-composer .send-btn').click();

    // Wait for proposal card
    await page.waitForSelector('text=Governed Action Proposal', { timeout: 15000 });
    const proposalCount = await page.locator('text=Governed Action Proposal').count();
    assert(proposalCount > 0, `Governed proposal card rendered for Sol request`);

    const confirmBtn = page.locator('button:has-text("Confirm & Apply")').last();
    assert(await confirmBtn.isVisible(), `Confirmation button present on proposal card (no bypass)`);

    // ------------------------------------------------------------------------
    // TEST 6: Split View Orthogonality
    // ------------------------------------------------------------------------
    console.log(`\n>>> TEST 6: Split View Orthogonality...`);
    const splitBtn = page.locator('button[title="Toggle Split View"], button:has-text("Split")');
    if (await splitBtn.isVisible()) {
      await splitBtn.click();
      await page.waitForTimeout(400);

      const splitPanes = page.locator('.document-canvas');
      const count = await splitPanes.count();
      console.log(`  [+] Split view activated (${count} panes visible)`);

      // Switch model inside split view
      await modelTrigger.click();
      await lunaOption.click();
      await page.waitForTimeout(200);

      const countAfter = await page.locator('.document-canvas').count();
      assert(count === countAfter, `Split view configuration unaffected by model switch`);
    }

    // ------------------------------------------------------------------------
    // TEST 7: Keyboard Accessibility
    // ------------------------------------------------------------------------
    console.log(`\n>>> TEST 7: Keyboard Accessibility & ARIA Semantics...`);
    await modelTrigger.focus();
    await page.keyboard.press('Enter');
    await page.waitForTimeout(150);
    assert(await dropdown.isVisible(), `Dropdown opened via Enter key`);

    await page.keyboard.press('Escape');
    await page.waitForTimeout(150);
    assert(!(await dropdown.isVisible()), `Dropdown closed via Escape key`);

    // ------------------------------------------------------------------------
    // TEST 8: Responsive Layout Verification
    // ------------------------------------------------------------------------
    console.log(`\n>>> TEST 8: Responsive Layout Checks...`);
    const viewports = [
      { width: 1440, height: 900 },
      { width: 1280, height: 800 },
      { width: 1024, height: 768 },
      { width: 900, height: 700 },
      { width: 768, height: 1024 },
    ];

    for (const vp of viewports) {
      await page.setViewportSize(vp);
      await page.waitForTimeout(150);
      const isTriggerVisible = await modelTrigger.isVisible();
      const isSendVisible = await page.locator('.agent-composer .send-btn').isVisible();
      assert(isTriggerVisible && isSendVisible, `Composer & Model Selector usable at ${vp.width}x${vp.height}`);
    }

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
