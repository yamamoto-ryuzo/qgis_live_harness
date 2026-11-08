import { chromium } from "playwright";
const KASC = encodeURIComponent("http://127.0.0.1:8520/op58/kasugai_canvas.kasc");
const browser = await chromium.launch({ channel: "chrome", headless: true, args: ["--use-angle=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
await page.goto(`http://127.0.0.1:8520/cesium/?kasc=${KASC}`, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForFunction(() => window.kasugaiApi, null, { timeout: 60000 });
await page.waitForTimeout(12000);
await page.screenshot({ path: process.env.TEMP + "/op58/opacity03.png" });
await page.evaluate(() => {
  for (const l of window.kasugaiApi.listLayers())
    window.kasugaiApi.setLayerVisible(l.id, l.title.includes("不透明"));
});
await page.waitForTimeout(8000);
await page.screenshot({ path: process.env.TEMP + "/op58/opacity10.png" });
await browser.close();
