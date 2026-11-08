import { chromium } from "playwright";
const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await browser.newPage();
await page.goto("http://127.0.0.1:8520/gt52/blank.html", { waitUntil: "domcontentloaded", timeout: 60000 });
const r = await page.evaluate(async () => {
  const mod = await import("/cesium/geotiff-layer.js");
  const Cesium = await import("https://cdn.jsdelivr.net/npm/cesium@1.133.1/+esm");
  const item = { title: "dem", url: "http://127.0.0.1:8520/gt52/DATA/dem.tif",
    colormap: "terrain", hillshade: { az: 315, el: 45, z: 2 }, nodata: -9999, gtMode: "tiles" };
  const gt = await mod.resolveGeoTiffItem(item, item.url);
  const provider = mod.createGeoTiffImageryProvider(Cesium, item, gt);
  const out = { mode: gt.mode, rect: provider.rectangle, maxLevel: provider.maximumLevel };
  // DEM bbox 内のタイルを level 6-9 で探して呼ぶ
  const samples = [];
  for (let level = 6; level <= 9 && samples.length < 3; level++) {
    const nx = provider.tilingScheme.getNumberOfXTilesAtLevel(level);
    const ny = provider.tilingScheme.getNumberOfYTilesAtLevel(level);
    for (let x = 0; x < nx && samples.length < 3; x++) {
      for (let y = 0; y < ny && samples.length < 3; y++) {
        const rect = provider.tilingScheme.tileXYToRectangle(x, y, level);
        if (!Cesium.Rectangle.intersection(rect, provider.rectangle)) continue;
        const cv = await provider.requestImage(x, y, level);
        const d = cv.getContext("2d").getImageData(0, 0, 256, 256).data;
        let opaque = 0, sum = [0, 0, 0];
        for (let i = 0; i < d.length; i += 4) { if (d[i + 3] > 0) { opaque++; sum[0] += d[i]; sum[1] += d[i + 1]; sum[2] += d[i + 2]; } }
        samples.push({ level, x, y, opaque, avg: opaque ? sum.map(v => Math.round(v / opaque)) : null });
      }
    }
  }
  out.tiles = samples;
  return out;
});
console.log(JSON.stringify(r, null, 1));
await browser.close();
