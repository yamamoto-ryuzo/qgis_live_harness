"""AIアシスタントパネル用のLLM APIクライアント(stdlibのみ)。

ai_panel.py(Qt層)から呼ばれる。QGIS/Qtに依存しないためpytest対象。

対応プロバイダ:
  - "openai": OpenAI Chat Completions 互換
    (POST {base}/chat/completions, tools=function calling)。
    Ollama・LM Studio・OpenRouter等の互換サーバも
    base URLを変えるだけで使える(例: http://localhost:11434/v1)
  - "gemini": Google Gemini API
    (POST {base}/models/{model}:generateContent, functionDeclarations。
    認証は x-goog-api-key ヘッダ)

ツール定義は mcp_http.TOOLS(MCP/RESTと同一)を各プロバイダの
スキーマに変換して使う。実行は LiveDriver.submit() に委譲するため
このモジュール自体はQGISを触らない。

プロバイダ抽象化: OpenAIProvider/GeminiProvider が
  build_messages / send / parse / append_exchange を実装し、
ai_panel のエージェントループはプロバイダ非依存で回る。
"""

import base64
import json
import os
import tempfile
import urllib.error
import urllib.request
import uuid

from .mcp_http import TOOLS

# 1ユーザメッセージに対するツール実行の最大往復数(暴走防止)
MAX_TOOL_ROUNDS = 25

# ツール結果としてモデルに返すテキストの上限(超過分は切り詰め)
MAX_TOOL_RESULT_CHARS = 6000

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"

GEMINI_DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_DEFAULT_MODEL = "gemini-2.5-flash"

PROVIDERS = {
    "openai": {
        "label": "OpenAI互換",
        "base": DEFAULT_BASE_URL,
        "model": DEFAULT_MODEL,
        "key_hint": "APIキー (ローカルサーバ等では空可)",
        "endpoint_hint": "https://api.openai.com/v1  または  http://localhost:11434/v1",
    },
    "gemini": {
        "label": "Gemini",
        "base": GEMINI_DEFAULT_BASE_URL,
        "model": GEMINI_DEFAULT_MODEL,
        "key_hint": "Gemini APIキー (AI Studioで発行)",
        "endpoint_hint": "https://generativelanguage.googleapis.com/v1beta",
    },
}

SYSTEM_PROMPT = """\
You are an AI assistant running inside QGIS (a desktop GIS application).
You operate QGIS through the provided tools. All tools run on the local
QGIS process via its live driver.

Guidelines:
- Prefer `qgis_pyeval` for QGIS operations. The code runs in the QGIS
  GUI thread with `iface`, `QgsProject`, `QgsApplication` and `driver`
  in scope. Expressions return their value; for statements assign the
  output to a variable named `result`.
- Use `qgis_status` first if you need to know which plugins are loaded
  or whether a plugin has a WebEngine view.
- Use `qgis_screenshot` to visually check the map canvas or the main
  window after operations that change the map.
- `plugin_id` routes eval/pyeval/screenshot to another plugin's live
  driver (e.g. a WebEngine plugin's `view`). Loaded plugin ids: {plugins}
- Keep each step small and verify the result before moving on.
- Answer in the user's language.
"""


class ApiError(Exception):
    """API呼び出しの失敗(HTTP/接続/応答形式/設定不足)。"""


def provider_defaults(provider):
    """プロバイダID → {"base","model","label","key_hint","endpoint_hint"}"""
    try:
        return PROVIDERS[provider]
    except KeyError:
        raise ApiError(f"未知のプロバイダ: {provider}")


# ---- 共通HTTP ----

def _get_json(url, headers, timeout=30.0):
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "replace")[:500]
        except Exception:
            pass
        raise ApiError(f"HTTP {e.code}: {detail or e.reason}") from e
    except urllib.error.URLError as e:
        raise ApiError(f"接続失敗: {e.reason}") from e


def _post_json(url, headers, body, timeout=180.0):
    headers = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "replace")[:500]
        except Exception:
            pass
        raise ApiError(f"HTTP {e.code}: {detail or e.reason}") from e
    except urllib.error.URLError as e:
        raise ApiError(f"接続失敗: {e.reason}") from e


