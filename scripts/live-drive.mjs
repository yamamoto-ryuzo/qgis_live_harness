// ファイル経由ライブドライバのクライアント側。
// プラグイン側 live_driver.py が commands.jsonl をポーリングし、
// 結果を results.jsonl に追記する。QtWebEngineのCDPが使えない環境でも
// 実QGIS内のUIをJSで検証できる(Playwrightのevaluate相当+スクリーンショット)。

import { appendFile, mkdir, readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join } from "node:path";

import { readdir, stat } from "node:fs/promises";

/**
 * liveDirを解決し、live plugin dirの一覧を返す。
 * プラグイン側は liveDir/qgis-<pid>/<pluginId>/ に分離して書き込む。
 * 新しいpidディレクトリ順に [{dir, pluginId}] を返す。
 * qgis-* が無い場合は渡されたdir自身を1件として返す(単一dir指定の後方互換)。
 */
export async function resolveLiveDirs(liveDir) {
  try {
    const entries = await readdir(liveDir, { withFileTypes: true });
    const pids = [];
    for (const e of entries) {
      if (!e.isDirectory() || !e.name.startsWith("qgis-")) continue;
      const p = join(liveDir, e.name);
      // クライアントのcommands.jsonl書き込みでmtimeが更新されてしまうためbirthtimeで判定
      pids.push({ path: p, birth: (await stat(p)).birthtimeMs });
    }
    pids.sort((a, b) => b.birth - a.birth);
    const out = [];
    for (const { path } of pids) {
      const subs = (await readdir(path, { withFileTypes: true }))
        .filter((x) => x.isDirectory());
      if (!subs.length) {
        // 旧レイアウト(qgis-<pid>直下にjsonlを置く)で動く既存インスタンス向け
        if (existsSync(join(path, "results.jsonl")) ||
            existsSync(join(path, "commands.jsonl"))) {
          out.push({ dir: path, pluginId: null });
        }
        continue;
      }
      for (const s of subs) out.push({ dir: join(path, s.name), pluginId: s.name });
    }
    if (out.length) return out;
  } catch {}
  return [{ dir: liveDir, pluginId: null }];
}

/**
 * 単一のlive plugin dirを返す(後方互換)。pluginId指定でそのプラグインを選ぶ。
 */
export async function resolveLiveDir(liveDir, pluginId) {
  const dirs = await resolveLiveDirs(liveDir);
  const match = pluginId
    ? dirs.find((d) => d.pluginId === pluginId)
    : dirs[0];
  return match ? match.dir : liveDir;
}

/**
 * 制御プラグイン qgis_live_driver のLivePageを返す。見つからなければnull。
 * 存在すれば plugin_id ルーティングで全プラグインを制御できる統一窓口になる。
 */
export async function getControlPage(liveDir) {
  const dirs = await resolveLiveDirs(liveDir);
  const c = dirs.find((d) => d.pluginId === "qgis_live_driver");
  return c ? new LivePage(c.dir) : null;
}

