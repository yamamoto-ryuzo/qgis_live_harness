// 常駐QGISインスタンスとのセッション管理。
//
// ensure: 応答するlive dirがあれば再利用。無ければdeployしてverify-in-qgis.ps1で
//         QGISを起動し、LiveDriverが応答するまで待つ。
//         → 呼ぶ側は常に「node scripts/qgis-session.mjs ensure」だけでよい。
//           2回目以降は既存インスタンスにアタッチするため起動コストは初回だけ。
//
// reload: deploy(-Copy)後、pyevalでプラグインをホットリロードしダイアログを開き直す。
//         QGIS再起動なしでコード変更を反映できる。
//
// 使い方:
//   node scripts/qgis-session.mjs ensure
//   node scripts/qgis-session.mjs reload [--no-deploy]

import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { LivePage, resolveLiveDirs } from "./live-drive.mjs";

const REPO = fileURLToPath(new URL("../", import.meta.url));
// QGIS上のプラグインID(deploy先ディレクトリ名)。独自名にする場合はここだけ変える
const PLUGIN_ID = JSON.parse(
  readFileSync(join(REPO, "plugin.config.json"), "utf8")
).id;
const LIVE_BASE = process.env.WEBENGINE_LIVE_DIR || join(REPO, "test-results", "live");
const DEPLOY_PS1 = join(REPO, "scripts", "deploy-plugin.ps1");
const QGIS_EXE = process.env.QGIS_EXE || "C:\\Program Files\\QGIS 4.0.1\\bin\\qgis-bin.exe";
const LOG_PATH = join(REPO, "test-results", "plugin_load.log");

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function deploy() {
  const r = spawnSync(
    "powershell",
    ["-ExecutionPolicy", "Bypass", "-File", DEPLOY_PS1, "-Copy"],
    { cwd: REPO, stdio: "inherit" }
  );
  if (r.status !== 0) throw new Error("deploy-plugin.ps1 failed");
}

// verify-in-qgis.ps1 と同等の環境変数でQGISを起動する。
// nodeのspawn(detached)経由でps1を直接実行するとQGISが起動しないため、
// powershell -Command + Start-Process で起動する(実機で動作確認済み)。
// Start-Processは子を即detachして返るためpowershell自体はすぐ終了する。
function launchQgis(liveBase) {
  const ps = [
    `$env:QTWEBENGINE_REMOTE_DEBUGGING='9222'`,
    `$env:QTWEBENGINE_CHROMIUM_FLAGS='--disable-gpu --no-sandbox --disable-gpu-compositing'`,
    `$env:WEBENGINE_AUTOOPEN='1'`,
    `$env:WEBENGINE_LIVE_DIR='${liveBase.replace(/'/g, "''")}'`,
    `$env:WEBENGINE_LOG_PATH='${LOG_PATH.replace(/'/g, "''")}'`,
    // リポジトリ側のbridge/uiを直接読むdevモード(devreloadが有効になる)
    `$env:WEBENGINE_DEV_SRC='${REPO.replace(/\\/g, "/").replace(/'/g, "''")}'`,
    `Start-Process -FilePath '${QGIS_EXE}'`,
  ].join("; ");
  spawnSync(
    "powershell",
    ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
    { cwd: REPO, stdio: "ignore", windowsHide: true }
  );
}

// 全live plugin dirに短時間プローブを打ち、応答したものを返す。
// pyevalでプローブする: evaluateはレンダラー(JS側)が飢餓していると応答しないが、
// pyevalはPython側(プラグインのQTimer)だけで完結するため、ドライバの生存確認に適する。
// ドライバが生きていればattach扱いにし、レンダラーの不調は呼び出し側の責務とする
// (reloadはviewを作り直すので飢餓したレンダラーも直せる)。
async function probeAll(liveBase) {
  const dirs = await resolveLiveDirs(liveBase);
  const live = [];
  for (const d of dirs) {
    const page = new LivePage(d.dir);
    // 過去セッションの古いresultsによる誤検知を防ぐため一度空にする
    try { await page.reset(); } catch {}
    try {
      await page.pyeval("1", { timeoutMs: 5000 });
      live.push(d);
    } catch {}
  }
  return live;
}

/**
 * 応答するlive plugin dirを全て返す。1つも無ければQGISを起動して待つ。
 * @returns {Promise<Array<{dir:string, pluginId:string|null}>>}
 */