# ---- OpenAI互換 (Chat Completions) ----

def openai_models_url(base):
    """base URLをmodels一覧のGET先に正規化する。"""
    u = (base or "").strip().rstrip("/")
    if not u:
        raise ApiError("APIエンドポイントが未設定です")
    if u.endswith("/chat/completions"):
        u = u[: -len("/chat/completions")]
    return u + "/models"


def endpoint_url(base):
    """base URLをchat/completionsのPOST先に正規化する。

    "https://api.openai.com/v1" → ".../v1/chat/completions"
    既に /chat/completions で終わるURLはそのまま使う。
    """
    u = (base or "").strip().rstrip("/")
    if not u:
        raise ApiError("APIエンドポイントが未設定です")
    if not u.endswith("/chat/completions"):
        u += "/chat/completions"
    return u


def openai_tools(allowed=None):
    """mcp_http.TOOLS をOpenAI function callingスキーマに変換する。"""
    out = []
    for t in TOOLS:
        if allowed is not None and t["name"][len("qgis_"):] not in allowed:
            continue
        out.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["inputSchema"],
            },
        })
    return out


def chat_completions(base, api_key, model, messages, tools=None,
                     timeout=180.0, extra=None):
    """POST {base}/chat/completions (非ストリーミング)して応答JSONを返す。

    @raises ApiError: HTTP/接続エラー・応答形式不正
    """
    body = {"model": model, "messages": messages}
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    if extra:
        body.update(extra)
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    data = _post_json(endpoint_url(base), headers, body, timeout)
    if not isinstance(data, dict) or not data.get("choices"):
        raise ApiError(f"応答形式が不正です: {str(data)[:300]}")
    return data


# ---- Gemini (generateContent) ----

def gemini_models_url(base):
    """base URLをmodels一覧のGET先に正規化する。"""
    u = (base or "").strip().rstrip("/")
    if not u:
        raise ApiError("APIエンドポイントが未設定です")
    if ":generateContent" in u:
        u = u.split("/models/")[0]  # /models/<m>:generateContent を切る
    return u + "/models"


def _gemini_schema(s):
    """JSON Schema(lowercase type)をGemini functionDeclarationsの
    Schema(UPPERCASE type, OpenAPIサブセット)に変換する。"""
    if isinstance(s, dict):
        out = {}
        for k, v in s.items():
            out[k] = (v.upper() if (k == "type" and isinstance(v, str))
                      else _gemini_schema(v))
        if out.get("type") == "ARRAY" and "items" not in out:
            out["items"] = {}  # items必須。{}=任意型
        return out
    if isinstance(s, list):
        return [_gemini_schema(x) for x in s]
    return s


def gemini_tools(allowed=None):
    """mcp_http.TOOLS をGemini functionDeclarationsに変換する。"""
    decls = []
    for t in TOOLS:
        if allowed is not None and t["name"][len("qgis_"):] not in allowed:
            continue
        decls.append({
            "name": t["name"],
            "description": t["description"],
            "parameters": _gemini_schema(t["inputSchema"]),
        })
    return decls


def gemini_url(base, model):
    """generateContentのPOST先URL。"""
    u = (base or "").strip().rstrip("/")
    if not u:
        raise ApiError("APIエンドポイントが未設定です")
    if ":generateContent" in u:
        return u
    return f"{u}/models/{model}:generateContent"


def gemini_generate(base, api_key, model, system, contents,
                    tools=None, timeout=180.0, extra=None):
    """POST {base}/models/{model}:generateContent して応答JSONを返す。"""
    body = {"contents": contents}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if tools:
        body["tools"] = [{"functionDeclarations": tools}]
    if extra:
        body.update(extra)
    headers = {"x-goog-api-key": api_key} if api_key else {}
    data = _post_json(gemini_url(base, model), headers, body, timeout)
    if not isinstance(data, dict) or not data.get("candidates"):
        fb = (data or {}).get("promptFeedback") if isinstance(data, dict) else None
        raise ApiError(
            f"応答形式が不正かブロックされました: "
            f"{str(fb or data)[:300]}")
    return data


