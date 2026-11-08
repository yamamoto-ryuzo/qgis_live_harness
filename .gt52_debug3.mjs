import { chromium } from "playwright";
const KASC = encodeURIComponent("http://127.0.0.1:8520/gt52/kasugai_canvas.kasc");
const browser = await chromium.launch({ channel: "chrome", headless: true, args: ["--use-angle=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
await page.goto(`http://127.0.0.1:8520/cesium/?kasc=${KASC}`, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForFunction(() => window.kasugaiApi && window.__gtItems?.length, null, { timeout: 60000 });
await page.waitForTimeout(8000);
console.log(JSON.stringify(await page.evaluate(() => window.__gtItems), null, 1));
// DEM 領域を実際にどう描いたか: タイル imagery か確認のため DOM の canvas ではなく
// viewer へのアクセスが無いのでスクリーンショット色を直接サンプル
await page.screenshot({ path: process.env.TEMP + "/gt52/dbg_main.png" });
await browser.close();
