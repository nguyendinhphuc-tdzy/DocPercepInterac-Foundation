import { chromium } from 'playwright';
import path from 'path';

const FIXTURE_A = 'C:\\Users\\PC\\Downloads\\DocPercepInterac Foundation\\anonymize client\\Demo files\\Demo files\\Compare LF\\Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx';
const FIXTURE_B = 'C:\\Users\\PC\\Downloads\\DocPercepInterac Foundation\\anonymize client\\Demo files\\Demo files\\Compare LF\\HMV-26-Final-Local File for FY2024-EN-R2901KPMG_drifted.docx';
const BASE_URL = process.argv[2] || 'http://localhost:5250';

async function testFixture(page, name, fixturePath) {
  console.log(`\n========================================`);
  console.log(`TESTING FIXTURE: ${name}`);
  console.log(`========================================`);
  
  await page.goto(BASE_URL, { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: /open workspace/i }).click();
  await page.waitForTimeout(500);

  const t0 = Date.now();
  console.log(`Uploading ${path.basename(fixturePath)}...`);
  await page.locator('input[type="file"]').first().setInputFiles(fixturePath);

  await page.waitForFunction(() => document.body.innerText.includes('Ready'), { timeout: 120000 });
  console.log(`Backend perceived & Ready in ${Date.now() - t0}ms`);

  // Switch to Inspect layout
  const layoutBtn = page.getByRole('button', { name: /^Agent$|^Inspect$/i }).first();
  await layoutBtn.click({ timeout: 10000 });
  await page.getByText(/^Inspect$/i).last().click({ timeout: 10000 });

  // Wait for mapping report to be set on window
  const t1 = Date.now();
  await page.waitForFunction(() => (window).__DOCX_MAPPING_REPORT__ != null, { timeout: 120000 });
  console.log(`Rendered & mapped in ${Date.now() - t1}ms`);

  const report = await page.evaluate(() => (window).__DOCX_MAPPING_REPORT__);
  console.log('MAPPING REPORT:', JSON.stringify(report, null, 2));

  // Test bidirectional interaction: click an element in Elements pane, verify selected class in document
  const allRows = page.locator('.element-tree-item');
  const rowCount = await allRows.count();
  console.log(`Elements tree row count: ${rowCount}`);

  if (rowCount > 0) {
    // Click 5th element
    const sampleIdx = Math.min(4, rowCount - 1);
    await allRows.nth(sampleIdx).click();
    await page.waitForTimeout(200);
    const selectedInDoc = await page.locator('.docx-el-selected').count();
    console.log(`Element at row ${sampleIdx} selected -> in DOM .docx-el-selected count: ${selectedInDoc}`);
  }

  return report;
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });

  const reportA = await testFixture(page, 'Fixture A (848-element KPMG template)', FIXTURE_A);
  const reportB = await testFixture(page, 'Fixture B (2,832-element HMV real doc)', FIXTURE_B);

  console.log('\n========================================');
  console.log('SUMMARY TABLE:');
  console.log('========================================');
  console.log('Fixture A Total:', reportA.total, 'Available:', reportA.byStatus.available, 'Unavailable:', reportA.byStatus.unavailable, 'Ambiguous:', reportA.byStatus.ambiguous);
  console.log('Fixture A byType:', JSON.stringify(reportA.byType));
  console.log('----------------------------------------');
  console.log('Fixture B Total:', reportB.total, 'Available:', reportB.byStatus.available, 'Unavailable:', reportB.byStatus.unavailable, 'Ambiguous:', reportB.byStatus.ambiguous);
  console.log('Fixture B byType:', JSON.stringify(reportB.byType));
  console.log('========================================');

  await browser.close();
})().catch((err) => {
  console.error('TEST ERROR:', err);
  process.exit(1);
});
