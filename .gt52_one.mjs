import { chromium } from "playwright";
const KASC = encodeURIComponent("http://127.0.0.1:8520/gt52/kasugai_canvas.kasc");
const browser = await chromium.launch({ channel: "chrome", headless: true, args: ["--use-angle=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
page.on("console", m => { if (m.type() !== "log") console.log("[c]", m.type(), m.text().slice(0, 250)); });
page.on("pageerror", e => console.log("[pageerror]", String(e).slice(0, 400)));
await page.goto(`http://127.0.0.1:8520/cesium/?kasc=${KASC}`, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForFunction(() => window.kasugaiApi, null, { timeout: 60000 });
await page.waitForTimeout(12000);
// DEM 中心 (138.8E, 35.45N) 真俯瞰 80km
await page.evaluate(() => window.kasugaiApi.flyTo({ latitude: 35.45, longitude: 138.8, height: 80000, pitch: -90 }, 0));
await page.waitForTimeout(10000);
await page.screenshot({ path: process.env.TEMP + "/gt52/overlay_terrain.png" });
await page.evaluate(() => {
  for (const l of window.kasugaiApi.listLayers())
    window.kasugaiApi.setLayerVisible(l.id, l.title.includes("素のtiles"));
});
await page.waitForTimeout(9000);
await page.screenshot({ path: process.env.TEMP + "/gt52/plain_tiles.png" });
await page.evaluate(() => {
  for (const l of window.kasugaiApi.listLayers())
    window.kasugaiApi.setLayerVisible(l.id, l.title.includes("overlay legacy"));
});
await page.waitForTimeout(9000);
await page.screenshot({ path: process.env.TEMP + "/gt52/overlay_legacy.png" });
console.log(JSON.stringify(await page.evaluate(() => ({ req: window.__tileReq || 0, errs: window.__tileErr }))));
await browser.close();
