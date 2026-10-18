"""ai_client.py のテスト。stdlibのみで動くため実QGIS不要。

ローカルのHTTPスタブに対して chat_completions の
リクエスト形式(Bearer認証・tools・URL正規化)も検証する。
"""

import json
import os
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from qgis_live_driver import ai_client, credential_store
from qgis_live_driver.mcp_http import TOOLS, start_http


# ---- URL/スキーマ変換 ----

def test_endpoint_url():
    assert ai_client.endpoint_url("https://api.openai.com/v1") == \
        "https://api.openai.com/v1/chat/completions"
    assert ai_client.endpoint_url("http://localhost:11434/v1/") == \
        "http://localhost:11434/v1/chat/completions"
    assert ai_client.endpoint_url("http://x/v1/chat/completions") == \
        "http://x/v1/chat/completions"
    with pytest.raises(ai_client.ApiError):
        ai_client.endpoint_url("  ")


def test_openai_tools_schema():
    tools = ai_client.openai_tools()
    assert len(tools) == len(TOOLS) + len(ai_client.INSTRUCTION_TOOLS)
    names = {t["function"]["name"] for t in tools}
    assert {"qgis_pyeval", "qgis_screenshot", "qgis_status"} <= names
    # AIローカルの指示書ツールも含まれる
    assert ai_client.INSTRUCTION_TOOL_NAMES <= names
    for t in tools:
        assert t["type"] == "function"
        assert "parameters" in t["function"]
    # allowedフィルタ(mcp側の_http_allowedと同じ種別名)
    filtered = ai_client.openai_tools(allowed={"status"})
    assert [t["function"]["name"] for t in filtered] == ["qgis_status"]


def test_tool_to_command():
    cmd = ai_client.tool_to_command("qgis_pyeval",
                                    {"code": "1+1", "plugin_id": None})
    assert cmd == {"type": "pyeval", "code": "1+1"}  # None引数は落とす
    with pytest.raises(ai_client.ApiError):
        ai_client.tool_to_command("notqgis_x", {})


def test_command_from_tool_call():
    tc = {"id": "call_1",
          "function": {"name": "qgis_status", "arguments": "{}"}}
    name, cmd = ai_client.command_from_tool_call(tc)
    assert name == "qgis_status" and cmd == {"type": "status"}
    # 壊れたargumentsはApiError
    bad = {"function": {"name": "qgis_status", "arguments": "{oops"}}
    with pytest.raises(ai_client.ApiError):
        ai_client.command_from_tool_call(bad)


def test_trim_history():
    """長い履歴は古いターンから落とし、最新ターンは必ず残る。"""
    h = [{"role": "user", "content": "x" * 100},
         {"role": "assistant", "content": "y" * 100},
         {"role": "user", "content": "z" * 100}]
    out = ai_client.trim_history(h, max_chars=200)
    # 最新2件(y,z)のみ残る。xは落とされる
    assert [m["content"][0] for m in out] == ["y", "z"]
    # 全て収まる場合はそのまま
    assert ai_client.trim_history(h, max_chars=1000) == h
    # 1件でも上限超過なら最新ターンは残る
    big = [{"role": "user", "content": "q" * 500}]
    assert len(ai_client.trim_history(big, max_chars=10)) == 1
    assert ai_client.trim_history([]) == []


def test_reply_to_text():
    assert ai_client.reply_to_text({"id": 1, "error": "boom"}) == \
        "ERROR: boom"
    assert ai_client.reply_to_text({"id": 1, "result": "ok"}) == "ok"
    assert json.loads(ai_client.reply_to_text(
        {"id": 1, "result": {"a": 1}})) == {"a": 1}
    long = "x" * (ai_client.MAX_TOOL_RESULT_CHARS + 10)
    out = ai_client.reply_to_text({"id": 1, "result": long})
    assert "truncated" in out and len(out) < len(long) + 100


def test_image_message_content(tmp_path):
    png = tmp_path / "s.png"
    png.write_bytes(b"\x89PNG fake")
    content = ai_client.image_message_content(str(png))
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")
    # 存在しないパスはNone(テキスト結果にフォールバックする)
    assert ai_client.image_message_content(str(tmp_path / "no.png")) is None


def test_system_prompt_lists_plugins():
    p = ai_client.system_prompt(["some_plugin", "qgis_live_driver"])
    assert "some_plugin" in p and "qgis_live_driver" in p


# ---- Gemini ----

def test_gemini_url():
    m = "gemini-2.5-flash"
    assert ai_client.gemini_url("https://generativelanguage.googleapis.com/v1beta", m) == \
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    assert ai_client.gemini_url("http://x/v1beta/", m).endswith(
        f"/models/{m}:generateContent")
    # 既に:generateContentを含むURLはそのまま
    u = "http://x/v1beta/models/gemini-pro:generateContent"
    assert ai_client.gemini_url(u, m) == u
    with pytest.raises(ai_client.ApiError):
        ai_client.gemini_url(" ", m)


def test_gemini_tools_schema_uppercase():
    decls = ai_client.gemini_tools()
    assert len(decls) == len(TOOLS) + len(ai_client.INSTRUCTION_TOOLS)
    assert ai_client.INSTRUCTION_TOOL_NAMES <= {
        d["name"] for d in decls}
    pyeval = next(d for d in decls if d["name"] == "qgis_pyeval")
    params = pyeval["parameters"]
    assert params["type"] == "OBJECT"          # lowercase→UPPERCASE変換
    assert params["properties"]["code"]["type"] == "STRING"
    assert params["required"] == ["code"]
    # ARRAY型にはitemsが補われる
    bridge = next(d for d in decls if d["name"] == "qgis_bridge_call")
    assert "items" in bridge["parameters"]["properties"]["args"]
    filtered = ai_client.gemini_tools(allowed={"status"})
    assert [d["name"] for d in filtered] == ["qgis_status"]


