"""qgis_live_driver内蔵HTTPサーバ。標準ライブラリのみで実装。

MCP (Streamable HTTP) と plain REST を同一ポートで提供し、
MCP非対応のAI/アプリからもHTTP POSTだけでQGISを操作できるようにする。

  POST /mcp              MCP JSON-RPC (initialize/tools/list/tools/call/ping)
  POST /api/pyeval       {"code": "..."} → {"result": ...} | {"error": ...}
  POST /api/eval         {"expression": "..."} (viewを持たないのでunsupportedを返す)
  POST /api/screenshot   {"path": "...?"} → PNGバイナリ (Content-Type: image/png)
  GET  /api/tools        ツール仕様JSON(function calling系AIが読む用)
  GET  /api/health       {"ok": true, "pid": ...}

実行経路: HTTPワーカースレッド → driver.submit() でメモリキュー投入 →
GUIスレッドの LiveDriver._poll が実行 → 結果を待機して返す。
iface/QgsProject に触れるのは常にGUIスレッドのみ。

バインドは 127.0.0.1 固定、ポート0(空き自動選択)。
pyeval=任意コード実行のためリモート公開は想定しない。
"""

import base64
import json
import os
import tempfile
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOOLS = [
    {
        "name": "qgis_pyeval",
        "description":
            "Execute arbitrary Python inside the running QGIS process "
            "(GUI thread). Namespace has iface/QgsProject/QgsApplication/"
            "driver. Expressions return their value; statements return "
            "the `result` variable.",
        "inputSchema": {
            "type": "object",
            "properties": {"code": {"type": "string"}},
            "required": ["code"],
        },
    },
    {
        "name": "qgis_screenshot",
        "description":
            "Capture the QGIS map canvas as PNG. Returns the image.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
        },
    },
]

PROTOCOL_VERSION = "2025-03-26"


def _content_text(v):
    return {
        "content": [{
            "type": "text",
            "text": v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, indent=2),
        }]
    }


class _Handler(BaseHTTPRequestHandler):
    server_version = "qgis-live/0.1"
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass  # QGIS内でstderrは死にやすいので黙らせる

    # ---- 共通ユーティリティ ----

    def _read_body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def _json(self, code, obj, extra_headers=None):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _dispatch(self, cmd, timeout=120.0):
        return self.server.driver.submit(cmd, timeout=timeout)

    # ---- REST ----

    def do_GET(self):
        if self.path == "/api/health":
            self._json(200, {"ok": True, "pid": os.getpid(),
                             "plugin": "qgis_live_driver"})
        elif self.path == "/api/tools":
            self._json(200, {"tools": TOOLS})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        try:
            body = self._read_body()
            data = json.loads(body.decode("utf-8")) if body else {}
        except Exception as e:
            self._json(400, {"error": f"bad json: {e}"})
            return
        if self.path == "/mcp":
            self._mcp(data)
        elif self.path == "/api/pyeval":
            self._api_call({"type": "pyeval", "code": data.get("code", "")})
        elif self.path == "/api/eval":
            self._api_call({"type": "eval",
                            "expression": data.get("expression", "")})
        elif self.path == "/api/screenshot":
            self._api_shot(data.get("path"))
        else:
            self._json(404, {"error": "not found"})

    def _api_call(self, cmd):
        rep = self._dispatch(cmd)
        self._json(200 if "error" not in rep else 500, rep)

    def _api_shot(self, path):
        if not path:
            path = os.path.join(tempfile.gettempdir(),
                                f"qgis-shot-{uuid.uuid4().hex[:8]}.png")
        rep = self._dispatch({"type": "screenshot", "path": path})
        if "error" in rep:
            self._json(500, rep)
            return
        try:
            with open(rep["result"], "rb") as f:
                png = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(png)))
            self.end_headers()
            self.wfile.write(png)
        except Exception as e:
            self._json(500, {"error": repr(e)})

    # ---- MCP (Streamable HTTP, JSON応答のみ) ----

    def _mcp(self, msg):
        method = msg.get("method", "")
        mid = msg.get("id")

        if method.startswith("notifications/"):
            self.send_response(202)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if method == "initialize":
            self._json(200, {
                "jsonrpc": "2.0", "id": mid,
                "result": {
                    "protocolVersion": msg.get("params", {})
                        .get("protocolVersion", PROTOCOL_VERSION),
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "qgis-live", "version": "0.1.0"},
                },
            }, {"Mcp-Session-Id": uuid.uuid4().hex})
            return

        if method == "ping":
            self._json(200, {"jsonrpc": "2.0", "id": mid, "result": {}})
            return

        if method == "tools/list":
            self._json(200, {"jsonrpc": "2.0", "id": mid,
                             "result": {"tools": TOOLS}})
            return

        if method == "tools/call":
            params = msg.get("params", {})
            result = self._tool_call(params.get("name"),
                                     params.get("arguments") or {})
            self._json(200, {"jsonrpc": "2.0", "id": mid, "result": result})
            return

        self._json(200, {
            "jsonrpc": "2.0", "id": mid,
            "error": {"code": -32601, "message": f"method not found: {method}"},
        })

    def _tool_call(self, name, args):
        if name == "qgis_pyeval":
            rep = self._dispatch({"type": "pyeval",
                                  "code": args.get("code", "")})
            if "error" in rep:
                return {"content": [{"type": "text",
                                     "text": rep["error"]}], "isError": True}
            return _content_text(rep.get("result"))
        if name == "qgis_screenshot":
            path = args.get("path") or os.path.join(
                tempfile.gettempdir(), f"qgis-shot-{uuid.uuid4().hex[:8]}.png")
            rep = self._dispatch({"type": "screenshot", "path": path})
            if "error" in rep:
                return {"content": [{"type": "text",
                                     "text": rep["error"]}], "isError": True}
            try:
                with open(rep["result"], "rb") as f:
                    return {"content": [{
                        "type": "image",
                        "data": base64.b64encode(f.read()).decode("ascii"),
                        "mimeType": "image/png",
                    }]}
            except Exception as e:
                return {"content": [{"type": "text", "text": repr(e)}],
                        "isError": True}
        return {"content": [{"type": "text", "text": f"unknown tool: {name}"}],
                "isError": True}


def start_http(driver, host="127.0.0.1", port=0):
    """HTTPサーバをデーモンスレッドで起動し実ポートを返す。"""
    httpd = ThreadingHTTPServer((host, port), _Handler)
    httpd.daemon_threads = True
    httpd.driver = driver
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd, httpd.server_address[1]
