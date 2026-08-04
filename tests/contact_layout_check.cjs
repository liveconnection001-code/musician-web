const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const baseUrl = process.env.MUSICIAN_CONTACT_VISUAL_URL;
const baselineUrl = process.env.MUSICIAN_CONTACT_BASELINE_URL;
const screenshotDir = process.env.MUSICIAN_CONTACT_SCREENSHOT_DIR;
if (!baseUrl || !baselineUrl || !screenshotDir) {
  throw new Error('MUSICIAN_CONTACT_VISUAL_URL, MUSICIAN_CONTACT_BASELINE_URL and MUSICIAN_CONTACT_SCREENSHOT_DIR are required.');
}

async function checkViewport(browser, name, width, height) {
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
  await page.goto(baseUrl, { waitUntil: 'networkidle' });
  await page.waitForSelector('#attendee_count');
  await page.waitForSelector('#photo_numbers');

  const result = await page.evaluate(() => {
    const checks = ['attendee_count', 'photo_numbers'].map((id) => {
      const input = document.getElementById(id);
      const row = input && input.closest('tr');
      const label = row && row.querySelector('label');
      const bounds = input && input.getBoundingClientRect();
      return {
        id,
        hasRow: Boolean(row),
        label: label && label.textContent.trim(),
        visible: Boolean(bounds && bounds.width > 0 && bounds.height > 0),
        withinViewport: Boolean(bounds && bounds.left >= 0 && bounds.right <= window.innerWidth + 1),
      };
    });
    const form = document.getElementById('contact-form');
    return {
      checks,
      scrollWidth: document.documentElement.scrollWidth,
      viewportWidth: window.innerWidth,
      formScrollWidth: form.scrollWidth,
      formClientWidth: form.clientWidth,
    };
  });

  for (const field of result.checks) {
    if (!field.hasRow || !field.visible || !field.withinViewport) {
      throw new Error(`${name}: ${field.id} is not displayed within the form layout: ${JSON.stringify(field)}`);
    }
  }
  if (result.formScrollWidth > result.formClientWidth + 1) {
    throw new Error(`${name}: the contact form itself has horizontal overflow (${result.formScrollWidth}px > ${result.formClientWidth}px).`);
  }

  await page.screenshot({ path: path.join(screenshotDir, `contact-${name}.png`), fullPage: true });
  if (result.scrollWidth > result.viewportWidth + 1) {
    await page.goto(baselineUrl, { waitUntil: 'networkidle' });
    const baselineScrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    if (result.scrollWidth > baselineScrollWidth + 1) {
      throw new Error(`${name}: page horizontal overflow increased from ${baselineScrollWidth}px to ${result.scrollWidth}px.`);
    }
    console.log(`[PASS] T8 ${name}: existing page-level overflow (${result.scrollWidth}px) is unchanged from baseline; the form has none.`);
  }
  await page.close();
  console.log(`[PASS] T8 ${name}: new rows are visible within the form layout.`);
}

(async () => {
  fs.mkdirSync(screenshotDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    await checkViewport(browser, 'desktop-1440', 1440, 1000);
    await checkViewport(browser, 'mobile-375', 375, 812);
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(`[FAIL] T8 ${error.message}`);
  process.exit(1);
});