def test_gemini_parse_and_exchange():
    prov = ai_client.get_provider("gemini")
    data = {"candidates": [{"content": {"role": "model", "parts": [
        {"text": "調べます"},
        {"functionCall": {"name": "qgis_status", "args": {}}},
        {"functionCall": {"name": "qgis_pyeval", "args": {"code": "1"}}},
    ]}}]}
    turn = prov.parse(data)
    assert turn["text"] == "調べます"
    assert [c["name"] for c in turn["calls"]] == \
        ["qgis_status", "qgis_pyeval"]
    assert turn["calls"][1]["args"] == {"code": "1"}

    msgs = []
    results = [{"text": "ok", "image": None},
               {"text": "2", "image": None}]
    prov.append_exchange(msgs, turn, results)
    # functionCallを含むmodelターン + 全functionResponseを持つ1 userターン
    assert msgs[0]["role"] == "model"
    assert msgs[1]["role"] == "user"
    frs = [p["functionResponse"] for p in msgs[1]["parts"]
           if "functionResponse" in p]
    assert [f["name"] for f in frs] == ["qgis_status", "qgis_pyeval"]
    assert frs[0]["response"] == {"result": "ok"}


def test_gemini_exchange_with_image(tmp_path):
    prov = ai_client.get_provider("gemini")
    png = tmp_path / "s.png"
    png.write_bytes(b"\x89PNG fake")
    turn = {"calls": [{"name": "qgis_screenshot", "args": {}}],
            "raw": {"role": "model", "parts": []}}
    msgs = []
    prov.append_exchange(msgs, turn,
                         [{"text": "path", "image": str(png)}])
    kinds = [set(p) for p in msgs[1]["parts"]]
    assert {"functionResponse"} in kinds and {"inlineData"} in kinds


def test_gemini_parse_blocked():
    prov = ai_client.get_provider("gemini")
    with pytest.raises(ai_client.ApiError):
        prov.parse({"candidates": [{"finishReason": "SAFETY",
                                    "content": {"parts": []}}]})


def test_models_url():
    assert ai_client.openai_models_url("https://api.openai.com/v1") == \
        "https://api.openai.com/v1/models"
    assert ai_client.openai_models_url("http://x/v1/chat/completions") == \
        "http://x/v1/models"
    assert ai_client.gemini_models_url(
        "https://generativelanguage.googleapis.com/v1beta") == \
        "https://generativelanguage.googleapis.com/v1beta/models"
    assert ai_client.gemini_models_url(
        "http://x/v1beta/models/gemini-pro:generateContent") == \
        "http://x/v1beta/models"
    with pytest.raises(ai_client.ApiError):
        ai_client.openai_models_url(" ")
    with pytest.raises(ai_client.ApiError):
        ai_client.gemini_models_url(" ")


def test_provider_registry():
    assert ai_client.get_provider("openai").id == "openai"
    assert ai_client.get_provider("gemini").id == "gemini"
    assert ai_client.get_provider("copilot").id == "copilot"
    with pytest.raises(ai_client.ApiError):
        ai_client.get_provider("nope")
    assert ai_client.provider_defaults("gemini")["model"] == \
        ai_client.GEMINI_DEFAULT_MODEL


# ---- HTTPクライアント ----

class _StubHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        self.server.last_req = {
            "path": self.path,
            "auth": self.headers.get("Authorization"),
            "body": json.loads(body.decode("utf-8")),
        }
        resp = {"choices": [{"message": {"role": "assistant",
                                        "content": "hi"}}]}
        raw = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


@pytest.fixture
def stub_server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _StubHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield httpd
    httpd.shutdown()


def test_chat_completions_request(stub_server):
    port = stub_server.server_address[1]
    resp = ai_client.chat_completions(
        f"http://127.0.0.1:{port}/v1", "secret-key", "mymodel",
        [{"role": "user", "content": "hello"}],
        tools=ai_client.openai_tools())
    assert resp["choices"][0]["message"]["content"] == "hi"
    req = stub_server.last_req
    assert req["path"] == "/v1/chat/completions"
    assert req["auth"] == "Bearer secret-key"
    assert req["body"]["model"] == "mymodel"
    assert req["body"]["tool_choice"] == "auto"
    assert len(req["body"]["tools"]) == \
        len(TOOLS) + len(ai_client.INSTRUCTION_TOOLS)


def test_chat_completions_no_key(stub_server):
    port = stub_server.server_address[1]
    ai_client.chat_completions(
        f"http://127.0.0.1:{port}", "", "m",
        [{"role": "user", "content": "x"}])
    assert stub_server.last_req["auth"] is None


def test_chat_completions_http_error(stub_server):
    class _Err(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            self.send_response(400)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Err)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        with pytest.raises(ai_client.ApiError) as ei:
            ai_client.chat_completions(
                f"http://127.0.0.1:{httpd.server_address[1]}", "k", "m", [])
        assert "HTTP 400" in str(ei.value)
    finally:
        httpd.shutdown()


# ---- Gemini HTTP ----

class _GeminiStub(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        self.server.last_req = {
            "path": self.path,
            "key": self.headers.get("x-goog-api-key"),
            "body": json.loads(body.decode("utf-8")),
        }
        resp = {"candidates": [{"content": {
            "role": "model", "parts": [{"text": "hi"}]}}]}
        raw = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def test_gemini_generate_request():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _GeminiStub)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        port = httpd.server_address[1]
        prov = ai_client.get_provider("gemini")
        data = prov.send(f"http://127.0.0.1:{port}/v1beta", "g-key",
                         "gemini-x", "sys prompt",
                         [{"role": "user", "parts": [{"text": "hello"}]}])
        assert prov.parse(data)["text"] == "hi"
        req = httpd.last_req
        assert req["path"] == \
            "/v1beta/models/gemini-x:generateContent"
        assert req["key"] == "g-key"
        body = req["body"]
        assert body["systemInstruction"]["parts"][0]["text"] == "sys prompt"
        assert body["contents"][0]["parts"][0]["text"] == "hello"
        assert "functionDeclarations" in body["tools"][0]
        assert len(body["tools"][0]["functionDeclarations"]) == \
            len(TOOLS) + len(ai_client.INSTRUCTION_TOOLS)
    finally:
        httpd.shutdown()


