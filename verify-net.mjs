import { chromium } from 'playwright';
const KASC = 'http://127.0.0.1:8089/export-data/kasugai_canvas.kasc';
const url = `http://127.0.0.1:8899/maplibre/?kasc=${encodeURIComponent(KASC)}&follow=1`;
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const page = await browser.newPage();
const reqs = [];
page.on('response', r => { if (r.url().includes('8089')) reqs.push(`${r.status()} ${r.url()}`); });
page.on('requestfailed', r => { if (r.url().includes('8089')) reqs.push(`FAIL ${r.url()} ${r.failure()?.errorText}`); });
await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
await page.waitForTimeout(8000);
console.log(reqs.join('\n'));
// 手動で /live/state を fetch して CORS 確認
const manual = await page.evaluate(async () => {
  try {
    const r = await fetch('http://127.0.0.1:8089/live/state', { cache: 'no-store' });
    const d = await r.json();
    return { ok: r.ok, hasQS: !!d?.live?.qgis_selection, qs: d?.live?.qgis_selection };
  } catch (e) { return { err: String(e) }; }
});
console.log(JSON.stringify(manual));
await browser.close();
