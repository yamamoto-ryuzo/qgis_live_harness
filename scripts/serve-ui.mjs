// ui/ を静的サーブするだけの最小サーバー(依存なし)
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

import { readFileSync } from "node:fs";

const pluginId = JSON.parse(
  readFileSync(new URL("../plugin.config.json", import.meta.url), "utf8")
).id;
const root = fileURLToPath(new URL(`../qgis-plugin/${pluginId}/ui/`, import.meta.url));
const port = Number(process.env.UI_PORT || 8734);
const mime = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
};

createServer(async (req, res) => {
  const path = normalize(decodeURIComponent(new URL(req.url, "http://x").pathname));
  const rel = path.replace(/^[/\\]+/, "") || "index.html";
  const file = join(root, rel);
  if (!file.startsWith(root)) {
    res.writeHead(403).end("forbidden");
    return;
  }
  try {
    const body = await readFile(file);
    res.writeHead(200, { "content-type": mime[extname(file)] || "application/octet-stream" });
    res.end(body);
  } catch {
    res.writeHead(404).end("not found");
  }
}).listen(port, () => console.log(`serving ui/ at http://localhost:${port}`));
