import { chromium } from 'playwright';
const KASC = 'http://127.0.0.1:8089/export-data/kasugai_canvas.kasc';
const engine = process.argv[2] || 'maplibre';
const url = `http://127.0.0.1:8899/${engine}/?kasc=${encodeURIComponent(KASC)}&follow=1`;
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const page = await browser.newPage({ viewport: { width: 1200, height: 800 } });
const errs = [];
page.on('pageerror', e => errs.push(String(e)));
await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
await page.waitForTimeout(8000);
const info = await page.evaluate(async () => {
  const mod = await import('/shared/live.js');
  const out = { live: mod.liveStatus(), winKeys: [] };
  for (const k of Object.keys(window)) {
    try { if (window[k] && typeof window[k] === 'object' && typeof window[k].getSource === 'function') out.winKeys.push(k); } catch (_) {}
  }
  // qgis-sel ソースの有無(maplibre)を kascMap 経由で確認
  try {
    const s = window.kascMap?.getSource?.('qgis-sel');
    out.selSrc = s ? (s._data?.features?.length ?? 'has-src') : 'nosrc';
  } catch (e) { out.selSrc = 'err:' + e; }
  return out;
});
console.log(JSON.stringify(info), 'errs:', errs.slice(0,3).join(' | '));
await page.screenshot({ path: process.env.TEMP + '/devin-live/' + engine + '-sel2.png' });
await browser.close();
