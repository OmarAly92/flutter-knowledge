const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ executablePath: process.argv[2], headless: true, args: ['--allow-file-access-from-files'] });
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
    await page.goto(process.argv[3]);
    await page.addScriptTag({ path: process.argv[4] });
    await page.addScriptTag({ path: process.argv[5] });
    await page.evaluate(() => document.fonts.ready);
    const snapshot = (selector, profile) => page.evaluate(({ selector, profile }) => captureFoundations({ selector, profile }), { selector, profile });
    const light = await snapshot('#library', { skin: 'light', state: 'idle' });
    await page.click('#save');
    await page.focus('#collection');
    const selected = await snapshot('#library', { skin: 'light', state: 'selected-focused' });
    await page.click('#mode');
    await page.evaluate(() => showView('settings'));
    const dark = await snapshot('#settings', { skin: 'dark', state: 'loading-selected' });
    await page.click('#settings .primary');
    const sheet = await snapshot('#sheet', { skin: 'dark', state: 'open' });
    const unresolved = await snapshot('body', { skin: 'dark', state: 'svg-dependency' });
    await page.route('https://styles.example.invalid/cross.css', (route) => route.fulfill({
      contentType: 'text/css', body: ':root { --foreign-rule: 1; }'
    }));
    await page.addStyleTag({ url: 'https://styles.example.invalid/cross.css' });
    const unavailable = await snapshot('body', { skin: 'dark', state: 'unavailable-cssom' });
    const font = require('fs').readFileSync(new URL('assets/body.ttf', process.argv[3])).toString('base64');
    await page.setContent(`<html lang="en"><style>
      @font-face { font-family: Orchard; src: url("data:font/ttf;base64,${font}"); font-weight: 400; }
      body { margin: 0; } #native { width: 300px; height: 400px; }
      input, textarea, select { font: 400 16px/19.2px Orchard; display: block; width: 150px; height: 30px; margin: 3px; }
      #native-placeholder::placeholder { font-size: 11px; font-weight: 500; font-style: italic; color: rgb(80, 90, 100); }
      #clip { width: 10px; height: 10px; overflow: hidden; }
      #native-clipped { margin-left: 40px; }
      #partial { width: 60px; height: 40px; overflow: hidden; }
      #native-offscreen { position: fixed; left: 800px; top: 0; }
      #native-outside { position: fixed; left: 320px; top: 0; }
    </style><body><main id="native">
      <input id="native-value" value="I"><input id="native-placeholder" placeholder="I">
      <textarea id="native-area">A</textarea><select id="native-select"><option>A</option><option selected>I</option></select>
      <input id="native-password" type="password" value="private-never-export">
      <input id="native-css-mask" style="-webkit-text-security:disc" value="css-private-never-export">
      <input id="native-empty-password" type="password" placeholder="I">
      <div style="opacity:0"><input id="native-transparent" value="I"></div>
      <div id="clip"><input id="native-clipped" value="I"></div>
      <div id="partial"><input id="native-partial" value="I"></div>
      <input id="native-offscreen" value="I"><input id="native-outside" value="I">
    </main></body></html>`);
    await page.evaluate(() => document.fonts.ready);
    const controls = await page.evaluate(() => captureFoundations({ selector: '#native', captureTarget: '#native',
      profile: { skin: 'light', state: 'native-controls', locale: 'en' } }));
    process.stdout.write(JSON.stringify({ light, selected, dark, sheet, unresolved, unavailable, controls }));
  } finally {
    await browser.close();
  }
})().catch((error) => { process.stderr.write(String(error)); process.exitCode = 1; });
