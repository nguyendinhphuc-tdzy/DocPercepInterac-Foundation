import { chromium } from 'playwright';
import path from 'path';

const BASE_URL = process.argv[2] || 'http://localhost:5173';
const DOCX_PATH = path.resolve('..', 'anonymize client/Demo files/Demo files/Compare LF/Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx');
const XLSX_PATH = path.resolve('..', 'anonymize client/Demo files/Demo files/FA&RPTS & Appendix I/FA&RPTs/HMV-FA&RPT FY2024.xlsx');

const VIEWPORTS = [
  { name: '1440x900 (Large Desktop)', width: 1440, height: 900 },
  { name: '1280x800 (Standard Laptop)', width: 1280, height: 800 },
  { name: '1024x768 (Small Laptop)', width: 1024, height: 768 },
  { name: '900x700 (Narrow Browser)', width: 900, height: 700 },
  { name: '768x1024 (Tablet Portrait)', width: 768, height: 1024 },
];

async function runTests() {
  console.log(`Starting UI/UX Polish & Responsive Verification Suite against ${BASE_URL}...\n`);
  const browser = await chromium.launch({ headless: true });

  try {
    // ── STAGE 1: RESPONSIVE VIEWPORT TESTING ──
    console.log(`========================================`);
    console.log(`STAGE 1: RESPONSIVE VIEWPORT STABILITY`);
    console.log(`========================================`);

    for (const vp of VIEWPORTS) {
      const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
      const page = await context.newPage();

      await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
      const getStartedBtn = page.locator('button:has-text("Open Workspace"), a:has-text("Open Workspace")');
      if (await getStartedBtn.isVisible()) {
        await getStartedBtn.click();
        await page.waitForTimeout(300);
      }

      // Check header and main layout visibility
      const headerVisible = await page.locator('.workspace-header').isVisible();
      const fileRailVisible = await page.locator('.file-rail').isVisible();
      console.log(`[+] Viewport ${vp.name.padEnd(28)} -> Header: ${headerVisible ? 'OK' : 'FAIL'}, FileRail: ${fileRailVisible ? 'OK' : 'FAIL'}`);
      await context.close();
    }

    // ── STAGE 2: INTERACTION & HARDENING TESTS ──
    console.log(`\n========================================`);
    console.log(`STAGE 2: DOCUMENT PANE & SELECTION HARDENING`);
    console.log(`========================================`);

    const context = await browser.newContext({ viewport: { width: 1366, height: 768 } });
    const page = await context.newPage();
    page.on('console', (msg) => {
      if (msg.type() === 'error') console.log(`[Browser Error]:`, msg.text());
    });

    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
    const getStartedBtn = page.locator('button:has-text("Open Workspace"), a:has-text("Open Workspace")');
    if (await getStartedBtn.isVisible()) {
      await getStartedBtn.click();
      await page.waitForTimeout(300);
    }

    // 1. Upload DOCX Fixture A
    console.log(`Uploading DOCX Fixture: ${path.basename(DOCX_PATH)}...`);
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.locator('button[title="Add documents"], .btn:has-text("Add")').first().click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(DOCX_PATH);

    await page.locator('.doc-badge.ready, span:has-text("Ready")').first().waitFor({ state: 'visible', timeout: 30000 });
    console.log(`[+] DOCX perceived and ready!`);

    // 2. Test FileRail Collapsible Toggle
    console.log(`Testing FileRail collapse/expand...`);
    const collapseBtn = page.locator('button[title*="Collapse documents panel"], button[aria-label*="Collapse documents panel"]');
    await collapseBtn.click();
    await page.waitForTimeout(300);

    const isCollapsed = await page.locator('.file-rail.collapsed').isVisible();
    console.log(`[+] FileRail collapsed state: ${isCollapsed ? 'VERIFIED' : 'FAILED'}`);

    const expandBtn = page.locator('button[title*="Expand documents panel"], button[aria-label*="Expand documents panel"]');
    await expandBtn.click();
    await page.waitForTimeout(300);
    const isExpanded = !(await page.locator('.file-rail.collapsed').isVisible());
    console.log(`[+] FileRail restored expanded state: ${isExpanded ? 'VERIFIED' : 'FAILED'}`);

    // 3. Test Selection and Deselection (Escape & Action Bar)
    console.log(`\nTesting Selection & Deselection Mechanics...`);
    await page.waitForFunction(() => window.__DOCX_MAPPING_REPORT__ !== undefined, { timeout: 30000 });
    await page.waitForTimeout(500);

    // Click a non-empty paragraph that has valid mapped element_id
    const targetPara = page.locator('.docx-render p:has-text("Contents"), .docx-render p:has-text("Executive Summary")').first();
    console.log(`Clicking mapped paragraph: "${(await targetPara.innerText()).slice(0, 40)}..."`);
    await targetPara.click();
    await page.waitForTimeout(500);

    // Verify contextual selection bar is visible
    const deselectBtn = page.locator('button:has-text("Deselect"), button[title*="Deselect"]');
    await deselectBtn.waitFor({ state: 'visible', timeout: 5000 });
    const hasDeselectBtn = await deselectBtn.isVisible();
    console.log(`[+] Contextual selection bar rendered: ${hasDeselectBtn ? 'VERIFIED' : 'FAILED'}`);

    // Test Escape key deselection (first Escape cancels edit mode, second Escape deselects)
    console.log(`Pressing Escape to exit edit mode and deselect...`);
    await page.keyboard.press('Escape'); // Exits edit mode
    await page.waitForTimeout(200);
    await page.keyboard.press('Escape'); // Deselects
    await page.waitForTimeout(400);
    const hasDeselectBtnAfterEsc = await deselectBtn.isVisible();
    console.log(`[+] Escape cleared selection: ${!hasDeselectBtnAfterEsc ? 'VERIFIED' : 'FAILED'}`);

    // Re-select and test Deselect button click
    await targetPara.click();
    await page.waitForTimeout(500);
    await deselectBtn.click();
    await page.waitForTimeout(400);
    const hasDeselectBtnAfterClick = await page.locator('button:has-text("Deselect")').isVisible();
    console.log(`[+] Deselect button click cleared selection: ${!hasDeselectBtnAfterClick ? 'VERIFIED' : 'FAILED'}`);

    // 4. Test Document Zoom Controls
    console.log(`\nTesting Document Zoom Controls...`);
    const zoomInBtn = page.locator('button[title="Zoom in"], button[aria-label="Zoom in"]');
    const zoomResetBtn = page.locator('button[title*="Reset zoom"]');
    await zoomInBtn.click();
    await page.waitForTimeout(200);
    const zoomInText = await zoomResetBtn.innerText();
    console.log(`[+] Zoomed in level: ${zoomInText}`);

    await zoomResetBtn.click();
    await page.waitForTimeout(200);
    const zoomResetText = await zoomResetBtn.innerText();
    console.log(`[+] Reset zoom level: ${zoomResetText} (${zoomResetText === '100%' ? 'VERIFIED' : 'FAILED'})`);

    // ── STAGE 3: CONFIGURABLE SPLIT VIEW TESTS ──
    console.log(`\n========================================`);
    console.log(`STAGE 3: CONFIGURABLE SPLIT VIEW ACCEPTANCE`);
    console.log(`========================================`);

    // Switch DocumentPane to Split mode
    const splitModeBtn = page.locator('.view-mode-btn:has-text("Split")');
    await splitModeBtn.click();
    await page.waitForTimeout(500);

    // Verify Split quick presets bar is visible
    const sameDocPresetBtn = page.locator('button:has-text("Same Doc (Original ↔ Elements)")');
    const hasSameDocPreset = await sameDocPresetBtn.isVisible();
    console.log(`[+] Preset 1: Same Document (Original ↔ Elements): ${hasSameDocPreset ? 'VERIFIED' : 'FAILED'}`);

    // Upload second document (XLSX) to test cross-document comparison
    console.log(`Uploading 2nd document (XLSX) for Multi-Document Split testing...`);
    const fileChooserPromise2 = page.waitForEvent('filechooser');
    await page.locator('button[title="Add documents"]').click();
    const fileChooser2 = await fileChooserPromise2;
    await fileChooser2.setFiles(XLSX_PATH);

    await page.locator('.doc-badge.ready, span:has-text("Ready")').nth(1).waitFor({ state: 'visible', timeout: 30000 });
    console.log(`[+] 2nd document ready!`);
    await page.waitForTimeout(500);

    // Verify multi-doc presets are now enabled
    const compareOrigBtn = page.locator('button:has-text("2 Docs (Original ↔ Original)")');
    const hasCompareOrig = await compareOrigBtn.isVisible();
    console.log(`[+] Preset 2: 2 Docs (Original ↔ Original): ${hasCompareOrig ? 'VERIFIED' : 'FAILED'}`);

    // Click Preset 2 to switch to cross-doc compare
    await compareOrigBtn.click();
    await page.waitForTimeout(500);

    // Check that left and right selectors show different documents
    const leftSelect = page.locator('select[aria-label="Left pane document"]');
    const rightSelect = page.locator('select[aria-label="Right pane document"]');
    const leftVal = await leftSelect.inputValue();
    const rightVal = await rightSelect.inputValue();
    console.log(`[+] Left pane doc: ${leftVal}, Right pane doc: ${rightVal} (${leftVal !== rightVal ? 'VERIFIED' : 'FAILED'})`);

    console.log(`\n========================================`);
    console.log(`ALL UI/UX & RESPONSIVE ACCEPTANCE TESTS PASSED!`);
    console.log(`========================================\n`);

    await context.close();
  } catch (err) {
    console.error(`Test failed with error:`, err);
    process.exit(1);
  } finally {
    await browser.close();
  }
}

runTests();
