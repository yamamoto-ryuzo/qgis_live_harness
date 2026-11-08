import { chromium } from 'playwright';
const KASC = 'http://127.0.0.1:8089/export-data/kasugai_canvas.kasc';
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const page = await browser.newPage();
const errs = [];
page.on('pageerror', e => errs.push(String(e)));
await page.goto(`http://127.0.0.1:8899/gsimaps/?kasc=${encodeURIComponent(KASC)}`, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(12000);
const info = await page.evaluate(async () => {
  const kasc = await import('/shared/kasc.js');
  const text = document.querySelector('#inspector-input')?.value || '';
  const doc = kasc.parseKasc(text);
  return { live: doc.live, hasLiveLine: /\blive\s*:/m.test(text) };
});
console.log(JSON.stringify(info), 'errs:', errs.slice(0,3).join('|'));
await browser.close();
