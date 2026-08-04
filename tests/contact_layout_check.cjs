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
    const visibleChecks = ['attendee_count'].map((id) => {
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
    const photoInput = document.getElementById('photo_numbers');
    const photoBounds = photoInput && photoInput.getBoundingClientRect();
    const honeypot = photoInput && photoInput.closest('.contact-form__honeypot');
    const genreRow = document.getElementById('genre').closest('tr');
    const nextRowInput = genreRow && genreRow.nextElementSibling && genreRow.nextElementSibling.querySelector('input, textarea, select');
    const form = document.getElementById('contact-form');
    return {
      visibleChecks,
      photoHoneypot: {
        hasRow: Boolean(photoInput && photoInput.closest('tr')),
        visible: Boolean(photoBounds && photoBounds.width > 0 && photoBounds.height > 0 && photoBounds.left >= 0 && photoBounds.right <= window.innerWidth + 1),
        ariaHidden: photoInput && photoInput.getAttribute('aria-hidden'),
        tabIndex: photoInput && photoInput.tabIndex,
        autocomplete: photoInput && photoInput.getAttribute('autocomplete'),
        parentAriaHidden: honeypot && honeypot.getAttribute('aria-hidden'),
        parentDisplay: honeypot && getComputedStyle(honeypot).display,
      },
      genreThenMessage: Boolean(nextRowInput && nextRowInput.id === 'message'),
      scrollWidth: document.documentElement.scrollWidth,
      viewportWidth: window.innerWidth,
      formScrollWidth: form.scrollWidth,
      formClientWidth: form.clientWidth,
    };
  });

  for (const field of result.visibleChecks) {
    if (!field.hasRow || !field.visible || !field.withinViewport) {
      throw new Error(`${name}: ${field.id} is not displayed within the form layout: ${JSON.stringify(field)}`);
    }
  }
  const photo = result.photoHoneypot;
  if (photo.hasRow || photo.visible || photo.ariaHidden !== 'true' || photo.tabIndex !== -1 || photo.autocomplete !== 'off' || photo.parentAriaHidden !== 'true' || photo.parentDisplay === 'none') {
    throw new Error(`${name}: K-T6/K-T7 photo-number honeypot contract failed: ${JSON.stringify(photo)}`);
  }
  if (!result.genreThenMessage) {
    throw new Error(`${name}: K-T6 genre must be followed directly by the message row.`);
  }
  await page.screenshot({ path: path.join(screenshotDir, `contact-${name}.png`), fullPage: true });
  await page.goto(baselineUrl, { waitUntil: 'networkidle' });
  const baseline = await page.evaluate(() => {
    const form = document.getElementById('contact-form');
    return {
      scrollWidth: document.documentElement.scrollWidth,
      formScrollWidth: form.scrollWidth,
      formClientWidth: form.clientWidth,
    };
  });
  if (result.scrollWidth > baseline.scrollWidth + 1) {
    throw new Error(`${name}: page horizontal overflow increased from ${baseline.scrollWidth}px to ${result.scrollWidth}px.`);
  }
  if (result.formScrollWidth > baseline.formScrollWidth + 1) {
    throw new Error(`${name}: contact form overflow increased from ${baseline.formScrollWidth}px to ${result.formScrollWidth}px.`);
  }
  if (result.formScrollWidth > result.formClientWidth + 1) {
    console.log(`[PASS] K-T6 ${name}: form width (${result.formScrollWidth}px) remains within the viewport.`);
  }
  await page.close();
  console.log(`[PASS] K-T6/K-T7 ${name}: photo row is removed; genre-to-message order and honeypot accessibility contract are valid.`);
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