# ---- モデル一覧取得 ----

class _ModelsStub(BaseHTTPRequestHandler):
    """GET /models に対して OpenAI形式 or Gemini形式の一覧を返す。"""

    def log_message(self, *a):
        pass

    def do_GET(self):
        self.server.last_req = {
            "path": self.path,
            "auth": self.headers.get("Authorization"),
            "key": self.headers.get("x-goog-api-key"),
        }
        if self.path.startswith("/v1beta"):
            resp = {"models": [
                {"name": "models/gemini-b",
                 "supportedGenerationMethods": ["generateContent"],
                 "inputTokenLimit": 1048576},
                {"name": "models/embed-a",
                 "supportedGenerationMethods": ["embedContent"]},
                {"name": "models/gemini-a"},  # methods無しは含める
            ]}
        else:
            resp = {"data": [
                {"id": "m2"},
                {"id": "m1",
                 "pricing": {"prompt": "0.00000015",
                             "completion": "0.0000006"},
                 "context_length": 128000,
                 "architecture": {"modality": "text+image->text"}},
                {"noid": 1}]}
        raw = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


@pytest.fixture
def models_server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _ModelsStub)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield httpd
    httpd.shutdown()


def test_openai_list_models(models_server):
    port = models_server.server_address[1]
    models = ai_client.list_models(
        "openai", f"http://127.0.0.1:{port}/v1", "k")
    assert models == ["m1", "m2"]
    assert models_server.last_req["path"] == "/v1/models"
    assert models_server.last_req["auth"] == "Bearer k"


def test_gemini_list_models(models_server):
    port = models_server.server_address[1]
    models = ai_client.list_models(
        "gemini", f"http://127.0.0.1:{port}/v1beta", "g-key")
    # embed-a は generateContent 非対応なので除外
    assert models == ["gemini-a", "gemini-b"]
    assert models_server.last_req["path"] == "/v1beta/models"
    assert models_server.last_req["key"] == "g-key"


# ---- モデルの種別・価格メタ情報 ----

def test_classify_model():
    c = ai_client.classify_model
    assert c("gpt-4o-mini") == "chat_vision"
    assert c("o3") == "chat_vision"
    assert c("gpt-3.5-turbo") == "chat"
    assert c("dall-e-3") == "image"
    assert c("google/gemini-2.5-flash-image") == "image"
    assert c("text-embedding-3-large") == "embed"
    assert c("whisper-1") == "other"
    assert c("anthropic/claude-sonnet-4") == "chat_vision"
    # API応答のmodalityは名前ヒントより優先
    assert c("strange-name", {"modality": "text+image->text"}) == \
        "chat_vision"
    assert c("strange-name", {"modality": "text->image"}) == "image"
    assert c("strange-name",
             {"input_modalities": ["text", "image"]}) == "chat_vision"


def test_model_info_price():
    # API応答のpricing(USD/token)を1Mトークンあたりに変換
    i = ai_client.model_info({
        "id": "openai/gpt-4o-mini",
        "pricing": {"prompt": "0.00000015", "completion": "0.0000006"},
        "context_length": 128000,
        "modality": "text+image->text"})
    assert i["kind"] == "chat_vision"
    assert i["price"] == "$0.15/$0.60"
    assert i["price_src"] == "api"
    assert i["context"] == 128000
    # 価格を返さないAPIでは既知価格表の参考値にフォールバック
    k = ai_client.model_info({"id": "gpt-4o-mini-2024-07-18"})
    assert k["price_src"] == "known" and k["price"] == "$0.15/$0.60"
    # 未知モデルは価格無し・chat判定
    u = ai_client.model_info({"id": "some-local-model"})
    assert u["price"] is None and u["kind"] == "chat"


def test_parse_usage_and_cost():
    # OpenAI形式: usage.prompt_tokens/completion_tokens
    prov = ai_client.get_provider("openai")
    data = {"choices": [{"message": {"content": "hi"}}],
            "usage": {"prompt_tokens": 1200, "completion_tokens": 30}}
    turn = prov.parse(data)
    assert turn["usage"] == {"in": 1200, "out": 30}
    # usageが無い応答ではNone
    assert ai_client.get_provider("openai").parse(
        {"choices": [{"message": {"content": "x"}}]})["usage"] is None
    # Gemini形式: usageMetadata(+thoughtsTokenCountは出力側へ)
    g = ai_client.get_provider("gemini")
    gd = {"candidates": [{"content": {"parts": [{"text": "x"}]}}],
          "usageMetadata": {"promptTokenCount": 500,
                            "candidatesTokenCount": 40,
                            "thoughtsTokenCount": 10}}
    assert g.parse(gd)["usage"] == {"in": 500, "out": 50}
    # parse_usage単体
    assert ai_client.parse_usage({}) is None
    # コスト: price_usd(1Mあたり)×usage
    info = ai_client.model_info({"id": "openai/gpt-4o-mini", "pricing": {
        "prompt": "0.00000015", "completion": "0.0000006"}})
    assert info["price_usd"] == (0.15, 0.6)
    cost = ai_client.usage_cost(info, {"in": 1_000_000, "out": 500_000})
    assert cost == pytest.approx(0.15 + 0.30)
    # 価格不明モデルはNone(Copilot等の定額制もこちら)
    assert ai_client.usage_cost(
        ai_client.model_info({"id": "x"}), {"in": 1, "out": 1}) is None