# ---- ツール共通 ----

def tool_to_command(name, args):
    """ツール呼び出し(qgis_<type>)をドライバのコマンドdictに変換する。

    mcp_http._tool_call と同じ規則: qgis_接頭辞を剥がしてtypeにし、
    引数をそのままマージする。None値の引数は送らない。
    """
    if not (name or "").startswith("qgis_"):
        raise ApiError(f"不明なツール: {name}")
    cmd = {"type": name[len("qgis_"):]}
    cmd.update({k: v for k, v in (args or {}).items() if v is not None})
    return cmd


def parse_tool_arguments(raw):
    """tool_callのarguments(JSON文字列)をdictにする。"""
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or "{}")
    except Exception as e:
        raise ApiError(
            f"tool argumentsがJSONとして不正: {e}: {str(raw)[:200]}")


def command_from_tool_call(tc):
    """OpenAI tool_callオブジェクト → (name, ドライバcmd)。"""
    fn = (tc or {}).get("function") or {}
    name = fn.get("name") or ""
    args = parse_tool_arguments(fn.get("arguments"))
    return name, tool_to_command(name, args)


def reply_to_text(rep):
    """ドライバのreply dictをツール結果テキストにする。"""
    if "error" in rep:
        return f"ERROR: {rep['error']}"
    text = rep.get("result")
    if not isinstance(text, str):
        text = json.dumps(text, ensure_ascii=False, indent=2)
    if len(text) > MAX_TOOL_RESULT_CHARS:
        text = (text[:MAX_TOOL_RESULT_CHARS]
                + f"\n... (truncated, {len(text)} chars total)")
    return text


def screenshot_temp_path():
    return os.path.join(tempfile.gettempdir(),
                        f"qgis-ai-shot-{uuid.uuid4().hex[:8]}.png")


def image_b64(path):
    """PNGファイルをbase64文字列にする(読めなければNone)。"""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except Exception:
        return None


def image_message_content(path, note=None):
    """PNGファイルをOpenAI vision用のcontent配列にする(読めなければNone)。"""
    b64 = image_b64(path)
    if b64 is None:
        return None
    return [
        {"type": "text",
         "text": note or f"screenshot saved: {path}"},
        {"type": "image_url",
         "image_url": {"url": f"data:image/png;base64,{b64}"}},
    ]


def system_prompt(plugins=None):
    plist = ", ".join(sorted(plugins)) if plugins else "(none)"
    return SYSTEM_PROMPT.format(plugins=plist)


# ---- プロバイダ抽象化 ----
# 各プロバイダは以下のインターフェースを持つ:
#   build_messages(system, history, user_text) -> ワイヤ形式のメッセージ列
#   send(base, key, model, system, msgs, timeout) -> 応答JSON
#   parse(data) -> {"text": str, "calls": [{"id","name","args"}], "raw": ...}
#   append_exchange(msgs, turn, results)
#       results: callsに対応する [{"text": str, "image": path|None}]
#       raw assistant + プロバイダ固有のツール結果エントリをmsgsに積む
#   list_models(base, key, timeout) -> [モデルID, ...]


class OpenAIProvider:
    id = "openai"
    label = PROVIDERS["openai"]["label"]

    def list_models(self, base, key, timeout=30.0):
        """GET {base}/models → data[].id をソートして返す。"""
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        data = _get_json(openai_models_url(base), headers, timeout)
        items = data.get("data") if isinstance(data, dict) else None
        if not isinstance(items, list):
            raise ApiError(f"応答形式が不正です: {str(data)[:300]}")
        return sorted(i["id"] for i in items
                      if isinstance(i, dict) and i.get("id"))

    def build_messages(self, system, history, user_text):
        return ([{"role": "system", "content": system}]
                + [dict(m) for m in history]
                + [{"role": "user", "content": user_text}])

    def send(self, base, key, model, system, msgs, timeout=180.0):
        return chat_completions(base, key, model, msgs,
                                tools=openai_tools(), timeout=timeout)

    def parse(self, data):
        msg = (data.get("choices") or [{}])[0].get("message") or {}
        calls = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function") or {}
            calls.append({
                "id": tc.get("id"),
                "name": fn.get("name") or "",
                "args": parse_tool_arguments(fn.get("arguments")),
            })
        return {"text": msg.get("content") or "",
                "calls": calls, "raw": msg}

    def append_exchange(self, msgs, turn, results):
        msgs.append(turn["raw"])
        for c, r in zip(turn["calls"], results):
            content = r["text"]
            if r.get("image"):
                img = image_message_content(r["image"], note=r["text"])
                if img is not None:
                    content = img
            msgs.append({"role": "tool",
                         "tool_call_id": c.get("id"),
                         "content": content})


