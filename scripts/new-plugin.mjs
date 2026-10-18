// 新しいWebEngineプラグインの足場を作る。
//   node scripts/new-plugin.mjs <plugin_id>
// qgis-plugin/webengine_plugin をテンプレートとして
// qgis-plugin/<plugin_id>/ にコピーし、metadata.txt の name を置き換え、
// 開発対象(plugin.config.json)をそのIDに切り替える。

import {
  cpSync, existsSync, readdirSync, readFileSync, rmSync, writeFileSync,
} from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const REPO = fileURLToPath(new URL("..", import.meta.url));
const TEMPLATE = join(REPO, "qgis-plugin", "webengine_plugin");
const CONFIG = join(REPO, "plugin.config.json");

const id = process.argv[2];
if (!id || !/^[a-z][a-z0-9_]*$/.test(id)) {
  console.error(
    "usage: node scripts/new-plugin.mjs <plugin_id>\n" +
    "  plugin_id = deploy先フォルダ名=Pythonパッケージ名。" +
    "小文字英字始まりの [a-z0-9_] のみ");
  process.exit(1);
}

const dest = join(REPO, "qgis-plugin", id);
if (existsSync(dest)) {
  console.error(`error: qgis-plugin/${id} already exists`);
  process.exit(1);
}

cpSync(TEMPLATE, dest, { recursive: true });
// テンプレ由来の生成物は引き継がない
for (const name of ["__pycache__"]) {
  const p = join(dest, name);
  if (existsSync(p)) rmSync(p, { recursive: true, force: true });
}

const metaPath = join(dest, "metadata.txt");
const meta = readFileSync(metaPath, "utf8")
  .replace(/^name=.*$/m, `name=${id}`);
writeFileSync(metaPath, meta);

writeFileSync(CONFIG, JSON.stringify({ id }, null, 2) + "\n");

console.log(`created qgis-plugin/${id}/ (from webengine_plugin template)`);
console.log(`plugin.config.json -> {"id": "${id}"}`);
console.log(`next:
  npm run deploy:copy   # deployしてQGISプラグイン管理で有効化
  npm run live:ensure   # 常駐QGIS起動
  # ui/index.html / bridge.py / logic.py を編集 → npm run live:devreload`);