def test_fmt_tokens_and_label():
    assert ai_client.fmt_tokens(128000) == "128k"
    assert ai_client.fmt_tokens(1048576) == "1.0M"
    info = ai_client.model_info({"id": "gpt-4o-mini"})
    label = ai_client.model_label(info)
    assert label.startswith("gpt-4o-mini") and "$" in label
    assert "種別" in ai_client.model_tooltip(info)


def test_openai_list_model_infos(models_server):
    port = models_server.server_address[1]
    infos = ai_client.list_model_infos(
        "openai", f"http://127.0.0.1:{port}/v1", "k")
    m1 = next(i for i in infos if i["id"] == "m1")
    assert m1["kind"] == "chat_vision"     # architecture.modality由来
    assert m1["price_src"] == "api"
    assert m1["price"] == "$0.15/$0.60"
    assert m1["context"] == 128000
    m2 = next(i for i in infos if i["id"] == "m2")
    assert m2["price"] is None and m2["kind"] == "chat"


def test_gemini_list_model_infos(models_server):
    port = models_server.server_address[1]
    infos = ai_client.list_model_infos(
        "gemini", f"http://127.0.0.1:{port}/v1beta", "g-key")
    assert [i["id"] for i in infos] == ["gemini-a", "gemini-b"]
    gb = next(i for i in infos if i["id"] == "gemini-b")
    assert gb["kind"] == "chat_vision"     # gemini名ヒント
    assert gb["context"] == 1048576


# ---- GitHub Copilot ----

class _CopilotStub(BaseHTTPRequestHandler):
    """copilot_internalトークン交換・Copilot API・OAuthの統合スタブ。"""

    def log_message(self, *a):
        pass

    def _json(self, resp):
        raw = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _record(self):
        self.server.reqs.append({
            "path": self.path,
            "auth": self.headers.get("Authorization"),
            "editor": self.headers.get("Editor-Version"),
        })

    def do_GET(self):
        self._record()
        port = self.server.server_address[1]
        if "/copilot_internal/v2/token" in self.path:
            if getattr(self.server, "v2_fail", False):
                self.send_response(404)
                self.end_headers()
                return
            self._json({"token": "ct-1", "expires_at": time.time() + 1800,
                        "endpoints": {"api": f"http://127.0.0.1:{port}"}})
        elif "/copilot_internal/user" in self.path:
            self._json({"copilot_plan": "business",
                        "endpoints": {"api": f"http://127.0.0.1:{port}"}})
        elif self.path == "/models":
            self._json({"data": [
                {"id": "gpt-4o",
                 "capabilities": {"type": "chat",
                     "limits": {"max_context_window_tokens": 128000},
                     "supports": {"tool_calls": True, "vision": True}},
                 "policy": {"state": "enabled"}},
                {"id": "embed-x", "capabilities": {"type": "embedding"}},
                {"id": "off-m", "capabilities": {"type": "chat"},
                 "policy": {"state": "disabled"}},
                {"id": "plain-m"}]})
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        self._record()
        if self.path == "/login/device/code":
            self.server.last_form = urllib.parse.parse_qs(body.decode())
            self._json({"device_code": "dc-1", "user_code": "ABCD-1234",
                        "verification_uri":
                            "https://github.com/login/device",
                        "interval": 5, "expires_in": 900})
        elif self.path == "/login/oauth/access_token":
            self.server.last_form = urllib.parse.parse_qs(body.decode())
            self._json({"access_token": "gho_test",
                        "token_type": "bearer"})
        else:
            self.server.last_json = json.loads(body.decode())
            self._json({"choices": [{"message": {"role": "assistant",
                                                 "content": "hi"}}]})


@pytest.fixture
def copilot_server(monkeypatch):
    """Copilot系URLをスタブへ向け、トークンキャッシュをクリアする。"""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _CopilotStub)
    httpd.reqs = []
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_address[1]
    ai_client._COPILOT_CACHE.clear()
    monkeypatch.setattr(
        ai_client, "COPILOT_TOKEN_URL",
        f"http://127.0.0.1:{port}/copilot_internal/v2/token")
    monkeypatch.setattr(
        ai_client, "COPILOT_USER_URL",
        f"http://127.0.0.1:{port}/copilot_internal/user")
    monkeypatch.setattr(
        ai_client, "GITHUB_DEVICE_CODE_URL",
        f"http://127.0.0.1:{port}/login/device/code")
    monkeypatch.setattr(
        ai_client, "GITHUB_ACCESS_TOKEN_URL",
        f"http://127.0.0.1:{port}/login/oauth/access_token")
    yield httpd
    httpd.shutdown()
    ai_client._COPILOT_CACHE.clear()


def test_copilot_send_exchanges_token(copilot_server):
    """既定base: GitHubトークンをCopilotトークンに交換して送信。"""
    prov = ai_client.get_provider("copilot")
    msgs = [{"role": "user", "content": "hello"}]
    data = prov.send("https://api.githubcopilot.com", "gh-tok",
                     "gpt-4o", "sys", msgs)
    assert data["choices"][0]["message"]["content"] == "hi"
    exch = next(r for r in copilot_server.reqs
                if "copilot_internal" in r["path"])
    assert exch["auth"] == "token gh-tok"
    post = next(r for r in copilot_server.reqs
                if r["path"] == "/chat/completions")
    assert post["auth"] == "Bearer ct-1"     # 交換後トークンで認証
    assert post["editor"]                    # Copilot用クライアントヘッダ
    assert copilot_server.last_json["tools"]  # function calling付き
    # 2回目はキャッシュで交換APIを呼ばない
    prov.send("https://api.githubcopilot.com", "gh-tok", "gpt-4o",
              "sys", msgs)
    assert len([r for r in copilot_server.reqs
                if "copilot_internal" in r["path"]]) == 1


