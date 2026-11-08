import { chromium } from 'playwright';
const KASC = 'http://127.0.0.1:8089/export-data/kasugai_canvas.kasc';
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const page = await browser.newPage();
await page.goto(`http://127.0.0.1:8899/gsimaps/?kasc=${encodeURIComponent(KASC)}`, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(12000);
// 手動 configureLive でモジュール自体は動くか確認
const r = await page.evaluate(async () => {
  const live = await import('/shared/live.js');
  const st0 = live.liveStatus();
  live.configureLive({ live: { url: 'http://127.0.0.1:8089' } }, {
    baseUrl: 'http://127.0.0.1:8089/export-data/',
    getView: () => ({}),
  });
  await new Promise(r => setTimeout(r, 300));
  return { before: st0, after: live.liveStatus() };
});
console.log(JSON.stringify(r));
await browser.close();
