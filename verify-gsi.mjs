import { chromium } from 'playwright';
const KASC = 'http://127.0.0.1:8089/export-data/kasugai_canvas.kasc';
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const page = await browser.newPage();
const errs = [], logs = [];
page.on('pageerror', e => errs.push(String(e)));
page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') logs.push(m.text()); });
await page.goto(`http://127.0.0.1:8899/gsimaps/?kasc=${encodeURIComponent(KASC)}`, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(12000);
const info = await page.evaluate(() => ({
  inspector: document.querySelector('#inspector-input')?.value?.slice(0, 120) || null,
  title: document.title,
  layers: document.querySelectorAll('#layers .layer-row, #layers li').length,
}));
const st = await page.evaluate(async () => (await import('/shared/live.js')).liveStatus());
console.log(JSON.stringify({ info, live: st, errs: errs.slice(0,3), logs: logs.slice(0,6) }));
await browser.close();
