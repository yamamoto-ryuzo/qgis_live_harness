import { chromium } from 'playwright';

const URL = 'http://127.0.0.1:8899/cesium/';
let browser;
for (const ch of ['chrome', 'msedge']) {
  try { browser = await chromium.launch({ channel: ch, headless: true, args: ['--use-gl=angle', '--enable-webgl', '--ignore-gpu-blocklist'] }); console.log('launched:', ch); break; }
  catch (e) { console.log('no channel', ch, e.message.split('\n')[0]); }
}
if (!browser) browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
page.on('console', m => { if (m.type() === 'error') console.log('[console.error]', m.text().slice(0, 200)); });
await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });

// kasugaiApi と viewer 準備待ち
await page.waitForFunction(() => window.kasugaiApi && window.Cesium && document.querySelector('#cesiumContainer'), { timeout: 60000 });
await page.waitForFunction(() => window.kasugaiApi.lineOfSight && typeof window.kasugaiApi.lineOfSight === 'function', { timeout: 30000 });

// UI パネルの存在確認
const ui = await page.evaluate(() => ({
  losBtn: !!document.querySelector('#tool-los'),
  obsH: document.querySelector('#los-observer-h')?.value,
  tgtH: document.querySelector('#los-target-h')?.value,
  resultEl: !!document.querySelector('#tools-los-result'),
  losTab: !!document.querySelector('[data-settings-panel="tools-los-panel"]'),
}));
console.log('UI:', JSON.stringify(ui));

// ケース1: 平地相当の2点（地形ソースに関わらず可視になるはず）
// 霞ヶ浦周辺の平坦地 (茨城) — 短距離
const r1 = await page.evaluate(async () => {
  const res = await window.kasugaiApi.lineOfSight({ lng: 140.40, lat: 36.10 }, { lng: 140.41, lat: 36.10 }, { observerHeight: 1.5, targetHeight: 1.5 });
  return res;
});
console.log('LOS flat:', JSON.stringify(r1));
const t1 = await page.evaluate(() => document.querySelector('#tools-los-result')?.textContent);
console.log('result text:', t1);

// geo-tools DataSource のエンティティ確認
const ents = await page.evaluate(() => {
  const ds = window.__viewer?.dataSources?._dataSources?.find(d => d.name === 'geo-tools')
    || (window.Cesium && window.viewer ? null : null);
  return null;
});
// viewer 参照を探す
const vref = await page.evaluate(() => {
  // window に公開されている viewer を探す
  for (const k of Object.keys(window)) { if (window[k]?.dataSources?.length !== undefined && window[k]?.scene?.globe) return k; }
  return null;
});
console.log('viewer global:', vref);
if (vref) {
  const info = await page.evaluate((vk) => {
    const v = window[vk];
    const ds = [...v.dataSources._dataSources].find(d => d.name === 'geo-tools');
    return ds ? { name: ds.name, entities: ds.entities.values.length, kinds: ds.entities.values.map(e => e.polyline ? 'line' : e.point ? 'point' : e.label ? 'label' : 'other') } : null;
  }, vref);
  console.log('geo-tools ds:', JSON.stringify(info));
}

// ケース2: 遮蔽ケース（地形考慮が効くか） — 富士山を挟む2点
// 山頂(3776m)を挟んで低地同士 → 地形プロバイダ or GSI API が効けば blocked
const r2 = await page.evaluate(async () => {
  try {
    const res = await window.kasugaiApi.lineOfSight(
      { lng: 138.50, lat: 35.30 }, { lng: 138.95, lat: 35.30 },
      { observerHeight: 10, targetHeight: 10 });
    return res;
  } catch (e) { return { error: String(e) }; }
});
console.log('LOS fuji:', JSON.stringify(r2));
const t2 = await page.evaluate(() => document.querySelector('#tools-los-result')?.textContent);
console.log('result text2:', t2);

await browser.close();