def test_copilot_passthrough_custom_base(copilot_server):
    """既定外エンドポイント(copilot-api互換プロキシ)は交換せず
    GitHubトークンをそのままBearerに使う。"""
    port = copilot_server.server_address[1]
    prov = ai_client.get_provider("copilot")
    prov.send(f"http://127.0.0.1:{port}/v1", "gh-tok", "m", "s",
              [{"role": "user", "content": "x"}])
    assert not any("copilot_internal" in r["path"]
                   for r in copilot_server.reqs)
    post = copilot_server.reqs[-1]
    assert post["path"] == "/v1/chat/completions"
    assert post["auth"] == "Bearer gh-tok"


def test_copilot_list_model_entries(copilot_server):
    infos = ai_client.list_model_infos(
        "copilot", "https://api.githubcopilot.com", "gh-tok")
    # embedding型とpolicy=disabledは除外。capabilities無しは採用
    assert [i["id"] for i in infos] == ["gpt-4o", "plain-m"]
    g = next(i for i in infos if i["id"] == "gpt-4o")
    assert g["kind"] == "chat_vision"     # supports.vision由来
    assert g["context"] == 128000
    exch = next(r for r in copilot_server.reqs
                if "copilot_internal" in r["path"])
    assert exch["auth"] == "token gh-tok"


def test_copilot_missing_key():
    prov = ai_client.get_provider("copilot")
    with pytest.raises(ai_client.ApiError):
        prov.send("https://api.githubcopilot.com", "", "m", "s", [])


def test_copilot_user_endpoint_fallback(copilot_server):
    """v2/tokenが404の環境では copilot_internal/user でAPI先を解決し、
    GitHubトークンをそのままBearerに使う(CLI方式)。"""
    copilot_server.v2_fail = True
    prov = ai_client.get_provider("copilot")
    data = prov.send("https://api.githubcopilot.com", "gh-tok",
                     "m", "s", [{"role": "user", "content": "x"}])
    assert data["choices"][0]["message"]["content"] == "hi"
    paths = [r["path"] for r in copilot_server.reqs]
    assert "/copilot_internal/user" in " ".join(paths)
    post = next(r for r in copilot_server.reqs
                if r["path"] == "/chat/completions")
    assert post["auth"] == "Bearer gh-tok"    # 生トークンで直接認証


def test_copilot_auth_failure(copilot_server, monkeypatch):
    """トークン交換も契約情報も失敗する場合はApiError。"""
    copilot_server.v2_fail = True  # v2/tokenを404にしてfallbackさせる

    class _DenyAll(_CopilotStub):
        def do_GET(self):
            self._record()
            self.send_response(401)
            self.end_headers()

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _DenyAll)
    httpd.reqs = []
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        monkeypatch.setattr(
            ai_client, "COPILOT_USER_URL",
            f"http://127.0.0.1:{httpd.server_address[1]}/u")
        with pytest.raises(ai_client.ApiError) as ei:
            ai_client.copilot_session(
                "bad-tok", "https://api.githubcopilot.com")
        assert "401" in str(ei.value)
    finally:
        httpd.shutdown()


def test_github_device_flow(copilot_server):
    d = ai_client.github_device_code()
    assert d["device_code"] == "dc-1" and d["user_code"] == "ABCD-1234"
    f = copilot_server.last_form
    assert f["client_id"][0] == ai_client.GITHUB_CLIENT_ID
    assert f["scope"] == ["read:user"]
    r = ai_client.github_poll_access_token(d["device_code"])
    assert r["access_token"] == "gho_test"
    f = copilot_server.last_form
    assert f["device_code"] == ["dc-1"]
    assert f["grant_type"] == [
        "urn:ietf:params:oauth:grant-type:device_code"]


# ---- エージェント/スキル(指示書ファイル) ----

def test_agents_roundtrip(tmp_path, monkeypatch):
    """agents/*.md の作成→一覧→読込→削除。"""
    monkeypatch.setenv("QGIS_LIVE_REGISTRY", str(tmp_path))
    assert ai_client.list_agents() == []
    p = ai_client.save_agent("テスト agent",
                             "# 地図士\n\n日本語で簡潔に答える")
    assert p.endswith("テスト_agent.md")  # 空白は_に置換
    agents = ai_client.list_agents()
    assert [a["id"] for a in agents] == ["テスト_agent"]
    a = agents[0]
    assert a["title"] == "地図士"          # 先頭の # 行
    assert a["desc"] == "日本語で簡潔に答える"
    assert not a["builtin"]
    assert "地図士" in ai_client.load_agent("テスト_agent")
    assert ai_client.load_agent("nonexistent") is None
    assert ai_client.load_agent(None) is None
    assert ai_client.delete_agent("テスト_agent")
    assert ai_client.list_agents() == []


def test_bundled_skill_listed(tmp_path, monkeypatch):
    """プラグイン同梱のskills/がbuiltinフラグ付きで列挙される。"""
    monkeypatch.setenv("QGIS_LIVE_REGISTRY", str(tmp_path))
    s = next(s for s in ai_client.list_skills()
             if s["id"] == "qgis-basics")
    assert s["builtin"] and s["title"] and s["desc"]


def test_user_skill_overrides_bundled(tmp_path, monkeypatch):
    """ユーザ側の同名.mdはbundledを上書きする。"""
    monkeypatch.setenv("QGIS_LIVE_REGISTRY", str(tmp_path))
    d = ai_client.skills_dir()
    os.makedirs(d)
    with open(os.path.join(d, "qgis-basics.md"), "w",
              encoding="utf-8") as f:
        f.write("# カスタム\n\n説明X\n")
    s = next(s for s in ai_client.list_skills()
             if s["id"] == "qgis-basics")
    assert not s["builtin"]
    assert s["title"] == "カスタム"


def test_system_prompt_agent_and_skills(tmp_path, monkeypatch):
    """agent_textは常時注入、skillsはパス+説明のみ載る。"""
    monkeypatch.setenv("QGIS_LIVE_REGISTRY", str(tmp_path))
    p = ai_client.system_prompt(["x"], agent_text="Be brief",
                                skills=ai_client.list_skills())
    assert "Be brief" in p
    assert "qgis-basics" in p and "open()" in p
    # 本文は載らない(ファイルを読ませる方式)
    assert "QgsProject.instance()" not in p


