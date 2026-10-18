"""mcp_http.py の認証・ツールフィルタ・MCP応答のテスト。

mcp_http.py はstdlibのみで動くため実QGIS不要。
ドライバは submit を持つフェイクで代用する。
"""

import json
import urllib.error
import urllib.request

import pytest

from qgis_live_driver.mcp_http import TOOLS, start_http


class _FakeDriver:
    def submit(self, cmd, timeout=180.0):
        if cmd.get("type") == "screenshot":
            return {"id": cmd.get("id"), "error": "no canvas in test"}
        return {"id": cmd.get("id"), "result": {"echo": cmd.get("type")}}


def _req(port, method, path, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            hdrs = dict(r.headers)
            status = r.status
    except urllib.error.HTTPError as e:
        raw = e.read()
        hdrs = dict(e.headers)
        status = e.code
    try:
        return status, json.loads(raw), hdrs
    except Exception:
        return status, raw, hdrs


@pytest.fixture
def make_server():
    servers = []

    def _make(**kw):
        httpd, port = start_http(_FakeDriver(), **kw)
        servers.append(httpd)
        return port

    yield _make
    for s in servers:
        s.shutdown()


MCP_INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
MCP_LIST = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
MCP_CALL = lambda name, args=None: {  # noqa: E731
    "jsonrpc": "2.0", "id": 3, "method": "tools/call",
    "params": {"name": name, "arguments": args or {}},
}
AUTH = {"Authorization": "Bearer testkey"}


def test_token_always_required(make_server):
    # 認証は常時必須(/api/healthのみ無認証)。トークン付きで全機能が使える
    port = make_server(api_keys={"testkey"})
    st, body, _ = _req(port, "GET", "/api/health")
    assert st == 200 and body["ok"]
    st, _, _ = _req(port, "POST", "/mcp", MCP_INIT)
    assert st == 401
    st, body, hdrs = _req(port, "POST", "/mcp", MCP_INIT, AUTH)
    assert st == 200
    assert body["result"]["serverInfo"]["name"] == "qgis-live"
    assert "Mcp-Session-Id" in hdrs
    st, body, _ = _req(port, "POST", "/mcp", MCP_LIST, AUTH)
    assert len(body["result"]["tools"]) == len(TOOLS)
    st, body, _ = _req(port, "POST", "/api/pyeval", {"code": "1"}, AUTH)
    assert st == 200 and body["result"]["echo"] == "pyeval"


def test_no_keys_rejects_all(make_server):
    # 有効キーが1つも無いサーバは fail-closed(health以外全て401)
    port = make_server()
    st, body, _ = _req(port, "GET", "/api/health")
    assert st == 200 and body["ok"]
    st, _, _ = _req(port, "POST", "/mcp", MCP_INIT, AUTH)
    assert st == 401
    st, _, _ = _req(port, "POST", "/api/pyeval", {"code": "1"}, AUTH)
    assert st == 401


def test_wrong_key_rejected(make_server):
    port = make_server(api_keys={"testkey"})
    st, _, _ = _req(port, "POST", "/mcp", MCP_INIT)
    assert st == 401
    st, _, _ = _req(port, "POST", "/mcp", MCP_INIT,
                    {"Authorization": "Bearer wrong"})
    assert st == 401
    # 受け付けるヘッダ: Bearer / X-Api-Key / api-key
    for h in ({"Authorization": "Bearer testkey"},
              {"X-Api-Key": "testkey"}, {"api-key": "testkey"}):
        st, body, _ = _req(port, "POST", "/mcp", MCP_INIT, h)
        assert st == 200, h


def test_multiple_keys_accepted(make_server):
    # セッショントークン + QGIS_LIVE_API_KEY 等の複数キーが併存できる
    port = make_server(api_keys={"k1", "k2"})
    for key in ("k1", "k2"):
        st, _, _ = _req(port, "POST", "/mcp", MCP_INIT,
                        {"Authorization": f"Bearer {key}"})
        assert st == 200, key


def test_forbidden_host_and_origin(make_server):
    port = make_server(api_keys={"k"})
    auth = {"Authorization": "Bearer k"}
    # loopback以外を指すHost/Originは拒否(DNSリバインド・ブラウザ対策)
    st, _, _ = _req(port, "GET", "/api/status",
                    headers={**auth, "Host": "evil.com"})
    assert st == 403
    st, _, _ = _req(port, "GET", "/api/status",
                    headers={**auth, "Origin": "https://evil.com"})
    assert st == 403
    st, _, _ = _req(port, "GET", "/api/status",
                    headers={**auth, "Origin": "null"})
    assert st == 403
    # localhostオリジンのローカルWebアプリからは使える
    st, _, _ = _req(port, "GET", "/api/status",
                    headers={**auth, "Origin": "http://localhost:3000"})
    assert st == 200


def test_tool_filter(make_server):
    port = make_server(api_keys={"testkey"}, allowed={"status", "screenshot"})
    st, body, _ = _req(port, "POST", "/mcp", MCP_LIST, AUTH)
    names = {t["name"] for t in body["result"]["tools"]}
    assert names == {"qgis_status", "qgis_screenshot"}
    # 許可ツールは呼べる
    st, body, _ = _req(port, "POST", "/mcp", MCP_CALL("qgis_status"), AUTH)
    assert st == 200 and not body["result"].get("isError")
    # 非許可ツールは isError
    st, body, _ = _req(port, "POST", "/mcp", MCP_CALL("qgis_pyeval",
                                                    {"code": "1"}), AUTH)
    assert st == 200 and body["result"]["isError"]
    # REST側も同じフィルタが効く
    st, _, _ = _req(port, "POST", "/api/pyeval", {"code": "1"}, AUTH)
    assert st == 403
    st, _, _ = _req(port, "POST", "/api/cmd", {"type": "pyeval"}, AUTH)
    assert st == 403
    st, body, _ = _req(port, "POST", "/api/cmd", {"type": "status"}, AUTH)
    assert st == 200
    st, _, _ = _req(port, "GET", "/api/status", headers=AUTH)
    assert st == 200
    # 許可されている種別ならREST経路も通る(実行自体はフェイクがerrorを返す)
    st, body, _ = _req(port, "POST", "/api/screenshot", {}, AUTH)
    assert st == 500 and "no canvas" in body["error"]


def test_tool_filter_blocks_screenshot(make_server):
    port = make_server(api_keys={"k"}, allowed={"status"})
    st, body, _ = _req(port, "POST", "/api/screenshot", {},
                       {"Authorization": "Bearer k"})
    assert st == 403


def test_get_mcp_is_405(make_server):
    port = make_server(api_keys={"k"})
    st, _, hdrs = _req(port, "GET", "/mcp",
                       headers={"Authorization": "Bearer k"})
    assert st == 405 and hdrs.get("Allow") == "POST"
