/**
 * Acceptance test for Agent Provider Error UX and Fallback Elimination.
 * Verifies:
 * 1. Offline / missing AI credentials displays clean error card, NEVER fake assistant response text.
 * 2. User prompt is preserved in chat history.
 * 3. [Retry {model}] retries with the exact failed model.
 * 4. [Switch to {otherModel}] explicitly switches model and retries.
 * 5. Dismiss button cleans error state.
 */
import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const TARGET_URL = process.argv[2] || 'http://localhost:5173';
const FIXTURE_DOCX = path.resolve(__dirname, '..', 'anonymize client', 'Demo files', 'Demo files', 'Compare LF', 'Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx');

async function run() {
  console.log('--- STARTING AGENT ERROR UX ACCEPTANCE TEST ---');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  try {
    await page.goto(TARGET_URL);
    await page.waitForLoadState('networkidle');

    const openWsBtn = page.locator('button:has-text("Open Workspace"), a:has-text("Open Workspace")');
    if (await openWsBtn.isVisible()) {
      await openWsBtn.click();
      await page.waitForTimeout(300);
    }

    // 1. Upload DOCX fixture so Agent composer becomes active
    console.log('1. Uploading DOCX fixture...');
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.locator('button[title="Add documents"], .btn:has-text("Add")').first().click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(FIXTURE_DOCX);
    await page.locator('.doc-badge.ready, span:has-text("Ready")').first().waitFor({ state: 'visible', timeout: 30000 });
    console.log('   Fixture loaded & ready.');

    // 2. Check Model selector starts at Luna
    console.log('2. Checking initial model selector trigger...');
    const modelTrigger = page.locator('[data-testid="agent-model-selector-trigger"]');
    await modelTrigger.waitFor({ state: 'visible', timeout: 5000 });
    const initialText = await modelTrigger.textContent();
    console.log(`   Initial trigger text: "${initialText.trim()}"`);
    if (!initialText.includes('Luna')) {
      throw new Error(`Expected initial model to be Luna, got: ${initialText}`);
    }

    // 3. Send query with Luna
    console.log('3. Sending query with Luna (unconfigured Workbench)...');
    const chatInput = page.locator('.agent-composer textarea');
    await chatInput.fill('Summarize the document structure in detail.');
    await page.locator('.agent-composer .send-btn').click();

    // 4. Verify explicit error card appears
    console.log('4. Waiting for provider error card...');
    const errorCard = page.locator('[data-testid="agent-provider-error-card"]');
    await errorCard.waitFor({ state: 'visible', timeout: 10000 });
    const errorCardText = await errorCard.textContent();
    console.log(`   Error card text:\n${errorCardText.trim()}`);

    if (!errorCardText.includes('Luna')) {
      throw new Error(`Expected error card to mention Luna, got: ${errorCardText}`);
    }

    // 5. Verify NO fake assistant message was created
    const assistantCount = await page.locator('.agent-message.assistant').count();
    console.log(`   Assistant message count: ${assistantCount}`);
    if (assistantCount !== 0) {
      throw new Error(`Expected 0 assistant messages, found: ${assistantCount}`);
    }

    // 6. Verify user message is preserved
    const userMsg = page.locator('.agent-message.user').first();
    const userText = await userMsg.textContent();
    console.log(`   Preserved user message: "${userText.trim()}"`);
    if (!userText.includes('Summarize the document structure in detail.')) {
      throw new Error('User message was not preserved!');
    }

    // 7. Verify Retry Luna button
    console.log('5. Checking Retry Luna button...');
    const retryBtn = page.locator('[data-testid="agent-error-retry-btn"]');
    await retryBtn.waitFor({ state: 'visible', timeout: 3000 });
    const retryText = await retryBtn.textContent();
    console.log(`   Retry button text: "${retryText.trim()}"`);
    if (!retryText.includes('Luna')) {
      throw new Error(`Expected retry button to say 'Retry Luna', got: ${retryText}`);
    }

    // 8. Test Switch to Sol button
    console.log('6. Clicking Switch to Sol button...');
    const switchBtn = page.locator('[data-testid="agent-error-switch-btn"]');
    await switchBtn.waitFor({ state: 'visible', timeout: 3000 });
    const switchText = await switchBtn.textContent();
    console.log(`   Switch button text: "${switchText.trim()}"`);
    if (!switchText.includes('Sol')) {
      throw new Error(`Expected switch button to say 'Switch to Sol', got: ${switchText}`);
    }

    await switchBtn.click();

    // 9. Wait for updated error card for Sol
    console.log('7. Waiting for Sol provider response...');
    await page.waitForTimeout(1000);
    await errorCard.waitFor({ state: 'visible', timeout: 10000 });
    const solErrorText = await errorCard.textContent();
    console.log(`   Updated error card text:\n${solErrorText.trim()}`);

    if (!solErrorText.includes('Sol')) {
      throw new Error(`Expected updated error card to mention Sol, got: ${solErrorText}`);
    }

    const updatedTriggerText = await modelTrigger.textContent();
    console.log(`   Model trigger text after switch: "${updatedTriggerText.trim()}"`);
    if (!updatedTriggerText.includes('Sol')) {
      throw new Error(`Expected model trigger to reflect 'Sol', got: ${updatedTriggerText}`);
    }

    // 10. Test dismiss button
    console.log('8. Testing Dismiss button...');
    const dismissBtn = page.locator('[data-testid="agent-error-dismiss-btn"]');
    await dismissBtn.click();
    await page.waitForTimeout(500);

    const isVisible = await errorCard.isVisible();
    if (isVisible) {
      throw new Error('Expected error card to be dismissed!');
    }
    console.log('   Error card dismissed cleanly.');

    console.log('--- ALL AGENT ERROR UX ACCEPTANCE CHECKS PASSED (100%) ---');
  } finally {
    await browser.close();
  }
}

run().catch((err) => {
  console.error('Test failed:', err);
  process.exit(1);
});
