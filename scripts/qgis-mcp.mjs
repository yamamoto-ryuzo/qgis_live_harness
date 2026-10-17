// QGIS常駐インスタンスをMCP経由で操作可能にするアダプタ。
// live-drive.mjs の LivePage (ファイル経由JSONLチャネル) を薄く包み、
// MCPツールとして公開する。QGIS未起動時は自動でensure( deploy+起動 )する。
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
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { z } from "zod";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { LivePage, resolveLiveDir } from "./live-drive.mjs";
import { ensureQgis, reloadPlugin, devReload } from "./qgis-session.mjs";

const REPO = fileURLToPath(new URL("../", import.meta.url));
const LIVE_BASE = process.env.WEBENGINE_LIVE_DIR || join(REPO, "test-results", "live");

// live dirを解決してLivePageを返す。ドライバが死んでいればensureで起動する。
// (ensureは応答するインスタンスがあればアタッチするだけで安い)
async function getPage() {
  const dir = await resolveLiveDir(LIVE_BASE);
  const page = new LivePage(dir);
  try {
    await page.pyeval("1", { timeoutMs: 4000 });
    return page;
  } catch {
    const ensured = await ensureQgis({ liveBase: LIVE_BASE });
    return new LivePage(ensured);
  }
}

const text = (v) => ({
  content: [{ type: "text", text: typeof v === "string" ? v : JSON.stringify(v, null, 2) }],
});
const err = (e) => ({
  content: [{ type: "text", text: String(e && e.message ? e.message : e).slice(-2000) }],
  isError: true,
});

const server = new McpServer({ name: "qgis-live", version: "0.1.0" });

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
      return { content: [{ type: "text", text: await ensureQgis({ liveBase: LIVE_BASE }) }] };
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
      "例: 'iface.activeLayer().name()' / 'len(QgsProject.instance().mapLayers())'",
    inputSchema: {
      code: z.string().describe("実行するPythonコード(式または文)"),
      timeoutMs: z.number().optional().describe("タイムアウトms(既定120000)"),
    },
  },
  async ({ code, timeoutMs }) => {
    try {
      const page = await getPage();
      return text(await page.pyeval(code, timeoutMs ? { timeoutMs } : {}));
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
      "重いQGIS操作直後はレンダラーが飢餓してタイムアウトすることがある(その場合pyevalを使う)。",
    inputSchema: {
      expression: z.string().describe("評価するJS式"),
      timeoutMs: z.number().optional().describe("タイムアウトms(既定45000)"),
    },
  },
  async ({ expression, timeoutMs }) => {
    try {
      const page = await getPage();
      return text(await page.evaluate(expression, timeoutMs ? { timeoutMs } : {}));
    } catch (e) {
      return err(e);
    }
  }
);

server.registerTool(
  "qgis_bridge_call",
  {
    description:
      "プラグインのbridgeメソッドを呼ぶ(BridgeClient.callJson相当)。 " +
      "実PluginBridgeのpyqtSlotが実行され、JSON結果がそのまま返る。 " +
      "例: method='pluginInfo' / method='setActiveLayer', args=['<layerId>']",
    inputSchema: {
      method: z.string().describe("bridgeメソッド名"),
      args: z.array(z.any()).optional().describe("引数の配列(既定[])"),
    },
  },
  async ({ method, args = [] }) => {
    try {
      const page = await getPage();
      const expr = `BridgeClient.callJson(${JSON.stringify(method)}${args.length ? "," + args.map((a) => JSON.stringify(a)).join(",") : ""})`;
      return text(await page.evaluate(expr));
    } catch (e) {
      return err(e);
    }
  }
);

server.registerTool(
  "qgis_screenshot",
  {
    description:
      "プラグインUI(QWebEngineView)をPNGで撮影し画像として返す。pathはQGIS側から見えるパス。",
    inputSchema: {
      path: z.string().optional().describe("保存先の絶対パス(既定: <repo>/test-results/mcp-shot.png)"),
    },
  },
  async ({ path }) => {
    try {
      const page = await getPage();
      const p = path || join(REPO, "test-results", "mcp-shot.png").replace(/\\/g, "/");
      const saved = await page.screenshot(p);
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
  "qgis_devreload",
  {
    description:
      "リポジトリ側のbridge.py/logic.py/ui/を再読み込みする(deploy・reloadPlugin・再起動すべて不要)。 " +
      "コード編集直後に呼んで反映する。プラグイン器側(main_plugin.py/live_driver.py)の変更はqgis_reloadを使う。",
    inputSchema: {},
  },
  async () => {
    try {
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
      "deploy -Copy 後、実行中QGISでプラグインをホットリロードする。 " +
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
