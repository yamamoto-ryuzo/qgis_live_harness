import { chromium } from 'playwright';
const KASC = 'http://127.0.0.1:8089/export-data/kasugai_canvas.kasc';
const engine = process.argv[2] || 'maplibre';
const url = `http://127.0.0.1:8899/${engine}/?kasc=${encodeURIComponent(KASC)}&follow=1`;
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const page = await browser.newPage({ viewport: { width: 1200, height: 800 } });
await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
await page.waitForTimeout(6000);
const info = await page.evaluate(() => {
  const cands = Object.entries(window)
    .filter(([k, v]) => v && typeof v === 'object' && typeof v.getSource === 'function' && typeof v.getZoom === 'function')
    .map(([k, v]) => {
      const s = (() => { try { return v.getSource('qgis-sel'); } catch (_) { return null; } })();
      return { key: k, zoom: v.getZoom(), hasSel: !!s, selFeats: s?._data?.features?.length ?? null };
    });
  return { cands };
});
await page.screenshot({ path: process.env.TEMP + '/devin-live/' + engine + '-sel.png' });
console.log(JSON.stringify(info));
await browser.close();