class GeminiProvider:
    id = "gemini"
    label = PROVIDERS["gemini"]["label"]

    def list_models(self, base, key, timeout=30.0):
        """GET {base}/models → generateContent対応モデルを返す。

        応答の models[].name は "models/<id>" 形式なので接頭辞を剥がす。
        supportedGenerationMethods に generateContent が無いモデル
        (embed等)は除外する。
        """
        headers = {"x-goog-api-key": key} if key else {}
        data = _get_json(gemini_models_url(base), headers, timeout)
        items = data.get("models") if isinstance(data, dict) else None
        if not isinstance(items, list):
            raise ApiError(f"応答形式が不正です: {str(data)[:300]}")
        out = []
        for m in items:
            name = (m.get("name") or "").split("/")[-1]
            methods = m.get("supportedGenerationMethods")
            if not name or (methods and "generateContent" not in methods):
                continue
            out.append(name)
        return sorted(set(out))

    def _parts(self, text):
        return [{"text": text}] if text else []

    def build_messages(self, system, history, user_text):
        contents = []
        for m in history:
            role = "model" if m.get("role") == "assistant" else "user"
            contents.append({"role": role,
                             "parts": self._parts(m.get("content", ""))})
        contents.append({"role": "user", "parts": [{"text": user_text}]})
        return contents

    def send(self, base, key, model, system, msgs, timeout=180.0):
        return gemini_generate(base, key, model, system, msgs,
                               tools=gemini_tools(), timeout=timeout)

    def parse(self, data):
        cand = (data.get("candidates") or [{}])[0]
        content = cand.get("content") or {}
        parts = content.get("parts") or []
        text = "".join(p.get("text", "") for p in parts)
        calls = [{"id": None,
                  "name": (p.get("functionCall") or {}).get("name") or "",
                  "args": (p.get("functionCall") or {}).get("args") or {}}
                 for p in parts if "functionCall" in p]
        raw = {"role": "model", "parts": parts}
        if not text and not calls:
            raise ApiError(
                f"応答が空かブロックされました: finishReason="
                f"{cand.get('finishReason')} {str(data)[:200]}")
        return {"text": text, "calls": calls, "raw": raw}

    def append_exchange(self, msgs, turn, results):
        # モデルのfunctionCallを含むcontentをそのまま積み、
        # 全functionResponseを1つのuserターンにまとめて返す
        msgs.append(turn["raw"])
        parts = []
        for c, r in zip(turn["calls"], results):
            parts.append({"functionResponse": {
                "name": c["name"],
                "response": {"result": r["text"]},
            }})
            if r.get("image"):
                b64 = image_b64(r["image"])
                if b64 is not None:
                    parts.append({"inlineData": {
                        "mimeType": "image/png", "data": b64}})
        msgs.append({"role": "user", "parts": parts})


_PROVIDERS = {"openai": OpenAIProvider, "gemini": GeminiProvider}


def get_provider(provider):
    """プロバイダID → プロバイダインスタンス。"""
    try:
        return _PROVIDERS[provider]()
    except KeyError:
        raise ApiError(f"未知のプロバイダ: {provider}")


def list_models(provider, base, key, timeout=30.0):
    """プロバイダのエンドポイントから利用可能なモデルID一覧を返す。"""
    return get_provider(provider).list_models(base, key, timeout)
