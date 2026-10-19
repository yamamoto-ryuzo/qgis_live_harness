// 開発中のホットリロード(watchモード)。
// qgis-plugin/<id>/ の変更を監視し、保存のたびに実行中QGIS内のプラグインを
// 自動で再読み込みする。QGIS再起動・deployは不要(junction配置が前提。
// 利用モード(実体配置)ではrepo編集が届かないため、先に `npm run deploy` で
// junction化しておくこと)。
//
// 再読み込み方式は変更ファイルで自動選択:
//   - ui/**, bridge.py, logic.py のみの変更 かつ 対象がWebEngineプラグイン
//     (viewを持つ) → devreload(repo側を別名importし直す軽量リロード)
//   - それ以外(プラグイン本体の *.py 等を含む) → reload_plugin
//     (sys.modules掃除 + reloadPlugin + open_dialog)
// 複数プラグインが同時に変更された場合は qgis_live_driver を最後に処理する
// (送信経路であるドライバを先に殺さないため)。
//
// 使い方:
//   node scripts/live-watch.mjs [--plugin <id>] [--debounce <ms>]
//     --plugin    監視対象を絞る(既定=plugin.config.jsonの全id)
//     --debounce  変更イベントのまとめ待ちms(既定500)
//   npm run live:watch
//   終了は Ctrl+C。

import { watch } from "node:fs";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { LivePage, resolveLiveDirs } from "./live-drive.mjs";
import { ensureQgis, reloadCode } from "./qgis-session.mjs";

const REPO = fileURLToPath(new URL("../", import.meta.url));
const LIVE_BASE =
  process.env.WEBENGINE_LIVE_DIR || join(REPO, "test-results", "live");
const WATCH_ROOT = join(REPO, "qgis-plugin");
const PLUGIN_IDS = [].concat(
  JSON.parse(readFileSync(join(REPO, "plugin.config.json"), "utf8")).id
);
const CTRL_ID = "qgis_live_driver";

// 監視対象外: 実行時に影響しない生成物・ドキュメント・翻訳ソース等。
// .ui/.py/.json 等の実行系ファイルは全てリロード対象。
const IGNORE_DIRS = new Set([
  "__pycache__", ".git", ".upstream", ".vscode", "node_modules", "i18n",
]);
const IGNORE_FILE =
  /\.(pyc|pyo|qm|ts|po|db|md|pdf|png|jpe?g|gif|svg|ico|zip|qrc|pro|bat|ps1|tmp|swp|bak|orig|~)$/i;

// WEBENGINE_DEV_SRC経由で別名importされるrepo側モジュール。
// これら「だけ」の変更ならdevreloadで足りる(対象がviewを持つ場合)。
const DEVSRC_FILES = new Set(["bridge.py", "logic.py"]);

const args = process.argv.slice(2);
const opt = (name, def) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : def;
};
const onlyPlugin = opt("--plugin", null);
const DEBOUNCE_MS = Number(opt("--debounce", 500)) || 500;
const targets = onlyPlugin ? [onlyPlugin] : PLUGIN_IDS;

const ts = () => new Date().toLocaleTimeString("ja-JP", { hour12: false });
const log = (msg) => console.log(`[watch ${ts()}] ${msg}`);

function isIgnored(rel) {
  const parts = rel.split(/[\\/]/);
  if (parts.some((p) => IGNORE_DIRS.has(p) || p.startsWith("."))) return true;
  const base = parts[parts.length - 1];
  // 拡張子の無い名前(dirイベントや LICENSE/Makefile 等)は無視
  if (!base.includes(".")) return true;
  return IGNORE_FILE.test(base);
}

// repo側devソース(ui/ or プラグイン直下のbridge.py/logic.py)か
function isDevSrc(rel) {
  const norm = rel.split(sep).join("/");
  if (norm.startsWith("ui/")) return true;
  return !norm.includes("/") && DEVSRC_FILES.has(norm);
}

// --- live dir解決(QGIS再起動時に新しいpid dirを拾えるよう毎回解決) ---
async function liveDirs() {
  return resolveLiveDirs(LIVE_BASE);
}

function pageFor(dirs, id) {
  const own = dirs.find((d) => d.pluginId === id);
  if (own) return { page: new LivePage(own.dir), opts: {} };
  const ctrl = dirs.find((d) => d.pluginId === CTRL_ID);
  return ctrl
    ? { page: new LivePage(ctrl.dir), opts: { pluginId: id } }
    : { page: null, opts: {} };
}

