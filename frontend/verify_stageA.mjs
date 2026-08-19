import { chromium } from 'playwright';
import path from 'path';

const SCREENSHOT_DIR = path.resolve(process.argv[2] || '.');
const BASE_URL = process.argv[3] || 'http://localhost:5245';
const FIXTURE = 'C:\\Users\\PC\\Downloads\\DocPercepInterac Foundation\\anonymize client\\Demo files\\Demo files\\Compare LF\\Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx';

const consoleErrors = [];
let shot = 0;
const nextShot = (page, name) => page.screenshot({ path: path.join(SCREENSHOT_DIR, `${String(++shot).padStart(2, '0')}-${name}.png`) });

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  page.on('console', (msg) => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
  page.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err.message));

  await page.goto(BASE_URL, { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: /open workspace/i }).click();
  await page.waitForTimeout(300);
  await page.locator('input[type="file"]').first().setInputFiles(FIXTURE);
  await page.waitForFunction(() => document.body.innerText.includes('Ready'), { timeout: 30000 }).catch((e) => console.log('WAIT_READY_FAILED', e.message));
  await page.waitForSelector('.docx-render', { timeout: 20000 });

  const layoutBtn = page.getByRole('button', { name: /^Agent$|^Inspect$/i }).first();
  await layoutBtn.click({ timeout: 5000 });
  await page.getByText(/^Inspect$/i).last().click({ timeout: 5000 });
  await page.waitForFunction(() => /mapping: \d+ total/.test(document.body.innerText), { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(1500);
  await nextShot(page, 'inspect-overview');

  const diagText = await page.locator('text=/mapping: \\d+ total/').first().innerText().catch(() => null);
  console.log('DEV_DIAGNOSTICS_LINE:', diagText);

  const totalElementsText = await page.locator('text=/^\\d+ elements$/').first().innerText().catch(() => null);
  console.log('TOTAL_ELEMENTS_HEADER:', totalElementsText);

  // Bidirectional check for a footnote
  const allRows = page.locator('.element-tree-item');
  const footnoteIndices = await allRows.evaluateAll((rows) =>
    rows.map((r, i) => ({ i, type: r.querySelector('.element-type')?.textContent?.trim().toLowerCase() })).filter((r) => r.type === 'footnote').map((r) => r.i)
  );
  console.log('FOOTNOTE_ROW_COUNT:', footnoteIndices.length);
  let footnoteVerified = 0;
  for (const idx of footnoteIndices) {
    await allRows.nth(idx).click();
    await page.waitForTimeout(150);
    const selected = page.locator('.docx-el-selected');
    if ((await selected.count()) > 0) {
      const tag = await selected.first().evaluate((n) => n.tagName);
      const noteId = await selected.first().evaluate((n) => n.getAttribute('data-note-id'));
      console.log(`FOOTNOTE_MATCH idx=${idx} tag=${tag} data-note-id=${noteId}`);
      footnoteVerified += 1;
      if (footnoteVerified === 1) {
        await nextShot(page, 'footnote-selected');
        await selected.first().dispatchEvent('click');
        await page.waitForTimeout(300);
        const backSelected = await page.locator('.element-tree-item.selected').count();
        console.log('CLICK_LI_SELECTS_IN_ELEMENTS:', backSelected);
      }
    }
  }
  console.log('FOOTNOTES_VERIFIED_COUNT:', footnoteVerified, '/', footnoteIndices.length);

  const docText = await page.locator('.docx-render').first().innerText();
  console.log('DOC_TEXT_LENGTH:', docText.length);
  console.log('CONSOLE_ERRORS_COUNT:', consoleErrors.length);
  if (consoleErrors.length) console.log('CONSOLE_ERRORS:', JSON.stringify(consoleErrors.slice(0, 15), null, 2));

  await browser.close();
})().catch((err) => { console.error('SCRIPT_ERROR:', err); process.exit(1); });
