// 常駐QGISインスタンスとのセッション管理。
//
// ensure: 応答するlive dirがあれば再利用。無ければQGISを起動し、
//         LiveDriverが応答するまで待つ。
//         → 呼ぶ側は常に「node scripts/qgis-session.mjs ensure」だけでよい。
//           2回目以降は既存インスタンスにアタッチするため起動コストは初回だけ。
//         ※プラグインの配置(deploy-plugin.ps1)は一切呼ばない。
//           プラグインフォルダへの書込みは全てUI操作(deploy/deploy:use/
//           deploy:install)という安全性の最強ルール。未配置なら
//           LiveDriverが現れず、タイムアウト時に手動deployを案内する。
//
// reload: pyevalでプラグインをホットリロードしダイアログを開き直す。
//         junction配置(dev)ならrepoコードがそのまま反映される。
//         QGIS再起動なしでコード変更を反映できる。
//
// 使い方:
//   node scripts/qgis-session.mjs ensure
//   node scripts/qgis-session.mjs reload

import { spawnSync } from "node:child_process";
import {
  existsSync, lstatSync, readdirSync, readFileSync, realpathSync,
} from "node:fs";
import { fileURLToPath } from "node:url";
import { basename, dirname, join } from "node:path";
import { LivePage, resolveLiveDirs } from "./live-drive.mjs";

const REPO = fileURLToPath(new URL("../", import.meta.url));
// QGIS上のプラグインID(deploy先ディレクトリ名)。plugin.config.jsonのidは
// 文字列または配列(先頭=主開発対象、全要素=reload/テスト対象)
const PLUGIN_IDS = [].concat(JSON.parse(
  readFileSync(join(REPO, "plugin.config.json"), "utf8")
).id);
const LIVE_BASE = process.env.WEBENGINE_LIVE_DIR || join(REPO, "test-results", "live");
// QGIS_EXE env > C:\Program Files\QGIS<ver>\bin\qgis-bin.exe(最新版優先)
function resolveQgisExe() {
  if (process.env.QGIS_EXE) return process.env.QGIS_EXE;
  const root = "C:\\Program Files";
  try {
    const cands = readdirSync(root)
      .filter((d) => /^QGIS/i.test(d))
      .map((d) => join(root, d, "bin", "qgis-bin.exe"))
      .filter((p) => existsSync(p))
      .sort()
      .reverse();
    if (cands.length) return cands[0];
  } catch {}
  return "C:\\Program Files\\QGIS 4.0.1\\bin\\qgis-bin.exe";
}
const QGIS_EXE = resolveQgisExe();
const LOG_PATH = join(REPO, "test-results", "plugin_load.log");

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// deployモード: "dev"=junction(repo優先) / "use"=実体dir(退避版の復元) /
//   "mixed"=混在 / null=未配置
// 配置実態を優先し、未配置の時だけ宣言マーカー(deploy-plugin.ps1 が書く)で
// 補う。実際に動くコードを決めるのは配置物なので、古い宣言で実態を
// 上書きしない。
// この判定は読取専用: launchQgis が DEV_SRC を立てるかの分岐にのみ使う
const QGIS_USER_ROOT =
  process.env.QGIS_USER_ROOT ||
  join(process.env.APPDATA || "", "QGIS", "QGIS4");
function isJunctionDeployed(p) {
  // junctionをisSymbolicLinkで拾えないNode版があるため、
  // realpathがqgis-plugin配下に解決されるかでも判定する
  try {
    if (lstatSync(p).isSymbolicLink()) return true;
  } catch {}
  try {
    return basename(dirname(realpathSync(p))) === "qgis-plugin";
  } catch {}
  return false;
}
export function currentDeployMode() {
  try {
    const ini = readFileSync(
      join(QGIS_USER_ROOT, "profiles", "profiles.ini"),
      "utf8"
    );
    const profile = (ini.match(/lastProfile=(.+)/)?.[1] || "default").trim();
    const profileRoot = join(QGIS_USER_ROOT, "profiles", profile);
    const pluginsDir = join(profileRoot, "python", "plugins");
    const ids = readdirSync(join(REPO, "qgis-plugin")).filter((d) =>
      existsSync(join(REPO, "qgis-plugin", d, "metadata.txt"))
    );
    const forms = new Set();
    for (const id of ids) {
      const p = join(pluginsDir, id);
      if (!existsSync(p)) continue;
      forms.add(isJunctionDeployed(p) ? "junction" : "dir");
    }
    if (forms.has("junction") && forms.has("dir")) return "mixed";
    if (forms.has("junction")) return "dev";
    if (forms.size) return "use";
    // 未配置: 宣言markerで補う(use宣言=自動deploy抑制の意図を残す)
    const marker = join(profileRoot, "qgis_live_mode.json");
    if (existsSync(marker)) {
      // PowerShellのSet-Content -Encoding UTF8はBOM付きなので剥がす
      const mode = JSON.parse(
        readFileSync(marker, "utf8").replace(/^﻿/, "")
      ).mode;
      if (mode === "dev" || mode === "use") return mode;
    }
    return null;
  } catch {
    return null;
  }
}

// ※deploy-plugin.ps1 は一切呼ばない。プラグインフォルダへの書込みは
//   全てUI操作(npm run deploy / deploy:use / deploy:install)のみ。
//   自動経路がdeployを呼ぶと、気づかないうちにモード遷移・利用版の
//   破壊につながるため、コードとして経路自体を持たない。