async function hasView(dirs, id) {
  const { page, opts } = pageFor(dirs, id);
  if (!page) return false;
  try {
    return !!(await page.pyeval("driver.view is not None", {
      ...opts,
      timeoutMs: 10000,
    }));
  } catch {
    return false;
  }
}

async function reloadOne(dirs, id) {
  const { page, opts } = pageFor(dirs, id);
  if (!page) {
    log(`${id}: live dirも制御ドライバも無し。スキップ`);
    return;
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
  log(`${id}: reload_plugin → ${JSON.stringify(res)}`);
  // viewを持つプラグインはUI再読込完了まで待つ(qgis-session.mjsと同じ待ち)
  if (await page.pyeval("driver.view is not None", opts).catch(() => false)) {
    await page.waitFor('[data-testid="layer-list"]', 60000, opts);
    log(`${id}: dialog re-opened and UI ready`);
  }
}

async function devReloadOne(dirs, id) {
  const { page, opts } = pageFor(dirs, id);
  await page.devreload(opts);
  await page.waitFor('[data-testid="layer-list"]', 60000, opts);
  log(`${id}: devreload → repo側 bridge/ui を再読込`);
}

async function applyChanges(id, files) {
  const list = [...files];
  log(`${id}: ${list.length}件の変更を検出 (${list.slice(0, 4).join(", ")}` +
    `${list.length > 4 ? ", ..." : ""})`);
  const dirs = await liveDirs();
  const devOnly = list.every(isDevSrc);
  try {
    if (devOnly && (await hasView(dirs, id))) {
      await devReloadOne(dirs, id);
      return;
    }
    // 本体側ファイルを含む / devソースでもview無し(Qtプラグイン) → 全体リロード
    await reloadOne(dirs, id);
  } catch (e) {
    // コマンド自体が死んだケース(QGIS再起動でlive dirが入れ替わった等)は
    // ensureで再接続/起動して1回だけリトライ
    log(`${id}: リロード失敗(${e.message})。ensureして再試行`);
    try {
      await ensureQgis({ liveBase: LIVE_BASE });
      await reloadOne(await liveDirs(), id);
    } catch (e2) {
      log(`${id}: リトライも失敗: ${e2.message}`);
    }
  }
}

// --- debounce + 直列キュー ---
const pending = new Map(); // id -> {files:Set, timer}
const queue = new Map(); // id -> Set(files)
let pumping = false;

function schedule(id, rel) {
  if (isIgnored(rel)) return;
  let e = pending.get(id);
  if (!e) {
    e = { files: new Set(), timer: null };
    pending.set(id, e);
  }
  e.files.add(rel);
  clearTimeout(e.timer);
  e.timer = setTimeout(() => {
    pending.delete(id);
    queue.set(id, new Set([...(queue.get(id) || []), ...e.files]));
    pump();
  }, DEBOUNCE_MS);
}

async function pump() {
  if (pumping) return;
  pumping = true;
  try {
    while (queue.size) {
      // ドライバ(制御面)は最後。Mapの順序維持のためキー配列をソート
      const ids = [...queue.keys()].sort(
        (a, b) => (a === CTRL_ID) - (b === CTRL_ID)
      );
      const id = ids[0];
      const files = queue.get(id);
      queue.delete(id);
      await applyChanges(id, files);
    }
  } finally {
    pumping = false;
  }
}

// --- watcher ---
function onChange(id, name) {
  if (!name) return;
  schedule(id, String(name));
}

function watchPlugin(id) {
  const root = join(WATCH_ROOT, id);
  if (!existsSync(root) || !statSync(root).isDirectory()) {
    log(`${id}: ${root} が無いため監視対象外`);
    return;
  }
  try {
    // Windows/Linux(Node>=19.1)ではrecursive指定でサブdirまで拾える
    watch(root, { recursive: true }, (_ev, name) => onChange(id, name));
  } catch {
    // recursive非対応環境向けフォールバック: サブdir個別監視
    const walk = (dir) => {
      watch(dir, (_ev, name) =>
        onChange(id, join(relative(root, dir), String(name))));
      for (const e of readdirSync(dir, { withFileTypes: true })) {
        if (e.isDirectory() && !IGNORE_DIRS.has(e.name) &&
            !e.name.startsWith(".")) {
          walk(join(dir, e.name));
        }
      }
    };
    walk(root);
  }
  log(`${id}: 監視開始 ${root}`);
}

const dirs = await ensureQgis({ liveBase: LIVE_BASE });
log(`live driver接続: ${dirs.map((d) => d.pluginId || "?").join(", ")}`);
for (const id of targets) watchPlugin(id);
log(`watching ${targets.length} plugin(s). 保存すると自動でリロードします`);
