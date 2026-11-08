import { chromium } from "playwright";
const url = "https://yamamoto-ryuzo.github.io/kasugai-canvas-web/unstable/cesium/?kasc=" +
  encodeURIComponent("https://yamamoto-ryuzo.github.io/kasugai_canvas_webGIS/sample_qgis/kasugai_canvas.kasc");
const browser = await chromium.launch({ channel: "chrome", headless: true, args: ["--use-angle=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
page.on("pageerror", e => console.log("[pageerror]", String(e).slice(0, 200)));
await page.goto(url, { waitUntil: "domcontentloaded", timeout: 90000 });
await page.waitForFunction(() => window.kasugaiApi, null, { timeout: 90000 });
await page.waitForTimeout(20000);
await page.screenshot({ path: process.env.TEMP + "/i60_cdn.png" });
console.log(JSON.stringify(await page.evaluate(() => window.kasugaiApi.getCamera?.() || null)));
await browser.close();
