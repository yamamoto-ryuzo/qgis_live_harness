#!/usr/bin/env python3
"""qgis_live用 MCP stdio ブリッジ(標準ライブラリのみ)。

MCPクライアントがこのスクリプトをspawnするだけで、
稼働中QGISへの遠隔操作がMCPツールとして使える:

    python .../plugins/qgis_live/mcp_stdio.py

動作: stdinの1行1JSON-RPCメッセージを受け、tools/callを
live dir の commands.jsonl へ追記 → results.jsonl の結果を待ち
MCP形式でstdoutへ返す。

接続先は ~/.qgis-live/<pid>-<plugin>.json のレジストリから自動検出
(QGIS側で qgis_live が WEBENGINE_LIVE_DIR 付きで起動している必要あり)。
QGIS_LIVE_PLUGIN で対象プラグインを指定できる(既定: qgis_live)。
"""

import base64
import json
import os
import sys
import time

REG_DIR = os.environ.get(
    "QGIS_LIVE_REGISTRY",
    os.path.join(os.path.expanduser("~"), ".qgis-live"),
)
TARGET_PLUGIN = os.environ.get("QGIS_LIVE_PLUGIN", "qgis_live")
TIMEOUT = 120.0
POLL = 0.2

PROTOCOL_VERSION = "2025-03-26"

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

_session = f"mcp{os.getpid()}"
_seq = 0
_live_dir = None


def _err(msg):
    sys.stderr.write(f"[mcp_stdio] {msg}\n")
    sys.stderr.flush()


def _find_live_dir():
    """レジストリから稼働中のlive dirを探して応答確認する。"""
    if not os.path.isdir(REG_DIR):
        return None
    cands = []
    for name in os.listdir(REG_DIR):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(REG_DIR, name), encoding="utf-8") as f:
                e = json.load(f)
            if e.get("live_dir"):
                cands.append(e)
        except Exception:
            pass
    cands.sort(key=lambda e: (
        e.get("plugin_id") != TARGET_PLUGIN, -e.get("started", 0)))
    for e in cands:
        d = e["live_dir"]
        if _probe(d):
            return d
    return None


def _probe(live_dir):
    try:
        return _send(live_dir, {"id": f"{_session}-probe",
                                "type": "pyeval", "code": "1"},
                     timeout=5.0).get("result") == 1
    except Exception:
        return False


def _send(live_dir, cmd, timeout=TIMEOUT):
    cmd_path = os.path.join(live_dir, "commands.jsonl")
    res_path = os.path.join(live_dir, "results.jsonl")
    os.makedirs(live_dir, exist_ok=True)
    with open(cmd_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(cmd, ensure_ascii=False) + "\n")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(res_path):
            with open(res_path, encoding="utf-8") as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    if obj.get("id") == cmd["id"]:
                        return obj
        time.sleep(POLL)
    return {"id": cmd["id"], "error": f"timeout ({timeout}s)"}


def _next_id():
    global _seq
    _seq += 1
    return f"{_session}-{_seq}"


def _tool_call(name, args):
    global _live_dir
    if _live_dir is None:
        _live_dir = _find_live_dir()
        if _live_dir is None:
            return {"content": [{"type": "text", "text":
                                 "no live qgis_live driver "
                                 f"(registry: {REG_DIR})"}],
                    "isError": True}
    if name == "qgis_pyeval":
        rep = _send(_live_dir, {"id": _next_id(), "type": "pyeval",
                                "code": args.get("code", "")})
    elif name == "qgis_screenshot":
        import tempfile
        path = args.get("path") or os.path.join(
            tempfile.gettempdir(), f"qgis-shot-{_seq}.png")
        rep = _send(_live_dir, {"id": _next_id(), "type": "screenshot",
                                "path": path})
        if "error" not in rep:
            try:
                with open(rep["result"], "rb") as f:
                    return {"content": [{
                        "type": "image",
                        "data": base64.b64encode(f.read()).decode("ascii"),
                        "mimeType": "image/png",
                    }]}
            except Exception as e:
                rep = {"error": repr(e)}
    else:
        return {"content": [{"type": "text", "text": f"unknown tool: {name}"}],
                "isError": True}
    if "error" in rep:
        return {"content": [{"type": "text", "text": str(rep["error"])}],
                "isError": True}
    v = rep.get("result")
    return {"content": [{"type": "text", "text":
                         v if isinstance(v, str)
                         else json.dumps(v, ensure_ascii=False, indent=2)}]}


def _handle(msg):
    method = msg.get("method", "")
    mid = msg.get("id")
    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": mid,
            "result": {
                "protocolVersion": msg.get("params", {})
                    .get("protocolVersion", PROTOCOL_VERSION),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "qgis-live", "version": "0.1.0"},
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        p = msg.get("params", {})
        return {"jsonrpc": "2.0", "id": mid,
                "result": _tool_call(p.get("name"), p.get("arguments") or {})}
    return {"jsonrpc": "2.0", "id": mid,
            "error": {"code": -32601,
                      "message": f"method not found: {method}"}}


def main():
    _err(f"started. registry={REG_DIR} target={TARGET_PLUGIN}")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue
        if msg.get("method", "").startswith("notifications/") or "id" not in msg:
            continue  # 通知は応答不要
        try:
            resp = _handle(msg)
        except Exception as e:
            resp = {"jsonrpc": "2.0", "id": msg.get("id"),
                    "error": {"code": -32603, "message": repr(e)}}
        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