export class LivePage {
  /**
   * @param liveDir プラグイン側 WEBENGINE_LIVE_DIR と同じディレクトリ
   */
  constructor(liveDir) {
    this.dir = liveDir;
    this.cmdPath = join(liveDir, "commands.jsonl");
    this.resPath = join(liveDir, "results.jsonl");
    this.resOffset = 0;
    this.seq = 0;
    // 別クライアントや前セッションが残した同id結果を誤読しないよう、
    // インスタンスごとに一意なprefixをidに付ける(ドライバはidをそのままエコーする)
    this.session = `s${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
    this.pending = new Map();
  }

  /**
   * 以前のセッションの結果が残っているとid衝突で誤読するため初期化する。
   * commands.jsonl は切り詰めない: ドライバは読み取りoffsetを保持しており、
   * 切り詰め後にファイルが旧offsetを超えて再成長すると「縮小」と判定できず
   * コマンド行の途中から読み出してJSONDecodeError+コマンド喪失を起こす。
   * append-only にすればoffsetは常に行頭を指す。results側は追記専用で
   * offsetを持たないため、切り詰めても破壊的にならない。
   */
  async reset() {
    await mkdir(this.dir, { recursive: true });
    const { writeFile } = await import("node:fs/promises");
    await writeFile(this.resPath, "");
  }

  async _nextResult(id, timeoutMs = 45000) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      if (existsSync(this.resPath)) {
        const text = await readFile(this.resPath, "utf8");
        const lines = text.split("\n").filter(Boolean);
        for (const line of lines) {
          try {
            const obj = JSON.parse(line);
            if (obj.id === id) {
              if (obj.error) throw new Error(obj.error);
              return obj.result;
            }
          } catch (e) {
            if (e instanceof SyntaxError) continue; // 書き込み途中の行
            throw e;
          }
        }
      }
      await new Promise((r) => setTimeout(r, 200));
    }
    throw new Error(`timeout waiting result id=${id}`);
  }

  _nextId() {
    return `${this.session}-${++this.seq}`;
  }

  async _send(cmd, timeoutMs = 45000) {
    await mkdir(this.dir, { recursive: true });
    await appendFile(this.cmdPath, JSON.stringify(cmd) + "\n");
    return this._nextResult(cmd.id, timeoutMs);
  }

  /**
   * JSを評価。Promiseはawaitされる。JSON化可能な値が返る。
   * ナビゲーション中などでrunJavaScriptのコールバックが捨てられると
   * プラグイン側がeval timeoutを返すため、その場合は新しいidでリトライする。
   * pluginId指定時はplugin_idルーティングで他プラグインへ転送される
   * (このpageが指すlive dirがqgis_live_driver等のハブである場合に有効)。
   */
  async evaluate(expression, { retries = 4, timeoutMs = 45000, pluginId } = {}) {
    for (let attempt = 0; attempt <= retries; attempt++) {
      const id = this._nextId();
      try {
        return await this._send(
          { id, type: "eval", expression, plugin_id: pluginId }, timeoutMs);
      } catch (e) {
        // "eval timeout"(ドライバ側宣言)と "timeout waiting result"(GUI飢餓で
        // 結果が返らない)はどちらも一過性なので新idで再送する。
        // コマンドはid単位で無害(古い結果は誰も拾わない)
        if (!String(e.message).includes("timeout") || attempt === retries) throw e;
        await new Promise((r) => setTimeout(r, 1000));
      }
    }
  }

  /**
   * QGISプロセス内でPythonを実行する(任意コード実行。検証モード専用)。
   * 式ならevalの結果、文なら `result` 変数の値が返る。
   * 名前空間には iface/view/driver が持続する。
   * pluginId指定時はそのプラグインのドライバ名前空間で実行される。
   * 例: pyeval("iface.activeLayer().name() if iface.activeLayer() else None")
   */
  async pyeval(code, { timeoutMs = 120000, pluginId } = {}) {
    return this._send(
      { id: this._nextId(), type: "pyeval", code, plugin_id: pluginId },
      timeoutMs);
  }

  async waitFor(selector, timeoutMs = 15000, { pluginId } = {}) {
    const start = Date.now();
    let lastErr;
    while (Date.now() - start < timeoutMs) {
      try {
        const found = await this.evaluate(
          `!!document.querySelector(${JSON.stringify(selector)})`,
          { timeoutMs: 5000, pluginId }
        );
        if (found) return;
      } catch (e) {
        // GUI/レンダラー飢餓中はevalが無応答になる。窓内では粘る
        lastErr = e;
      }
      await new Promise((r) => setTimeout(r, 250));
    }
    throw new Error(
      `waitFor timeout: ${selector}` +
      (lastErr ? ` (last error: ${lastErr.message})` : "")
    );
  }

  async click(selector) {
    return this.evaluate(
      `(()=>{const el=document.querySelector(${JSON.stringify(selector)});` +
        `if(!el)throw new Error("not found: ${selector}");el.click();return true})()`
    );
  }

  /**
   * リポジトリ側のbridge等を再importしてページを再読み込みさせる。
   * deploy/reloadPlugin不要。WEBENGINE_DEV_SRC 必須(未設定ならエラー返る)。
   */
  async devreload({ timeoutMs = 30000, pluginId } = {}) {
    return this._send(
      { id: this._nextId(), type: "devreload", plugin_id: pluginId },
      timeoutMs);
  }

  /**
   * PNG保存。pathはQGIS側から見える絶対パス。
   * target: view(既定)|window|canvas|mainwindow。
   */
  async screenshot(path, { pluginId, target } = {}) {
    return this._send(
      { id: this._nextId(), type: "screenshot", path, plugin_id: pluginId,
        target });
  }

  /** ドライバ状態(pid/プラグイン一覧/view有無/http_port)を返す。 */
  async status() {
    return this._send({ id: this._nextId(), type: "status" });
  }

  /** プラグインをload/startしてopen_dialogする(未ロードでも使える)。 */
  async openPlugin(pluginId, { timeoutMs = 60000 } = {}) {
    return this._send(
      { id: this._nextId(), type: "open_plugin", plugin_id: pluginId },
      timeoutMs);
  }

  /**
   * プラグインをホットリロード(sys.modules掃除+reloadPlugin+open_dialog)。
   * deploy済みコードの器側変更を反映する。QGIS再起動不要。
   */
  async reloadPlugin(pluginId, { timeoutMs = 120000 } = {}) {
    return this._send(
      { id: this._nextId(), type: "reload_plugin", plugin_id: pluginId },
      timeoutMs);
  }

  /**
   * プラグインのbridgeメソッドをプロセス内で直接呼ぶ。
   * JS経由のBridgeClient.callJsonと違いWebChannelを通らないため、
   * レンダラー飢餓中でも使える。JSON文字列の結果は構造化して返る。
   */
  async bridgeCall(method, args = [], { pluginId, timeoutMs = 120000 } = {}) {
    return this._send(
      { id: this._nextId(), type: "bridge_call", plugin_id: pluginId,
        method, args },
      timeoutMs);
  }

  close() {}
}
