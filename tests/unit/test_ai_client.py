"""ai_client.py のテスト。stdlibのみで動くため実QGIS不要。

ローカルのHTTPスタブに対して chat_completions の
リクエスト形式(Bearer認証・tools・URL正規化)も検証する。
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from qgis_live_driver import ai_client
from qgis_live_driver.mcp_http import TOOLS


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
    assert len(tools) == len(TOOLS)
    names = {t["function"]["name"] for t in tools}
    assert {"qgis_pyeval", "qgis_screenshot", "qgis_status"} <= names
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
    assert len(decls) == len(TOOLS)
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
    assert len(req["body"]["tools"]) == len(TOOLS)


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
        assert len(body["tools"][0]["functionDeclarations"]) == len(TOOLS)
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