// verify-in-qgis.ps1 と同等の環境変数でQGISを起動する。
// nodeのspawn(detached)経由でps1を直接実行するとQGISが起動しないため、
// powershell -Command + Start-Process で起動する(実機で動作確認済み)。
// Start-Processは子を即detachして返るためpowershell自体はすぐ終了する。
function launchQgis(liveBase) {
  // WEBENGINE_DEV_SRC は dev モード確定時のみ立てる(開発専用機構)。
  // use/未配置では配置済み実体dirがそのまま動き、repo側コードは載せない
  const devMode = currentDeployMode() === "dev";
  const ps = [
    `$env:QTWEBENGINE_REMOTE_DEBUGGING='9222'`,
    `$env:QTWEBENGINE_CHROMIUM_FLAGS='--disable-gpu --no-sandbox --disable-gpu-compositing'`,
    `$env:WEBENGINE_AUTOOPEN='1'`,
    `$env:WEBENGINE_LIVE_DIR='${liveBase.replace(/'/g, "''")}'`,
    `$env:WEBENGINE_LOG_PATH='${LOG_PATH.replace(/'/g, "''")}'`,
    // リポジトリ側のbridge/uiを直接読むdevモード(devreloadが有効になる)
    ...(devMode
      ? [`$env:WEBENGINE_DEV_SRC='${REPO.replace(/\\/g, "/").replace(/'/g, "''")}'`]
      : []),
    `Start-Process -FilePath '${QGIS_EXE}'`,
  ].join("; ");
  if (!devMode) {
    console.log(
      "[ensure] devモード以外のため WEBENGINE_DEV_SRC 未設定で起動" +
        "(配置済み実体dirが動作。開発は npm run deploy で開発モードへ)"
    );
  }
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

  const mode = currentDeployMode();
  console.log(
    `[ensure] no live driver; launching QGIS ` +
      `(deploy mode: ${mode || "unknown"}. 未配置なら npm run deploy / ` +
      `deploy:use / deploy:install を手動で実行してください)`
  );
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
      `プラグイン未配置なら npm run deploy(開発)/deploy:install(利用)を ` +
      `手動で実行してください。test-results/plugin_load.log と ` +
      `QGIS起動状態も確認`
  );
}

// pyevalで実行するリロードコードを生成する。プラグイン配下のimportキャッシュを
// 掃除してからreloadPluginし、ダイアログを開き直す。
// プラグインが未ロードの場合(QGIS側で無効化等)はloadPlugin+startPluginに倒す。
// ※ドライバが reload_plugin コマンドを実装済みならそちらを使い、
//   これは旧ドライバ向けのフォールバック。
export const reloadCode = (pluginId) => `
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
_p = qgis.utils.plugins.get(PLUGIN_ID)
if hasattr(_p, "open_dialog"):
    _p.open_dialog()
result = {"loaded": PLUGIN_ID in qgis.utils.plugins,
          "plugins": sorted(qgis.utils.plugins.keys())}
`;

/**
 * 実行中のQGIS内で全プラグインをホットリロードする。
 * reloadPluginでプラグインインスタンスが作り直され、新しいview+LiveDriverが
 * 同じlive dir(PID不変)を使い始める。
 */
export async function reloadPlugin({ liveBase = LIVE_BASE } = {}) {
  const dirs = await ensureQgis({ liveBase });
  // 制御プラグインがあればhub経由でreloadできる
  // (対象プラグインにlive dirが無くても reload_plugin→open_dialog で作られる)
  const ctrlDir = dirs.find((d) => d.pluginId === "qgis_live_driver");
  const ctrlPage = ctrlDir ? new LivePage(ctrlDir.dir) : null;
  // reload対象: live dirを持つ全プラグイン + plugin.config.jsonの開発対象
  const ids = [
    ...new Set([...dirs.map((d) => d.pluginId).filter(Boolean), ...PLUGIN_IDS]),
  ];
  // 送信中の経路を先に殺さないようドライバ自身は最後にreloadする
  ids.sort((a, b) => (a === "qgis_live_driver") - (b === "qgis_live_driver"));
  const results = [];
  for (const id of ids) {
    const own = dirs.find((d) => d.pluginId === id);
    const page = own ? new LivePage(own.dir) : ctrlPage;
    if (!page) {
      console.log(`[reload] ${id}: no live dir and no control driver; skipped`);
      continue;
    }
    let res;
    try {
      res = await page.reloadPlugin(id);
    } catch (e) {
      // 旧ドライバ(コマンド未実装)はpyeval版へフォールバック
      if (!/unknown type|unsupported|does not support/i.test(String(e.message))) {
        throw e;
      }
      res = await page.pyeval(reloadCode(id));
    }
    console.log(`[reload] ${id}: ${JSON.stringify(res)}`);
    // 新しいviewがindex.htmlを読み込み終わるまで待つ。
    // reload直後は旧viewが破棄中でeval timeoutすることがあるのでwaitForで吸収する。
    // viewを持たない制御プラグイン(qgis_live_driver等)はスキップ。
    // hub経由の場合はplugin_idで対象ドライバの名前空間に転送される。
    const opts = own ? {} : { pluginId: id };
    const hasUi = await page
      .pyeval("driver.view is not None", opts)
      .catch(() => false);
    if (hasUi) {
      await page.waitFor('[data-testid="layer-list"]', 60000, opts);
      console.log(`[reload] ${id}: dialog re-opened and UI ready`);
    }
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
    // viewを持たない制御プラグイン(qgis_live_driver等)はdevreload対象外
    const hasUi = await page.pyeval("driver.view is not None").catch(() => false);
    if (!hasUi) continue;
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
      await reloadPlugin();
    } else if (cmd === "devreload") {
      await devReload();
    } else {
      console.log("usage: node scripts/qgis-session.mjs <ensure|reload|devreload>");
      process.exit(cmd ? 1 : 0);
    }
  } catch (e) {
    console.error(e.message || e);
    process.exit(1);
  }
}
