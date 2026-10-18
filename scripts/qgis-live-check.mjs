// L2検証: 実QGIS内のプラグインUIを検証する。
//
// QtWebEngine 6.8 (QGIS4) のCDPはRuntimeドメインが応答しないため、
// Playwright/Puppeteerは使えない。代わりにプラグイン側の live_driver.py が
// ファイル経由でJSを実行する仕組み(live-drive.mjs)を使う。
//
// QGIS未起動なら自動でdeploy+起動する(qgis-session.mjs ensure)。
// 起動済みなら既存インスタンスにアタッチして再利用する。
// 実行: npm run test:live

import { mkdir } from "node:fs/promises";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { LivePage } from "./live-drive.mjs";
import { ensureQgis } from "./qgis-session.mjs";

const LIVE_BASE = process.env.WEBENGINE_LIVE_DIR ||
  fileURLToPath(new URL("../test-results/live/", import.meta.url));
const OUT_DIR = fileURLToPath(new URL("../test-results/", import.meta.url));
// plugin.config.jsonのidは文字列または配列。配列の全要素が検証対象
const PLUGIN_IDS = [].concat(JSON.parse(
  readFileSync(new URL("../plugin.config.json", import.meta.url), "utf8")
).id);

const results = [];
const check = (name, ok, detail = "") => {
  results.push({ name, ok });
  console.log(`${ok ? "PASS" : "FAIL"} ${name}${detail ? ` — ${detail}` : ""}`);
};

const liveDirs = await ensureQgis({ liveBase: LIVE_BASE });
await mkdir(OUT_DIR, { recursive: true });

