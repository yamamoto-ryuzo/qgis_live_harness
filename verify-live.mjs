// QGIS live 双方向連携のブラウザ検証
import { chromium } from 'playwright';

const KASC = 'http://127.0.0.1:8089/export-data/kasugai_canvas.kasc';
const base = 'http://127.0.0.1:8899';

async function run(engine, extra = '') {
  const url = `${base}/${engine}/?kasc=${encodeURIComponent(KASC)}${extra}`;
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage();
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(String(e)));
  const t0 = Date.now();
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  // live セッション + レンダリングを待つ
  await page.waitForTimeout(6000);
  const st = await page.evaluate(async () => {
    const mod = await import('/shared/live.js');
    return { status: mod.liveStatus() };
  }).catch(e => ({ evalError: String(e) }));
  // 選択ハイライト(qgis-sel source)の地物数
  let selCount = null;
  if (engine === 'maplibre') {
    selCount = await page.evaluate(() => {
      try { const s = window.map?.getSource?.('qgis-sel'); const d = s?._data; return d?.features?.length ?? null; }
      catch (e) { return 'err:' + e; }
    }).catch(() => null);
    // window.map が無ければモジュール経由ではなく DOM から推定不可 → API で
    if (selCount == null) {
      selCount = await page.evaluate(async () => {
        try {
          const maps = Object.values(window).find(v => v && v.getSource && v.getZoom);
          const s = maps?.getSource?.('qgis-sel');
          return s?._data?.features?.length ?? 'nosrc';
        } catch (e) { return 'err:' + e; }
      }).catch(e => 'evalErr:' + e);
    }
  }
  const view = await page.evaluate(() => {
    const m = Object.values(window).find(v => v && v.getCenter && v.getZoom);
    if (!m) return null;
    const c = m.getCenter(); return { lng: +c.lng.toFixed(4), lat: +c.lat.toFixed(4), z: +m.getZoom().toFixed(2) };
  }).catch(() => null);
  console.log(JSON.stringify({ engine, ms: Date.now() - t0, live: st, selCount, view, errors: errors.slice(0, 5) }));
  await browser.close();
}

const engine = process.argv[2] || 'maplibre';
const extra = process.argv[3] || '';
await run(engine, extra);
