import { chromium } from "playwright";
const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await browser.newPage();
page.on("console", m => console.log("[c]", m.text().slice(0, 300)));
page.on("pageerror", e => console.log("[pageerror]", String(e).slice(0, 400)));
await page.goto("http://127.0.0.1:8520/cesium/index.html", { waitUntil: "domcontentloaded", timeout: 60000 });
const r = await page.evaluate(async () => {
  const mod = await import("/cesium/geotiff-layer.js");
  const lut = mod.compileColorRamp("terrain", {});
  const lutHex = mod.compileColorRamp("#0000cc,#00cc00,#ffff00,#ff0000", {});
  const lutVal = mod.compileColorRamp("0:#0000cc,2000:#ff0000", { min: 0, max: 2000 });
  // GeoTIFF を直接開いて render 経路を単体実行
  const GT = await import("https://cdn.jsdelivr.net/npm/geotiff@2.1.3/+esm");
  const tiff = await GT.fromUrl("http://127.0.0.1:8520/gt52/DATA/dem.tif");
  const img = await tiff.getImage(0);
  const item = { bands: [1], colormap: "terrain", hillshade: { az: 315, el: 45, z: 2 }, nodata: -9999, stretch: "minmax" };
  const gt = { images: [{ index: 0, image: img, w: img.getWidth(), h: img.getHeight(), resX: 1 }], base: img, crs: { code: 4326 }, bboxNative: img.getBoundingBox(), nodata: null };
  // buildRenderOpts は内部関数のため resolveGeoTiffItem 経由で試す
  item.gtMode = "tiles";
  const gti = await mod.resolveGeoTiffItem(item, "http://127.0.0.1:8520/gt52/DATA/dem.tif");
  const canvas = await mod.readGeoTiffToCanvas(img, { outW: 200, outH: 200, render: { ...gti.render, cellsize: [50, 50] } });
  const ctx = canvas.getContext("2d");
  const d = ctx.getImageData(0, 0, 200, 200).data;
  const colors = new Set();
  for (let i = 0; i < d.length; i += 400) colors.add(`${d[i]},${d[i+1]},${d[i+2]},${d[i+3]}`);
  return { lutLen: lut?.length, lut0: lut ? Array.from(lut.slice(0, 8)) : null,
           hex0: lutHex ? Array.from(lutHex.slice(0, 8)) : null, hexLast: lutHex ? Array.from(lutHex.slice(-4)) : null,
           valMid: lutVal ? Array.from(lutVal.slice(127 * 4, 127 * 4 + 4)) : null,
           mode: gti.mode, stats: gti.render?.stats, renderLut: !!gti.render?.lut,
           samples: [...colors].slice(0, 12) };
});
console.log(JSON.stringify(r, null, 1));
await browser.close();
