import { chromium } from 'playwright';
const KASC = 'http://127.0.0.1:8089/export-data/kasugai_canvas.kasc';
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const page = await browser.newPage();
await page.goto(`http://127.0.0.1:8899/gsimaps/?kasc=${encodeURIComponent(KASC)}`, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(15000);
const r = await page.evaluate(() => ({
  pending: window._gsimapsDbg?.layerEntries?.filter(e => e.pending).length,
  failed: window._gsimapsDbg?.layerEntries?.filter(e => e.failed).map(e => e.item?.title),
  booted: !!document.querySelector('#layers .layer-row'),
}));
console.log(JSON.stringify(r));
await browser.close();