def test_system_prompt_agent_list(tmp_path, monkeypatch):
    """agents一覧はid+説明のみ載り、選択中は[active]が付く。"""
    monkeypatch.setenv("QGIS_LIVE_REGISTRY", str(tmp_path))
    ai_client.save_agent("mapper", "# 地図士\n\n地図デザイン専門")
    ai_client.save_agent("coder", "# 開発者\n\nコード重視")
    p = ai_client.system_prompt(
        ["x"],
        agent_text=ai_client.load_agent("mapper"),
        agents=ai_client.list_agents(),
        active_agent="mapper")
    assert "## Agents" in p
    assert "mapper: 地図デザイン専門 [active]" in p
    assert "coder: コード重視" in p and "[active]" not in \
        next(l for l in p.splitlines() if "coder" in l)
    assert "ai_select_agent" in p


def test_instruction_tool_roundtrip(tmp_path, monkeypatch):
    """ai_*ツール: 一覧→保存→読込→削除。"""
    monkeypatch.setenv("QGIS_LIVE_REGISTRY", str(tmp_path))
    out = ai_client.run_instruction_tool(
        "ai_list_instructions", {"kind": "agents"})
    assert out == "(なし)"
    out = ai_client.run_instruction_tool(
        "ai_save_instruction",
        {"kind": "skills", "name": "レシピ a",
         "text": "# レシピ\n\n説明\n\n手順"})
    assert "レシピ_a.md" in out and out.startswith("saved:")
    out = ai_client.run_instruction_tool(
        "ai_read_instruction", {"kind": "skills", "id": "レシピ_a"})
    assert "手順" in out
    out = ai_client.run_instruction_tool(
        "ai_delete_instruction", {"kind": "skills", "id": "レシピ_a"})
    assert "deleted" in out
    with pytest.raises(ai_client.ApiError):
        ai_client.run_instruction_tool(
            "ai_read_instruction", {"kind": "skills", "id": "レシピ_a"})


def test_instruction_tool_errors(tmp_path, monkeypatch):
    """ai_*ツール: 引数不正・同梱品削除はApiError。"""
    monkeypatch.setenv("QGIS_LIVE_REGISTRY", str(tmp_path))
    with pytest.raises(ai_client.ApiError):
        ai_client.run_instruction_tool(
            "ai_list_instructions", {"kind": "bogus"})
    with pytest.raises(ai_client.ApiError):
        ai_client.run_instruction_tool(
            "ai_save_instruction",
            {"kind": "agents", "name": "x"})  # text無し
    # 同梱品は削除できない
    with pytest.raises(ai_client.ApiError) as ei:
        ai_client.run_instruction_tool(
            "ai_delete_instruction",
            {"kind": "skills", "id": "qgis-basics"})
    assert "削除できません" in str(ei.value)
    with pytest.raises(ai_client.ApiError):
        ai_client.run_instruction_tool("ai_nope", {"kind": "agents"})
    # 選択ツールはパネル専用(ファイル層では扱わない)
    with pytest.raises(ai_client.ApiError):
        ai_client.run_instruction_tool("ai_select_agent", {"id": "x"})


# ---- 外部MCPクライアント ----

def test_iter_rpc_msgs_sse():
    """SSE形式とJSON形式の両方からJSON-RPCを取り出せる。"""
    raw = ('data: {"jsonrpc":"2.0","id":1,"result":{"a":1}}\n\n'
           'data: {"jsonrpc":"2.0",\n'
           'data: "id":2,"result":{"b":2}}\n\n')
    msgs = list(ai_client._iter_rpc_msgs(raw, "text/event-stream"))
    assert [m["id"] for m in msgs] == [1, 2]
    msgs = list(ai_client._iter_rpc_msgs(
        '{"id":1,"result":{}}', "application/json"))
    assert msgs[0]["id"] == 1


def test_mcp_result_text():
    r = {"content": [{"type": "text", "text": "a"},
                     {"type": "text", "text": "b"}]}
    assert ai_client._mcp_result_text(r) == "a\nb"
    with pytest.raises(ai_client.ApiError):
        ai_client._mcp_result_text(
            {"isError": True,
             "content": [{"type": "text", "text": "boom"}]})


def test_mcp_config_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("QGIS_LIVE_REGISTRY", str(tmp_path))
    assert ai_client.mcp_servers_config() == {}      # 未設定は空
    ai_client.mcp_save_config(json.dumps({"mcpServers": {
        "fs": {"command": "npx", "args": ["-y", "srv"]},
        "bad": {"x": 1},                              # command/url無しは除外
        "api": {"url": "http://localhost:9/mcp"}}}))
    cfg = ai_client.mcp_servers_config()
    assert set(cfg) == {"fs", "api"}
    with pytest.raises(ai_client.ApiError):
        ai_client.mcp_save_config("{not json")
    with pytest.raises(ai_client.ApiError):
        ai_client.mcp_save_config('{"servers": {}}')  # 形式違い


class _McpFakeDriver:
    def submit(self, cmd, timeout=180.0):
        return {"id": cmd.get("id"), "result": {"echo": cmd.get("type")}}


def test_mcp_http_session(tmp_path, monkeypatch):
    """実MCPサーバ(自前のmcp_http)へのStreamable HTTPセッション。"""
    monkeypatch.setenv("QGIS_LIVE_REGISTRY", str(tmp_path))
    httpd, port = start_http(_McpFakeDriver(), api_keys={"k"})
    try:
        sess = ai_client.McpSession(
            "t", {"url": f"http://127.0.0.1:{port}/mcp",
                  "headers": {"Authorization": "Bearer k"}}, timeout=10)
        try:
            names = {t["name"] for t in sess.tools}
            assert "qgis_status" in names
            assert "echo" in sess.call("qgis_status", {})
        finally:
            sess.close()
    finally:
        httpd.shutdown()


