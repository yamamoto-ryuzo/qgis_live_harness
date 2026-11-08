import { chromium } from "playwright";
const KASC = encodeURIComponent("http://127.0.0.1:8520/gt52/kasugai_canvas.kasc");
const browser = await chromium.launch({ channel: "chrome", headless: true, args: ["--use-angle=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
page.on("pageerror", e => console.log("[pageerror]", String(e).slice(0, 300)));
await page.goto(`http://127.0.0.1:8520/cesium/?kasc=${KASC}`, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForFunction(() => window.kasugaiApi, null, { timeout: 60000 });
await page.waitForTimeout(12000);
await page.evaluate(() => window.kasugaiApi.flyTo({ latitude: 35.45, longitude: 138.8, height: 90000, pitch: -90 }, 0));
await page.waitForTimeout(9000);
await page.screenshot({ path: process.env.TEMP + "/gt52/1_terrain_hillshade.png" });
async function only(sub, file, zoom) {
  await page.evaluate((s) => {
    for (const l of window.kasugaiApi.listLayers())
      window.kasugaiApi.setLayerVisible(l.id, l.title.includes(s));
  }, sub);
  if (zoom) await page.evaluate((z) => window.kasugaiApi.flyTo(z, 0), zoom);
  await page.waitForTimeout(8000);
  await page.screenshot({ path: `${process.env.TEMP}/gt52/${file}` });
  console.log("shot:", file);
}
await only("viridis", "2_viridis.png");
await only("陰影のみ", "3_hillshade.png");
await only("明示範囲", "4_hexramp.png");
await only("従来", "5_legacy.png");
// RGB 回帰: gt_test4326.tif の bbox へ（DATA内のRGB tif。位置は4326矩形）
await only("RGB写真", "6_rgb.png", { latitude: 35.5, longitude: 139.0, height: 120000, pitch: -90 });
await browser.close();
console.log("DONE");
