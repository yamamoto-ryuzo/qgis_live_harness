import { chromium } from 'playwright';
const KASC = 'http://127.0.0.1:8089/export-data/kasugai_canvas.kasc';
const browser = await chromium.launch({ channel: 'chrome', headless: true });

// 1) OpenLayers: live active + 地物クリック → QGIS 側選択へ逆通知
{
  const page = await browser.newPage({ viewport: { width: 1200, height: 800 } });
  await page.goto(`http://127.0.0.1:8899/openlayers/?kasc=${encodeURIComponent(KASC)}`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(7000);
  const st = await page.evaluate(async () => (await import('/shared/live.js')).liveStatus());
  // 画面中央のサンプル地物群(渋谷周辺のマーカー)をクリック
  await page.mouse.click(600, 430);
  await page.waitForTimeout(1200);
  console.log('openlayers:', JSON.stringify(st));
  await page.close();
}
// 2) Cesium: follow で pitch が保持されるか(-90に固定されない)
{
  const page = await browser.newPage({ viewport: { width: 1200, height: 800 } });
  await page.goto(`http://127.0.0.1:8899/cesium/?kasc=${encodeURIComponent(KASC)}&follow=1`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(8000);
  const pitch = await page.evaluate(() => {
    const v = window.kascView || window.viewer;
    try { return +(v.camera.pitch * 180 / Math.PI).toFixed(1); } catch (e) { return 'err:' + e; }
  });
  const st = await page.evaluate(async () => (await import('/shared/live.js')).liveStatus());
  console.log('cesium pitch:', pitch, 'live:', JSON.stringify(st));
  await page.close();
}
// 3) gsimaps: live セッション有効化
{
  const page = await browser.newPage({ viewport: { width: 1200, height: 800 } });
  const errs = [];
  page.on('pageerror', e => errs.push(String(e)));
  await page.goto(`http://127.0.0.1:8899/gsimaps/?kasc=${encodeURIComponent(KASC)}`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(9000);
  const st = await page.evaluate(async () => (await import('/shared/live.js')).liveStatus()).catch(e => ({ err: String(e) }));
  console.log('gsimaps live:', JSON.stringify(st), 'errs:', errs.slice(0, 3).join('|'));
  await page.close();
}
await browser.close();