_STDIO_STUB = (
    "import sys, json\n"
    "for line in sys.stdin:\n"
    "    try:\n"
    "        m = json.loads(line)\n"
    "    except Exception:\n"
    "        continue\n"
    "    mid, meth = m.get('id'), m.get('method')\n"
    "    if mid is None:\n"
    "        continue\n"
    "    if meth == 'initialize':\n"
    "        res = {'protocolVersion': '2025-03-26', 'capabilities': {}}\n"
    "    elif meth == 'tools/list':\n"
    "        res = {'tools': [{'name': 'echo', 'description': 'd',"
    " 'inputSchema': {'type': 'object'}"
    "}]}\n"
    "    elif meth == 'tools/call':\n"
    "        res = {'content': [{'type': 'text', 'text':"
    " 'echo:' + json.dumps(m['params'].get('arguments'))}]}\n"
    "    else:\n"
    "        res = {}\n"
    "    sys.stdout.write(json.dumps("
    "{'jsonrpc': '2.0', 'id': mid, 'result': res}) + chr(10))\n"
    "    sys.stdout.flush()\n")


def test_mcp_stdio_session():
    """python子プロセスのstdio MCPスタブと往復できる。"""
    sess = ai_client.McpSession(
        "s", {"command": sys.executable,
              "args": ["-u", "-c", _STDIO_STUB]}, timeout=20)
    try:
        assert [t["name"] for t in sess.tools] == ["echo"]
        assert "echo:" in sess.call("echo", {"t": "hi"})
    finally:
        sess.close()


def test_mcp_discover(tmp_path, monkeypatch):
    """設定の各サーバへ接続し、失敗はerrorsへ分離する。"""
    monkeypatch.setenv("QGIS_LIVE_REGISTRY", str(tmp_path))
    httpd, port = start_http(_McpFakeDriver(), api_keys={"k"})
    try:
        ai_client.mcp_save_config(json.dumps({"mcpServers": {
            "live": {"url": f"http://127.0.0.1:{port}/mcp",
                     "headers": {"Authorization": "Bearer k"}},
            "dead": {"url": "http://127.0.0.1:9/mcp"}}}))
        r = ai_client.mcp_discover(timeout=5)
        assert "live" in r["sessions"]
        assert "dead" in r["errors"]
        assert any(t["name"].startswith("mcp_live__qgis_")
                   for t in r["tools"])
        for s in r["sessions"].values():
            s.close()
    finally:
        httpd.shutdown()


class _TokenHandler(BaseHTTPRequestHandler):
    """OAuth client_credentials用の最小トークンエンドポイント。"""

    def do_POST(self):
        import base64
        n = int(self.headers.get("Content-Length") or 0)
        body = urllib.parse.parse_qs(
            self.rfile.read(n).decode("utf-8"))
        auth = self.headers.get("Authorization", "")
        ok = (body.get("grant_type") == ["client_credentials"]
              and auth == "Basic " + base64.b64encode(
                  b"cid:csec").decode()
              # oauth.extra の追加パラメータがボディへ届くこと
              and body.get("box_subject_type") == ["enterprise"])
        out = ({"access_token": "otk", "expires_in": 3600}
               if ok else {"error": "invalid_client"})
        data = json.dumps(out).encode()
        self.send_response(200 if ok else 401)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def test_mcp_http_oauth(tmp_path):
    """oauth(client_id/secret)でトークンを取りBearer付きでMCP呼出。"""
    tokd = ThreadingHTTPServer(("127.0.0.1", 0), _TokenHandler)
    threading.Thread(target=tokd.serve_forever, daemon=True).start()
    # MCP側は "otk" を要求
    httpd, port = start_http(_McpFakeDriver(), api_keys={"otk"})
    try:
        tport = tokd.server_address[1]
        sess = ai_client.McpSession(
            "o", {"url": f"http://127.0.0.1:{port}/mcp",
                  "oauth": {
                      "token_url":
                          f"http://127.0.0.1:{tport}/oauth/token",
                      "client_id": "cid",
                      "client_secret": "csec",
                      "extra": {"box_subject_type": "enterprise"}}},
            timeout=10)
        try:
            assert "qgis_status" in {t["name"] for t in sess.tools}
            assert sess._io._tok == "otk"
            assert "echo" in sess.call("qgis_status", {})
        finally:
            sess.close()
    finally:
        httpd.shutdown()
        tokd.shutdown()


def test_mcp_secret_store_migration(tmp_path, monkeypatch):
    """平文client_secretは保存時に資格情報ストアへ移され$store:参照になる。"""
    monkeypatch.setenv("QGIS_LIVE_REGISTRY", str(tmp_path))
    out = ai_client.mcp_save_config(json.dumps({"mcpServers": {
        "box": {"url": "https://mcp.box.com",
                "oauth": {
                    "token_url": "https://api.box.com/oauth2/token",
                    "client_id": "cid",
                    "client_secret": "csec"}},
        "tmpl": {"url": "http://x/mcp",
                 "oauth": {"client_id": "<id>",
                           "client_secret": "<Client Secret>"}},
        "ref": {"url": "http://x/mcp",
                "oauth": {"client_secret": "$store:mcp:x:client_secret"}}}}))
    d = json.loads(out)["mcpServers"]
    ref = d["box"]["oauth"]["client_secret"]
    assert ref == "$store:mcp:box:client_secret"
    # 雛形の <...> と既存の $store: 参照はそのまま
    assert d["tmpl"]["oauth"]["client_secret"] == "<Client Secret>"
    assert d["ref"]["oauth"]["client_secret"] == \
        "$store:mcp:x:client_secret"
    # ファイルにも平文が残らない
    with open(ai_client.mcp_config_path(), encoding="utf-8") as f:
        assert "csec" not in f.read()
    assert credential_store.get_secret("mcp:box:client_secret") == "csec"


