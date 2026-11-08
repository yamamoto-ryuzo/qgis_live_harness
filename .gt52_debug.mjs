import { chromium } from "playwright";
const KASC = encodeURIComponent("http://127.0.0.1:8520/gt52/kasugai_canvas.kasc");
const browser = await chromium.launch({ channel: "chrome", headless: true, args: ["--use-angle=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"] });
const page = await browser.newPage();
page.on("pageerror", e => console.log("[pageerror]", String(e).slice(0, 300)));
await page.goto(`http://127.0.0.1:8520/cesium/?kasc=${KASC}`, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForFunction(() => window.kasugaiApi, null, { timeout: 60000 });
await page.waitForTimeout(12000);
const info = await page.evaluate(() => {
  const mod = window.__gtDebug || {};
  const items = (window.__layers || []).map(i => i);
  return { has: Object.keys(window).filter(k => /gt|layer/i.test(k)).slice(0, 20) };
});
// item._gt は内部変数のため、layery一覧 API から item を辿れない→ コンソール評価で確認
const r = await page.evaluate(() => {
  // kasugaiApi.listLayers が item 参照を返すか確認
  const l = (window.kasugaiApi.listLayers() || []).find(x => /疑似カラー/.test(x.title));
  const g = l?._gt || l?.gt || null;
  if (!g) return { found: !!l, keys: l ? Object.keys(l) : null, raw: l };
  return { found: true, mode: g.mode, crs: g.crs, nodata: g.nodata,
    render: g.render ? { band: g.render.band, lut: !!g.render.lut, lut0: g.render.lut ? Array.from(g.render.lut.slice(0,8)) : null, min: g.render.min, max: g.render.max, stats: g.render.stats, hillshade: g.render.hillshade } : null };
});
console.log(JSON.stringify(r, null, 1));
await browser.close();
