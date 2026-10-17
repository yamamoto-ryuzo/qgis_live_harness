// ファイル経由ライブドライバのクライアント側。
// プラグイン側 live_driver.py が commands.jsonl をポーリングし、
// 結果を results.jsonl に追記する。QtWebEngineのCDPが使えない環境でも
// 実QGIS内のUIをJSで検証できる(Playwrightのevaluate相当+スクリーンショット)。

import { appendFile, mkdir, readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join } from "node:path";

import { readdir, stat } from "node:fs/promises";

/**
 * liveDirを解決する。プラグイン側は liveDir/qgis-<pid>/ に分離して書き込むため、
 * baseディレクトリが渡された場合は最も新しく作られた qgis-* サブディレクトリを選ぶ。
 */
export async function resolveLiveDir(liveDir) {
  try {
    const entries = await readdir(liveDir, { withFileTypes: true });
    const subdirs = entries.filter((e) => e.isDirectory() && e.name.startsWith("qgis-"));
    let newest = null, newestBirth = 0;
    for (const e of subdirs) {
      const p = join(liveDir, e.name);
      // クライアントのcommands.jsonl書き込みでmtimeが更新されてしまうためbirthtimeで判定
      const s = await stat(p);
      if (s.birthtimeMs > newestBirth) { newestBirth = s.birthtimeMs; newest = p; }
    }
    if (newest) return newest;
  } catch {}
  return liveDir;
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
    this.pending = new Map();
  }

  /** 以前のセッションの結果が残っているとid衝突で誤読するため初期化する */
  async reset() {
    await mkdir(this.dir, { recursive: true });
    const { writeFile } = await import("node:fs/promises");
    await writeFile(this.cmdPath, "");
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

  async _send(cmd, timeoutMs = 45000) {
    await mkdir(this.dir, { recursive: true });
    await appendFile(this.cmdPath, JSON.stringify(cmd) + "\n");
    return this._nextResult(cmd.id, timeoutMs);
  }

  /**
   * JSを評価。Promiseはawaitされる。JSON化可能な値が返る。
   * ナビゲーション中などでrunJavaScriptのコールバックが捨てられると
   * プラグイン側がeval timeoutを返すため、その場合は新しいidでリトライする。
   */
  async evaluate(expression, { retries = 4 } = {}) {
    for (let attempt = 0; attempt <= retries; attempt++) {
      const id = ++this.seq;
      try {
        return await this._send({ id, type: "eval", expression });
      } catch (e) {
        if (!String(e.message).includes("eval timeout") || attempt === retries) throw e;
        await new Promise((r) => setTimeout(r, 1000));
      }
    }
  }

  async waitFor(selector, timeoutMs = 15000) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      const found = await this.evaluate(
        `!!document.querySelector(${JSON.stringify(selector)})`
      );
      if (found) return;
      await new Promise((r) => setTimeout(r, 250));
    }
    throw new Error(`waitFor timeout: ${selector}`);
  }

  async click(selector) {
    return this.evaluate(
      `(()=>{const el=document.querySelector(${JSON.stringify(selector)});` +
        `if(!el)throw new Error("not found: ${selector}");el.click();return true})()`
    );
  }

  /** QWebEngineView.grab() でPNG保存。pathはQGIS側から見える絶対パス */
  async screenshot(path) {
    const id = ++this.seq;
    return this._send({ id, type: "screenshot", path });
  }

  close() {}
}
