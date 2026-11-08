import { chromium } from 'playwright';
const KASC = 'http://127.0.0.1:8089/export-data/kasugai_canvas.kasc';
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const page = await browser.newPage();
await page.goto(`http://127.0.0.1:8899/gsimaps/?kasc=${encodeURIComponent(KASC)}`, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(9000);
const st = await page.evaluate(async () => (await import('/shared/live.js')).liveStatus());
console.log('gsimaps live:', JSON.stringify(st));
await browser.close();
