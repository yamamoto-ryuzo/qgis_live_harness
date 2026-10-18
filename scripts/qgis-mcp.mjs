// QGIS常駐インスタンスをMCP経由で操作可能にするアダプタ。
// live-drive.mjs の LivePage (ファイル経由JSONLチャネル) を薄く包み、
// MCPツールとして公開する。QGIS未起動時は自動でensure( deploy+起動 )する。
//
// qgis_live_driver がlive中ならそこをhubとして使い、pluginIdは
// plugin_idルーティングで各プラグインへ転送される(1窓口で全プラグイン制御)。
// tools: qgis_ensure / qgis_pyeval / qgis_eval / qgis_bridge_call /
//        qgis_screenshot / qgis_status / qgis_open_plugin /
//        qgis_devreload / qgis_reload
//
// 設定例 (.devin/mcp_config.json):
//   { "mcpServers": { "qgis-live": { "command": "node",
//     "args": ["<repo>/scripts/qgis-mcp.mjs"] } } }
//
// 注意: stdio transportではstdoutがJSON-RPC専用のため、
// 内部の進捗ログ(qgis-session.mjsのconsole.log)はstderrに退避している。

// stdio MCPサーバはstdoutがプロトコル専用。呼び出し先のconsole.logもstderrへ。
console.log = (...args) => console.error(...args);

import { readFile } from "node:fs/promises";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { z } from "zod";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { LivePage, resolveLiveDirs } from "./live-drive.mjs";
import { ensureQgis, reloadPlugin, devReload } from "./qgis-session.mjs";

const REPO = fileURLToPath(new URL("../", import.meta.url));
const LIVE_BASE = process.env.WEBENGINE_LIVE_DIR || join(REPO, "test-results", "live");
// plugin.config.jsonのidは文字列または配列(先頭=主開発対象)
const PLUGIN_ID = [].concat(JSON.parse(
  readFileSync(new URL("../plugin.config.json", import.meta.url), "utf8")
).id)[0];

// live dirを列挙する。どれか1つでもドライバが応答すればそれを返し、
// 全滅ならensure(deploy+起動)して再列挙する。
async function liveDirs() {
  const dirs = await resolveLiveDirs(LIVE_BASE);
  for (const d of dirs) {
    try {
      await new LivePage(d.dir).pyeval("1", { timeoutMs: 4000 });
      return dirs;
    } catch {}
  }
  return ensureQgis({ liveBase: LIVE_BASE });
}

// コマンド送信用のLivePageを返す。
// qgis_live_driver が居ればそれをhubとして返し、pluginIdはplugin_id
// ルーティングとしてコマンドに載せる。居なければ対象プラグイン自身の
// live dirへ直結し、pluginIdはundefinedにする(自身への送信にルーティング不要)。
async function dispatchPage(pluginId) {
  const dirs = await liveDirs();
  const ctrl = dirs.find((d) => d.pluginId === "qgis_live_driver");
  if (ctrl) return { page: new LivePage(ctrl.dir), pluginId };
  const t = dirs.find((d) => d.pluginId === pluginId)
    || dirs.find((d) => d.pluginId === PLUGIN_ID)
    || dirs[0];
  return { page: new LivePage(t.dir), pluginId: undefined };
}

// 対象プラグイン自身のlive dirに直結するLivePage(JS評価フォールバック用)。
async function directPage(pluginId) {
  const dirs = await liveDirs();
  const t = dirs.find((d) => d.pluginId === pluginId)
    || dirs.find((d) => d.pluginId === PLUGIN_ID)
    || dirs[0];
  return new LivePage(t.dir);
}

const text = (v) => ({
  content: [{ type: "text", text: typeof v === "string" ? v : JSON.stringify(v, null, 2) }],
});
const err = (e) => ({
  content: [{ type: "text", text: String(e && e.message ? e.message : e).slice(-2000) }],
  isError: true,
});

const server = new McpServer({ name: "qgis-live", version: "1.0.0" });

