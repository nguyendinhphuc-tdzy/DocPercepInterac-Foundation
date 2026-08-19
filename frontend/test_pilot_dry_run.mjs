/**
 * test_pilot_dry_run.mjs
 *
 * Internal instrumentation dry run (docs/evaluation/agent-pilot/, phase 28).
 * Exercises the Pilot Mode UI affordances the automated Playwright regression
 * suite does not touch: scenario launcher, task start/complete, citation
 * click + reveal, and the feedback widget — so the pilot event log has real
 * end-to-end coverage before any real pilot participant runs a scenario.
 *
 * This script is automation, not a real pilot user. Its output belongs in
 * the "Internal Dry Run" section of Agent_Pilot_Report.md, never in the
 * real pilot-results sections.
 */
import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const TARGET_URL = process.argv[2] || 'http://localhost:5173';
const FIXTURE_DOCX = path.resolve(__dirname, '..', 'anonymize client', 'Demo files', 'Demo files', 'Compare LF', 'Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx');

(async () => {
  console.log('='.repeat(60));
  console.log('PILOT INSTRUMENTATION DRY RUN (automated, not a real pilot user)');
  console.log(`Target: ${TARGET_URL}`);
  console.log('='.repeat(60));

  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();
  page.on('console', (msg) => {
    if (msg.type() === 'error') console.log(`[Browser Error]: ${msg.text()}`);
  });

  try {
    await page.goto(TARGET_URL);
    await page.waitForLoadState('networkidle');

    const openWsBtn = page.locator('button:has-text("Open Workspace"), a:has-text("Open Workspace")');
    if (await openWsBtn.isVisible()) {
      await openWsBtn.click();
      await page.waitForTimeout(300);
    }

    console.log('\n>>> UPLOADING FIXTURE DOCX...');
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.locator('button[title="Add documents"], .btn:has-text("Add")').first().click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(FIXTURE_DOCX);
    await page.locator('.doc-badge.ready, span:has-text("Ready")').first().waitFor({ state: 'visible', timeout: 30000 });
    console.log('  [+] Document perceived and Ready.');

    console.log('\n>>> ENABLING PILOT MODE...');
    await page.locator('button[title*="Pilot mode"]').click();
    await page.waitForTimeout(300);
    const scenarioSelect = page.locator('.agent-pane select');
    await scenarioSelect.waitFor({ state: 'visible', timeout: 5000 });
    const optionCount = await scenarioSelect.locator('option').count();
    console.log(`  [+] Pilot Mode enabled. Scenario launcher populated with ${optionCount - 1} scenarios.`);

    console.log('\n>>> STARTING SCENARIO 001...');
    await scenarioSelect.selectOption('001_selected_summary');
    await page.waitForTimeout(200);
    const taskBadge = page.locator('text=Task in progress:');
    await taskBadge.waitFor({ state: 'visible', timeout: 3000 });
    console.log('  [+] pilot.task.started emitted (task badge visible).');

    console.log('\n>>> SELECT ELEMENT + SUMMARIZE (agent.citation.clicked + reveal)...');
    await page.waitForFunction(() => window.__DOCX_MAPPING_REPORT__ !== undefined, { timeout: 30000 });
    const targetPara = page.locator('.docx-render p:has-text("Contents")').first();
    await targetPara.click();
    await page.waitForTimeout(300);
    const explainChip = page.locator('button:has-text("Explain Selection")');
    await explainChip.click();
    await page.waitForSelector('.agent-message.assistant', { timeout: 15000 });

    const citationBtn = page.locator('.agent-message.assistant button').filter({ hasText: /para|heading|Contents/ }).first();
    await citationBtn.waitFor({ state: 'visible', timeout: 5000 });
    await citationBtn.click();
    await page.waitForTimeout(400);
    console.log('  [+] Citation clicked (agent.citation.clicked + agent.reveal.completed emitted).');

    console.log('\n>>> SUBMITTING PILOT FEEDBACK...');
    const helpfulYesBtn = page.locator('.agent-message.assistant button[title="Yes, helpful"]').last();
    await helpfulYesBtn.waitFor({ state: 'visible', timeout: 5000 });
    await helpfulYesBtn.click();
    await page.waitForTimeout(200);
    const thanksText = page.locator('text=Thanks for the feedback.');
    await thanksText.waitFor({ state: 'visible', timeout: 3000 });
    console.log('  [+] pilot.feedback.submitted emitted (helpful=true).');

    console.log('\n>>> COMPLETING TASK...');
    await page.locator('button:has-text("Mark Complete")').click();
    await page.waitForTimeout(300);
    console.log('  [+] pilot.task.completed emitted.');

    console.log('\n' + '='.repeat(60));
    console.log('PILOT DRY RUN UI COVERAGE COMPLETE');
    console.log('='.repeat(60));
  } catch (err) {
    console.error('Pilot dry run failed:', err);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