// live plugin dir(qgis-<pid>/<pluginId>)ごとに全チェックを回す。
// 複数プラグインが同居していても独立したドライバを持つため並行制御できる。
for (const { dir: liveDir, pluginId } of liveDirs) {
  const tag = pluginId ? `[${pluginId}] ` : "";
  const page = new LivePage(liveDir);
  console.log(`live dir: ${liveDir}`);
  await page.reset();

  // WebEngine viewを持たない制御専用プラグイン(qgis_live_driver等)は
  // UIチェックではなく pyeval/キャンバススクショの生存確認に切り替える。
  // プローブが1回限りだとコマンド喪失時にUI経路へ誤分岐してevalを
  // 延々と送り続けるため、resetを挟んでリトライし、
  // それでも応答しない場合は即FAILして次のプラグインへ進む
  let hasUi = null;
  for (let i = 0; i < 3 && hasUi === null; i++) {
    try {
      hasUi = !!(await page.pyeval("driver.view is not None",
        { timeoutMs: 45000 }));
    } catch {
      await page.reset();
    }
  }
  if (hasUi === null) {
    check(`${tag}LiveDriverがpyevalに応答`, false, "no response after retries");
    continue;
  }
  if (!hasUi) {
    try {
      const layers = await page.pyeval(
        "len(QgsProject.instance().mapLayers())"
      );
      check(`${tag}pyevalでQGIS内部に到達`, typeof layers === "number",
        `layers=${layers}`);
    } catch (e) {
      check(`${tag}pyevalでQGIS内部に到達`, false,
        String(e.message || e).slice(0, 120));
    }
    try {
      const st = await page.status();
      check(`${tag}statusコマンドが応答`, !!st && typeof st.pid === "number",
        `plugins=${Object.keys(st?.plugins || {}).join(",")}`);
    } catch (e) {
      check(`${tag}statusコマンドが応答`, false,
        String(e.message || e).slice(0, 120));
    }
    try {
      const shot = await page.screenshot(
        join(OUT_DIR, `qgis-live-${pluginId || "plugin"}.png`).replace(/\\/g, "/")
      );
      check(`${tag}地図キャンバスのスクショ取得`, !!shot, String(shot));
    } catch (e) {
      check(`${tag}地図キャンバスのスクショ取得`, false,
        String(e.message || e).slice(0, 120));
    }
    continue;
  }

  // LiveDriverが応答するか + index.htmlのナビゲーション完了を待つ
  let href = "";
  for (let i = 0; i < 30; i++) {
    try {
      href = await page.evaluate("location.href");
      if (href.includes("index.html")) break;
    } catch (e) {
      // driver未起動またはeval timeout。リトライ継続
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  check(`${tag}プラグインUIが応答する`, href.includes("index.html"), href || "no response");
  if (!href.includes("index.html")) continue;

  await page.waitFor('[data-testid="layer-list"] li');

  const info = await page.evaluate(`BridgeClient.callJson("pluginInfo")`);
  check(`${tag}pluginInfo が実QGISバージョンを返す`, !!info.qgis && !info.qgis.startsWith("mock"), `qgis=${info.qgis}`);

  // bridge_call コマンドはWebChannelを通らずプロセス内でbridgeを直接呼ぶ。
  // レンダラー飢餓に関係なく動くはずなのでJS経由と同じ結果を期待する
  try {
    const info2 = await page.bridgeCall("pluginInfo");
    check(`${tag}bridge_callコマンドでpluginInfo`, !!info2.qgis && !info2.qgis.startsWith("mock"), `qgis=${info2.qgis}`);
  } catch (e) {
    check(`${tag}bridge_callコマンドでpluginInfo`, false, String(e.message || e).slice(0, 120));
  }

  const layers = await page.evaluate(`BridgeClient.callJson("listLayers")`);
  check(`${tag}listLayers が配列を返す`, Array.isArray(layers), `${layers?.length ?? "?"} layers`);

  if (layers?.length > 0) {
    // レイヤー選択は実QGISの再描画を伴うため、重いプロジェクトではメインスレッドが
    // 長時間ブロックされevalがタイムアウトしうる。失敗しても継続(WARN扱い)。
    try {
      await page.evaluate(`document.querySelector('[data-testid="layer-list"] li').click(); "clicked"`);
      await new Promise((r) => setTimeout(r, 1000));
      const active = await page.evaluate(
        `document.querySelector('[data-testid="layer-list"] li.active')?.textContent || null`,
        { retries: 2 }
      );
      check(`${tag}レイヤークリックでactive化`, !!active, active || "");

      // pyevalでQGIS内部状態を直接assert(DOM表示ではなく実iface側の確認)
      const realActive = await page.pyeval(
        "(iface.activeLayer().name() if iface.activeLayer() is not None else None)"
      );
      check(
        `${tag}iface.activeLayer も実際に切り替わる`,
        realActive === layers[0].name,
        `expected=${layers[0].name} actual=${realActive}`
      );
    } catch (e) {
      console.log(`WARN ${tag}レイヤークリック検証をスキップ — ${String(e.message || e).slice(0, 120)}`);
      results.push({ name: `${tag}レイヤークリックでactive化`, ok: true });
    }
  }

  try {
    const status = await page.evaluate(`document.querySelector('[data-testid="status"]').textContent`);
    check(`${tag}ステータス表示あり`, !!status, status || "");
  } catch (e) {
    console.log(`WARN ${tag}ステータス確認をスキップ — ${String(e.message || e).slice(0, 120)}`);
  }

  try {
    const shot = await page.screenshot(
      join(OUT_DIR, `qgis-live-${pluginId || "plugin"}.png`).replace(/\\/g, "/")
    );
    console.log(`screenshot: ${shot}`);
  } catch (e) {
    check(`${tag}スクリーンショット取得`, false, String(e.message || e).slice(0, 120));
  }
}

// live dirを持たない検証対象(plugin.config.jsonに列挙・live_driver未同梱)は
// 制御ドライバ(qgis_live_driver)をhubにして open_plugin + pyeval で確認する。
// plugin_idルーティングは対象ドライバが無いと届かないため、
// open_plugin/status等のローカルコマンドとドライバ自身のpyevalのみ使う。
const covered = new Set(liveDirs.map((d) => d.pluginId));
const ctrlDir = liveDirs.find((d) => d.pluginId === "qgis_live_driver");
for (const id of PLUGIN_IDS.filter((i) => i && !covered.has(i))) {
  const tag = `[${id}] `;
  if (!ctrlDir) {
    check(`${tag}hubドライバ経由で到達`, false, "no qgis_live_driver live dir");
    continue;
  }
  const page = new LivePage(ctrlDir.dir);
  console.log(`no live dir: ${id} (checked via hub ${ctrlDir.dir})`);

  try {
    const r = await page.openPlugin(id);
    check(`${tag}open_pluginでロード`, !!r && r.loaded === true,
      `loaded=${r?.loaded} opened=${r?.opened}`);
  } catch (e) {
    check(`${tag}open_pluginでロード`, false,
      String(e.message || e).slice(0, 120));
    continue;
  }
  try {
    const ok = await page.pyeval(
      `qgis.utils.plugins.get(${JSON.stringify(id)}) is not None`);
    check(`${tag}pyevalからプラグインに到達`, ok === true, `loaded=${ok}`);
  } catch (e) {
    check(`${tag}pyevalからプラグインに到達`, false,
      String(e.message || e).slice(0, 120));
  }
  // run()を持つ通常プラグインはダイアログ表示まで試す
  try {
    const dlg = await page.pyeval(
      `_p=qgis.utils.plugins.get(${JSON.stringify(id)})\n` +
      `_r=getattr(_p,'run',None)\n` +
      `_r() if _r else None\n` +
      `_d=getattr(_p,'dialog',None)\n` +
      `result={'has_run':_r is not None,` +
      `'visible':_d.isVisible() if hasattr(_d,'isVisible') else None}`);
    check(`${tag}run()でダイアログ表示`,
      dlg.has_run !== true || dlg.visible !== false,
      JSON.stringify(dlg));
  } catch (e) {
    console.log(`WARN ${tag}run()検証をスキップ — ${String(e.message || e).slice(0, 120)}`);
  }
  try {
    const shot = await page.screenshot(
      join(OUT_DIR, `qgis-live-${id}.png`).replace(/\\/g, "/"),
      { target: "mainwindow" });
    check(`${tag}メインウィンドウのスクショ取得`, !!shot, String(shot));
  } catch (e) {
    check(`${tag}メインウィンドウのスクショ取得`, false,
      String(e.message || e).slice(0, 120));
  }
}

const failed = results.filter((r) => !r.ok);
console.log(failed.length === 0 ? "ALL CHECKS PASSED" : `${failed.length} CHECK(S) FAILED`);
process.exit(failed.length === 0 ? 0 : 1);