server.registerTool(
  "qgis_ensure",
  {
    description:
      "QGIS検証インスタンスが動いているか確認し、未起動ならdeploy+起動する。" +
      "応答するLiveDriverのlive dirを返す。他のツールは内部で自動ensureするため明示呼び出しは任意。",
    inputSchema: {},
  },
  async () => {
    try {
      const dirs = await ensureQgis({ liveBase: LIVE_BASE });
      return {
        content: [{
          type: "text",
          text: dirs.map((d) => `${d.dir} (${d.pluginId})`).join("\n"),
        }],
      };
    } catch (e) {
      return err(e);
    }
  }
);

server.registerTool(
  "qgis_pyeval",
  {
    description:
      "実行中のQGISプロセス内でPythonを同期実行する。式はeval、文はexec(result変数が返却値)。 " +
      "名前空間に iface/view/driver があり持続する。qgis.core等はコード内でimportする。 " +
      "pluginId指定でそのプラグインのドライバ名前空間(そのview)で実行される。 " +
      "例: 'iface.activeLayer().name()' / 'len(QgsProject.instance().mapLayers())'",
    inputSchema: {
      code: z.string().describe("実行するPythonコード(式または文)"),
      pluginId: z.string().optional().describe("対象プラグインID(省略時はドライバ自身の名前空間)"),
      timeoutMs: z.number().optional().describe("タイムアウトms(既定120000)"),
    },
  },
  async ({ code, pluginId, timeoutMs }) => {
    try {
      const { page, pluginId: pid } = await dispatchPage(pluginId);
      return text(await page.pyeval(
        code, { pluginId: pid, ...(timeoutMs ? { timeoutMs } : {}) }));
    } catch (e) {
      return err(e);
    }
  }
);

server.registerTool(
  "qgis_eval",
  {
    description:
      "プラグインUI(QWebEngineView)内でJS式を評価する。Promiseはawaitされる。 " +
      "DOM検査・BridgeClient.callJson()呼び出し等に使う。 " +
      "pluginId省略時は開発対象(plugin.config.json)のview。 " +
      "重いQGIS操作直後はレンダラーが飢餓してタイムアウトすることがある(その場合pyevalを使う)。",
    inputSchema: {
      expression: z.string().describe("評価するJS式"),
      pluginId: z.string().optional().describe("対象プラグインID(省略時はplugin.config.jsonのid)"),
      timeoutMs: z.number().optional().describe("タイムアウトms(既定45000)"),
    },
  },
  async ({ expression, pluginId, timeoutMs }) => {
    try {
      const { page, pluginId: pid } = await dispatchPage(pluginId || PLUGIN_ID);
      return text(await page.evaluate(
        expression, { pluginId: pid, ...(timeoutMs ? { timeoutMs } : {}) }));
    } catch (e) {
      return err(e);
    }
  }
);

server.registerTool(
  "qgis_bridge_call",
  {
    description:
      "プラグインのbridgeメソッドを呼ぶ。ドライバ経由ではプロセス内で直接呼ぶため " +
      "WebChannelを通らず、レンダラー飢餓中でも動く。 " +
      "例: method='pluginInfo' / method='setActiveLayer', args=['<layerId>']",
    inputSchema: {
      method: z.string().describe("bridgeメソッド名"),
      args: z.array(z.any()).optional().describe("引数の配列(既定[])"),
      pluginId: z.string().optional().describe("対象プラグインID(省略時はplugin.config.jsonのid)"),
    },
  },
  async ({ method, args = [], pluginId }) => {
    const pid = pluginId || PLUGIN_ID;
    try {
      const { page, pluginId: fwd } = await dispatchPage(pid);
      try {
        return text(await page.bridgeCall(method, args, { pluginId: fwd }));
      } catch (e) {
        // 旧ドライバ(bridge_call未実装)はJS経由にフォールバック
        if (!/unknown type|does not support/i.test(String(e.message))) throw e;
      }
      const direct = await directPage(pid);
      const expr = `BridgeClient.callJson(${JSON.stringify(method)}${args.length ? "," + args.map((a) => JSON.stringify(a)).join(",") : ""})`;
      return text(await direct.evaluate(expr));
    } catch (e) {
      return err(e);
    }
  }
);