export async function ensureQgis({ liveBase = LIVE_BASE, timeoutMs = 180000 } = {}) {
  const live = await probeAll(liveBase);
  if (live.length) return live;

  console.log("[ensure] no live driver; deploying plugins and launching QGIS...");
  deploy();
  launchQgis(liveBase);

  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    await sleep(2000);
    const found = await probeAll(liveBase);
    if (found.length) {
      console.log(
        `[ensure] live driver ready: ${found.map((d) => d.dir).join(", ")}`
      );
      return found;
    }
  }
  throw new Error(
    `[ensure] live driver did not respond within ${timeoutMs / 1000}s. ` +
      `Check test-results/plugin_load.log and QGIS startup.`
  );
}

// pyevalで実行するリロードコードを生成する。プラグイン配下のimportキャッシュを
// 掃除してからreloadPluginし、ダイアログを開き直す。
// プラグインが未ロードの場合(QGIS側で無効化等)はloadPlugin+startPluginに倒す。
const reloadCode = (pluginId) => `
import sys, qgis.utils
PLUGIN_ID = ${JSON.stringify(pluginId)}
for k in [k for k in list(sys.modules)
          if k == PLUGIN_ID or k.startswith(PLUGIN_ID + ".")]:
    sys.modules.pop(k, None)
if PLUGIN_ID in qgis.utils.plugins:
    qgis.utils.reloadPlugin(PLUGIN_ID)
else:
    qgis.utils.loadPlugin(PLUGIN_ID)
    qgis.utils.startPlugin(PLUGIN_ID)
qgis.utils.plugins[PLUGIN_ID].open_dialog()
result = {"loaded": PLUGIN_ID in qgis.utils.plugins,
          "plugins": sorted(qgis.utils.plugins.keys())}
`;

/**
 * deploy後、実行中のQGIS内で全プラグインをホットリロードする。
 * reloadPluginでプラグインインスタンスが作り直され、新しいview+LiveDriverが
 * 同じlive dir(PID不変)を使い始める。
 */
export async function reloadPlugin({ liveBase = LIVE_BASE, deploy: doDeploy = true } = {}) {
  if (doDeploy) {
    console.log("[reload] deploying plugins (-Copy)...");
    deploy();
  }
  const dirs = await ensureQgis({ liveBase });
  const results = [];
  for (const d of dirs) {
    const id = d.pluginId || PLUGIN_ID;
    const page = new LivePage(d.dir);
    const res = await page.pyeval(reloadCode(id));
    console.log(`[reload] ${id}: ${JSON.stringify(res)}`);
    // 新しいviewがindex.htmlを読み込み終わるまで待つ。
    // reload直後は旧viewが破棄中でeval timeoutすることがあるのでwaitForで吸収する。
    await page.waitFor('[data-testid="layer-list"]', 60000);
    console.log(`[reload] ${id}: dialog re-opened and UI ready`);
    results.push(res);
  }
  return results;
}

/**
 * リポジトリ側のbridge/uiを再読み込みする。deployもreloadPluginも不要。
 * プラグイン本体側(main_plugin.py, live_driver.py等)を触った時は live:reload を使う。
 */
export async function devReload({ liveBase = LIVE_BASE } = {}) {
  const dirs = await ensureQgis({ liveBase });
  for (const d of dirs) {
    const page = new LivePage(d.dir);
    await page.devreload();
    await page.waitFor('[data-testid="layer-list"]', 60000);
    console.log(`[devreload] ${d.pluginId || "?"}: repo-side bridge/ui reloaded`);
  }
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const cmd = process.argv[2];
  try {
    if (cmd === "ensure") {
      const dirs = await ensureQgis();
      for (const d of dirs) console.log(`live dir: ${d.dir} (${d.pluginId})`);
    } else if (cmd === "reload") {
      await reloadPlugin({ deploy: !process.argv.includes("--no-deploy") });
    } else if (cmd === "devreload") {
      await devReload();
    } else {
      console.log("usage: node scripts/qgis-session.mjs <ensure|reload [--no-deploy]|devreload>");
      process.exit(cmd ? 1 : 0);
    }
  } catch (e) {
    console.error(e.message || e);
    process.exit(1);
  }
}
