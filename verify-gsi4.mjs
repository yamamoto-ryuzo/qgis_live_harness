import { chromium } from 'playwright';
const KASC = 'http://127.0.0.1:8089/export-data/kasugai_canvas.kasc';
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const page = await browser.newPage();
const errs = [], logs = [];
page.on('pageerror', e => errs.push(String(e)));
page.on('console', m => logs.push(`${m.type()}:${m.text().slice(0,160)}`));
await page.goto(`http://127.0.0.1:8899/gsimaps/?kasc=${encodeURIComponent(KASC)}`, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(12000);
const info = await page.evaluate(() => ({
  unsupported: document.querySelector('#unsupported')?.textContent?.slice(0, 300) || null,
  status: document.querySelector('#inspector-status')?.textContent?.slice(0, 300) || null,
  dbg: !!window._gsimapsDbg,
  nEntries: window._gsimapsDbg?.layerEntries?.length ?? null,
}));
console.log(JSON.stringify(info));
console.log('ERRS:', errs.join(' | '));
console.log('LOGS:', logs.filter(l => !l.startsWith('warning')).join('\n').slice(0, 1500));
await browser.close();