server.registerTool(
  "qgis_screenshot",
  {
    description:
      "PNGで撮影し画像として返す。pathはQGIS側から見えるパス。 " +
      "pluginId省略時はドライバの地図キャンバス、指定時はそのプラグインのview。 " +
      "target: view|window|canvas|mainwindow。",
    inputSchema: {
      path: z.string().optional().describe("保存先の絶対パス(既定: <repo>/test-results/mcp-shot.png)"),
      pluginId: z.string().optional().describe("対象プラグインID(省略時は地図キャンバス)"),
      target: z.string().optional().describe("view|window|canvas|mainwindow"),
    },
  },
  async ({ path, pluginId, target }) => {
    try {
      const { page, pluginId: pid } = await dispatchPage(pluginId);
      const p = path || join(REPO, "test-results", "mcp-shot.png").replace(/\\/g, "/");
      const saved = await page.screenshot(p, { pluginId: pid, target });
      const png = await readFile(p);
      return {
        content: [
          { type: "image", data: png.toString("base64"), mimeType: "image/png" },
          { type: "text", text: `saved: ${saved}` },
        ],
      };
    } catch (e) {
      return err(e);
    }
  }
);

server.registerTool(
  "qgis_status",
  {
    description:
      "ドライバの状態を返す(pid/http_port/ロード中プラグインと各view・driver有無)。 " +
      "ensure済みか・どのプラグインを操作できるかの確認に使う。",
    inputSchema: {},
  },
  async () => {
    try {
      const { page, pluginId } = await dispatchPage();
      try {
        return text(await page.status());
      } catch (e) {
        if (!/unknown type|unsupported/i.test(String(e.message))) throw e;
        return text({ note: "status unsupported by this driver", pluginId });
      }
    } catch (e) {
      return err(e);
    }
  }
);

server.registerTool(
  "qgis_open_plugin",
  {
    description:
      "プラグインをload/startしてopen_dialogする(未ロード・ダイアログ未オープンでも可)。 " +
      "プラグインのlive dirがまだ無い場合はこれで作れる。",
    inputSchema: {
      pluginId: z.string().optional().describe("対象プラグインID(省略時はplugin.config.jsonのid)"),
    },
  },
  async ({ pluginId }) => {
    try {
      const pid = pluginId || PLUGIN_ID;
      const { page } = await dispatchPage(pid);
      return text(await page.openPlugin(pid));
    } catch (e) {
      return err(e);
    }
  }
);

server.registerTool(
  "qgis_devreload",
  {
    description:
      "リポジトリ側のbridge.py/logic.py/ui/を再読み込みする(deploy・reloadPlugin・再起動すべて不要)。 " +
      "コード編集直後に呼んで反映する。プラグイン器側(main_plugin.py/live_driver.py)の変更はqgis_reloadを使う。",
    inputSchema: {
      pluginId: z.string().optional().describe("対象プラグインID(省略時はlive dirを持つ全プラグイン)"),
    },
  },
  async ({ pluginId }) => {
    try {
      if (pluginId) {
        const { page, pluginId: pid } = await dispatchPage(pluginId);
        await page.devreload({ pluginId: pid });
        return text(`devreload done: ${pluginId} repo-side bridge/ui reloaded`);
      }
      await devReload({ liveBase: LIVE_BASE });
      return text("devreload done: repo-side bridge/ui reloaded");
    } catch (e) {
      return err(e);
    }
  }
);

server.registerTool(
  "qgis_reload",
  {
    description:
      "deploy -Copy 後、実行中QGISでプラグインをホットリロードする(内部は " +
      "reload_plugin コマンド、旧ドライバ時はpyevalへフォールバック)。 " +
      "プラグイン器側(main_plugin.py, live_driver.py等)の変更を反映する時に使う。",
    inputSchema: {},
  },
  async () => {
    try {
      const res = await reloadPlugin({ liveBase: LIVE_BASE });
      return text(res);
    } catch (e) {
      return err(e);
    }
  }
);

await server.connect(new StdioServerTransport());
