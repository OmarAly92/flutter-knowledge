const fs = require('node:fs');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ executablePath: process.argv[2], headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 420, height: 700 }, deviceScaleFactor: 2 });
    await page.setContent(fs.readFileSync(process.argv[3], 'utf8'));
    await page.addScriptTag({ path: process.argv[4] });
    const result = await page.evaluate(() => {
      const screen = '[data-screen-label="Chat"]';
      const extract = (captureTarget) => typeof captureComposition === 'function'
        ? captureComposition(screen, { captureTarget }) : null;
      const legacy = layoutTree(screen);
      const shell = extract('.sa-appwrap');
      const narrow = extract(screen);
      const viewport = extract(undefined);
      document.querySelector('#overlay').style.display = 'none';
      const closed = extract('.sa-appwrap');
      let invalid = null;
      if (typeof captureComposition === 'function') {
        try { captureComposition(screen, { captureTarget: '#missing' }); }
        catch (error) { invalid = error.message; }
      }
      return { legacy, shell, narrow, viewport, closed, invalid };
    });
    process.stdout.write(JSON.stringify(result));
  } finally {
    await browser.close();
  }
})().catch((error) => { process.stderr.write(String(error)); process.exitCode = 1; });
