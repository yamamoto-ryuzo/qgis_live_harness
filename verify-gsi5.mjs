import { chromium } from 'playwright';
const KASC = 'http://127.0.0.1:8089/export-data/kasugai_canvas.kasc';
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const page = await browser.newPage();
const reqs = [];
page.on('response', r => { if (r.url().includes('live') || r.url().includes('8089')) reqs.push(`${r.status()} ${r.url().replace('http://127.0.0.1:8089','')}`); });
page.on('requestfailed', r => { if (r.url().includes('8089')) reqs.push(`FAIL ${r.url()}`); });
await page.goto(`http://127.0.0.1:8899/gsimaps/?kasc=${encodeURIComponent(KASC)}`, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(14000);
const appjs = await page.evaluate(async () => {
  const r = await fetch('/gsimaps/app.js'); const t = await r.text();
  return { hasCfgLive: /configureLive\(doc/.test(t), len: t.length };
});
console.log(JSON.stringify(appjs)); console.log(reqs.slice(0, 25).join('\n'));
await browser.close();