def test_mcp_secret_store_unresolved(tmp_path, monkeypatch):
    """$store:参照先が無ければエラー。"""
    monkeypatch.setenv("QGIS_LIVE_REGISTRY", str(tmp_path))
    with pytest.raises(ai_client.ApiError):
        ai_client._resolve_secret_ref("$store:mcp:none:client_secret")
    # 参照でない値は素通し
    assert ai_client._resolve_secret_ref("plain") == "plain"


def test_mcp_oauth_secret_ref(tmp_path, monkeypatch):
    """$store:参照のclient_secretでもBasic認証でトークン取得できる。"""
    monkeypatch.setenv("QGIS_LIVE_REGISTRY", str(tmp_path))
    assert credential_store.set_secret("mcp:o:client_secret", "csec")
    tokd = ThreadingHTTPServer(("127.0.0.1", 0), _TokenHandler)
    threading.Thread(target=tokd.serve_forever, daemon=True).start()
    httpd, port = start_http(_McpFakeDriver(), api_keys={"otk"})
    try:
        tport = tokd.server_address[1]
        sess = ai_client.McpSession(
            "o", {"url": f"http://127.0.0.1:{port}/mcp",
                  "oauth": {
                      "token_url":
                          f"http://127.0.0.1:{tport}/oauth/token",
                      "client_id": "cid",
                      "client_secret": "$store:mcp:o:client_secret",
                      "extra": {"box_subject_type": "enterprise"}}},
            timeout=10)
        try:
            assert sess._io._tok == "otk"
            assert "echo" in sess.call("qgis_status", {})
        finally:
            sess.close()
    finally:
        httpd.shutdown()
        tokd.shutdown()


class _AuthCodeTokenHandler(BaseHTTPRequestHandler):
    """authorization_code交換用の最小トークンエンドポイント。"""

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = urllib.parse.parse_qs(
            self.rfile.read(n).decode("utf-8"))
        ok = (body.get("grant_type") == ["authorization_code"]
              and body.get("code") == ["authcode-1"]
              and body.get("code_verifier")
              and body.get("redirect_uri"))
        out = ({"access_token": "utok", "refresh_token": "rtok",
                "expires_in": 3600} if ok
               else {"error": "invalid_grant"})
        data = json.dumps(out).encode()
        self.send_response(200 if ok else 400)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def test_mcp_http_oauth_authcode(tmp_path, monkeypatch):
    """authorization_code+PKCE: ブラウザ同意を模擬しトークン交換→
    MCP呼出→トークン永続化まで。"""
    import socket
    import urllib.request
    monkeypatch.setenv("QGIS_LIVE_REGISTRY", str(tmp_path))
    tokd = ThreadingHTTPServer(("127.0.0.1", 0), _AuthCodeTokenHandler)
    threading.Thread(target=tokd.serve_forever, daemon=True).start()
    httpd, port = start_http(_McpFakeDriver(), api_keys={"utok"})
    # 空きポートを拾って redirect_uri に使う
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    cb_port = s.getsockname()[1]
    s.close()

    opened = []

    def fake_open(url):
        opened.append(url)
        q = urllib.parse.parse_qs(
            urllib.parse.urlparse(url).query)
        assert q["code_challenge_method"] == ["S256"]
        assert q["code_challenge"]
        # 認可サーバの応答=コールバックへのリダイレクトを模擬
        urllib.request.urlopen(
            q["redirect_uri"][0] + "?" + urllib.parse.urlencode(
                {"code": "authcode-1", "state": q["state"][0]}),
            timeout=5).read()

    monkeypatch.setattr(ai_client.webbrowser, "open", fake_open)
    try:
        tport = tokd.server_address[1]
        sess = ai_client.McpSession(
            "o", {"url": f"http://127.0.0.1:{port}/mcp",
                  "oauth": {
                      "authorize_url":
                          f"http://127.0.0.1:{tport}/authorize",
                      "token_url":
                          f"http://127.0.0.1:{tport}/oauth/token",
                      "client_id": "cid",
                      "client_secret": "csec",
                      "redirect_uri":
                          f"http://127.0.0.1:{cb_port}/callback"}},
            timeout=10)
        try:
            assert opened and "authorize" in opened[0]
            assert sess._io._tok == "utok"
            assert "echo" in sess.call("qgis_status", {})
        finally:
            sess.close()
        # トークンが永続化され、2回目はブラウザ無しで再利用される
        saved = ai_client._mcp_token_load("o")
        assert saved["access_token"] == "utok"
        assert saved["refresh_token"] == "rtok"
        opened.clear()
        sess2 = ai_client.McpSession(
            "o", {"url": f"http://127.0.0.1:{port}/mcp",
                  "oauth": {"authorize_url": "x",
                            "token_url": "x",
                            "client_id": "cid",
                            "client_secret": "csec"}},
            timeout=10)
        try:
            assert not opened      # 保存トークン再利用でブラウザ不要
            assert sess2._io._tok == "utok"
        finally:
            sess2.close()
    finally:
        httpd.shutdown()
        tokd.shutdown()


def test_extra_tools_register():
    """外部ツールがopenai_toolsに混ざりrun_extra_toolで実行できる。"""
    ai_client.register_extra_tools(
        [{"name": "mcp_x__y", "description": "d",
          "inputSchema": {"type": "object", "properties": {}}}],
        {"mcp_x__y": lambda a: f"got:{a.get('v')}"})
    try:
        names = {t["function"]["name"] for t in ai_client.openai_tools()}
        assert "mcp_x__y" in names
        assert ai_client.run_extra_tool("mcp_x__y", {"v": 1}) == "got:1"
        with pytest.raises(ai_client.ApiError):
            ai_client.run_extra_tool("mcp_no", {})
    finally:
        ai_client.register_extra_tools([], {})
