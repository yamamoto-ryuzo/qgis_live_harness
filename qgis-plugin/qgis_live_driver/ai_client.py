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
  - "copilot": GitHub Copilot
    (OpenAI互換の {api}/chat/completions。APIキー欄のGitHubトークンを
    api.github.com/copilot_internal/v2/token で短期トークンに交換し、
    応答の endpoints.api をAPI先に使う。Copilot契約が必要。
    「GitHubでサインイン」ボタンはOAuthデバイスフローでトークンを取得)

ツール定義は mcp_http.TOOLS(MCP/RESTと同一)を各プロバイダの
スキーマに変換して使う。実行は LiveDriver.submit() に委譲するため
このモジュール自体はQGISを触らない。

プロバイダ抽象化: OpenAIProvider/GeminiProvider/CopilotProvider が
  build_messages / send / parse / append_exchange を実装し、
ai_panel のエージェントループはプロバイダ非依存で回る。
"""

import base64
import json
import os
import re
import tempfile
import threading
import time
import urllib.error
import urllib.parse
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

# ---- GitHub Copilot ----
# GitHub Copilot APIは公開仕様ではなく、VS CodeのCopilot Chatが使う
# 内部エンドポイント。GitHubトークンを短期トークンに交換して使うのは
# copilot-api等のコミュニティ実装と同じ経路。Copilot契約が必要。
COPILOT_DEFAULT_BASE = "https://api.githubcopilot.com"
COPILOT_DEFAULT_MODEL = "gpt-4o"
COPILOT_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"
# v2/tokenが応答しない環境でのフォールバック: 契約情報(endpoints.api/
# access_type_sku)を返す。@github/copilot CLIが使う公式経路
COPILOT_USER_URL = "https://api.github.com/copilot_internal/user"
# api.githubcopilot.com が要求するクライアント識別ヘッダ。
# 任意のEditor-Versionでは拒否されうるため、VS CodeのCopilot Chatが
# 送る値(VS Code拡張・copilot-api等と同じデファクト)を使う。
COPILOT_HEADERS = {
    "Editor-Version": "vscode/1.99.3",
    "Editor-Plugin-Version": "copilot-chat/0.26.7",
    "Copilot-Integration-Id": "vscode-chat",
    "Openai-Intent": "conversation-panel",
    "User-Agent": "GitHubCopilotChat/0.26.7",
}
# OAuthデバイスフローのclient_id。既定はVS Codeの公開OAuth Appで、
# 同意画面には「Visual Studio Code」と表示される(Copilot認可を受ける
# デファクトの方法。copilot-api等も同値)。独自OAuth Appを使う場合は
# 環境変数で差し替える。
GITHUB_CLIENT_ID = os.environ.get("QGIS_LIVE_GITHUB_CLIENT_ID",
                                  "Iv1.b507a08c87ecfe98")
GITHUB_DEVICE_CODE_URL = "https://github.com/login/device/code"
GITHUB_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"

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
    "copilot": {
        "label": "GitHub Copilot",
        "base": COPILOT_DEFAULT_BASE,
        "model": COPILOT_DEFAULT_MODEL,
        "key_hint": "GitHubトークン (Copilot契約必須。「GitHubでサインイン」で自動取得可)",
        "endpoint_hint": "https://api.githubcopilot.com  (copilot-api等の互換プロキシはそのURL)",
    },
}

# ---- モデル一覧のメタ情報 ----

# モデル種別 → 表示ラベル。この順序でコンボをグループ化する。
MODEL_KINDS = [
    ("chat_vision", "テキスト (画像入力可)"),
    ("chat", "テキスト"),
    ("image", "画像生成"),
    ("embed", "埋め込み"),
    ("other", "音声/その他"),
]
MODEL_KIND_LABELS = dict(MODEL_KINDS)

# プロバイダ既定エンドポイント利用時にコンボへ予め載せる推奨モデル
# (「取得」ボタンを押さなくても価格付きで選べるようにするため)。
# 実際に使えるかはAPIキーのプラン次第。取得で実一覧に置き換わる。
SUGGESTED_MODELS = {
    "openai": ["gpt-5-mini", "gpt-5", "gpt-4.1-mini", "gpt-4.1",
               "gpt-4o-mini", "gpt-4o", "o4-mini"],
    "gemini": ["gemini-2.5-flash", "gemini-2.5-pro",
               "gemini-2.5-flash-lite", "gemini-2.0-flash"],
    "copilot": ["gpt-4o", "gpt-4.1", "gpt-5-mini", "gpt-5", "o4-mini",
                "claude-sonnet-4", "claude-3.7-sonnet", "gemini-2.5-pro"],
}

# 主要モデルの参考価格 (USD / 1Mトークン, [入力, 出力])。
# APIが価格を返さない場合の目安表示用。公開価格ベースだが
# 変動しうるため「参考値」として表示する。モデルIDの末尾部分
# (プロバイダ名を除いたもの)との前方一致・最長一致で引く。
KNOWN_MODEL_PRICES = {
    "gpt-5-pro": (15.00, 120.00),
    "gpt-5": (1.25, 10.00),
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5-nano": (0.05, 0.40),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "o3": (2.00, 8.00),
    "o4-mini": (1.10, 4.40),
    "claude-opus-4": (15.00, 75.00),
    "claude-sonnet-4": (3.00, 15.00),
    "claude-haiku-4": (1.00, 5.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "claude-3-haiku": (0.25, 1.25),
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-2.0-flash-lite": (0.075, 0.30),
}

# 種別推定のための名前ヒント(モデルID末尾の小文字に対して検索)。
# 判定は推定であり、APIが modality 等を返す場合はそちらを優先する。
_EMBED_RE = re.compile(r"embed")
_IMAGE_RE = re.compile(
    r"dall-e|gpt-image|imagen|[-_/]image($|[-_.0-9])|flux|"
    r"stable.?diffusion|sdxl|ideogram|recraft|playground-v|cogview|"
    r"kolors|seedream|photon|hunyuan-image|pixart")
_AUDIO_RE = re.compile(
    r"whisper|tts|transcribe|realtime|audio|moderation|speech|voice")
_VISION_RE = re.compile(
    r"vision|gpt-4o|chatgpt|gpt-4\.1|gpt-5|gpt-4-turbo|gpt-4-|"
    r"\bo[134]\b|claude|gemini|gemma-?3|pixtral|llava|moondream|"
    r"cogvlm|internvl|minicpm-v|qvq|glm-4|kimi|[-_.]vl($|[-_.0-9])|"
    r"qwen.*vl|llama-4|llama-3\.2-(11|90)b|mistral-(small|medium|large)|"
    r"grok")


def classify_model(model_id, entry=None):
    """モデルID(+APIのメタ情報)から種別を推定する。

    @returns "chat_vision"|"chat"|"image"|"embed"|"other"
    entry は list_model_entries() の1要素。OpenRouter等が返す
    architecture.modality ("text+image->text" 等) や
    input_modalities/output_modalities があれば最優先で使う。
    """
    tail = (model_id or "").split("/")[-1].lower()
    if entry:
        mod = str(entry.get("modality") or "").lower()
        ins = [str(x).lower() for x in entry.get("input_modalities") or []]
        outs = [str(x).lower() for x in entry.get("output_modalities") or []]
        if "->" in mod:
            mi, mo = mod.split("->", 1)
            if "image" in mo:
                return "image"
            if "image" in mi:
                return "chat_vision"
        if any("image" in o for o in outs):
            return "image"
        if any("image" in i for i in ins):
            return "chat_vision"
    if _EMBED_RE.search(tail):
        return "embed"
    if _IMAGE_RE.search(tail):
        return "image"
    if _AUDIO_RE.search(tail):
        return "other"
    if _VISION_RE.search(tail):
        return "chat_vision"
    return "chat"


def _usd(v):
    """金額を $ 表記に整形 (0.6→$0.60, 0.075→$0.075, 10→$10)。"""
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    if "." in s and len(s.rsplit(".", 1)[1]) < 2:
        s = f"{v:.2f}"
    return f"${s}"


def fmt_tokens(n):
    """トークン数を短縮表記に (128000→"128k", 1048576→"1.0M")。"""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return None
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return str(n)


def _known_price(tail):
    """既知価格表を末尾IDで最長前方一致検索 → (in_usd, out_usd)|None"""
    best = None
    for key, io in KNOWN_MODEL_PRICES.items():
        if tail == key or tail.startswith(key):
            if best is None or len(key) > len(best[0]):
                best = (key, io)
    return best[1] if best else None


def _entry_price(entry, tail):
    """価格情報 → (短表記, 説明文, 出典) 。無ければ (None, None, None)。

    OpenRouter等が pricing.prompt/completion (USD/token) を返せば
    それを使い、無ければ既知価格表(参考値)にフォールバックする。
    """
    pr = entry.get("pricing")
    if isinstance(pr, dict):
        def _pm(key):
            try:
                return float(pr[key]) * 1_000_000
            except (KeyError, TypeError, ValueError):
                return None
        pin, pout = _pm("prompt"), _pm("completion")
        if pin is not None or pout is not None:
            pin, pout = pin or 0.0, pout or 0.0
            return (f"{_usd(pin)}/{_usd(pout)}",
                    f"入力 {_usd(pin)} / 出力 {_usd(pout)} /1Mトークン",
                    "api")
        try:
            pimg = float(pr.get("image"))
        except (TypeError, ValueError):
            pimg = None
        if pimg:
            return (f"{_usd(pimg)}/img",
                    f"{_usd(pimg)} /枚(画像生成)", "api")
    kp = _known_price(tail)
    if kp:
        return (f"{_usd(kp[0])}/{_usd(kp[1])}",
                f"入力 {_usd(kp[0])} / 出力 {_usd(kp[1])} /1Mトークン",
                "known")
    return None, None, None


def model_info(entry):
    """list_model_entries()の1要素 → {id, kind, price, price_desc,
    price_src, context} に正規化する。"""
    mid = entry["id"]
    tail = mid.split("/")[-1].lower()
    price, desc, src = _entry_price(entry, tail)
    return {
        "id": mid,
        "kind": classify_model(mid, entry),
        "price": price,
        "price_desc": desc,
        "price_src": src,          # "api"=エンドポイント応答 / "known"=参考値
        "context": (entry.get("context_length")
                    or entry.get("input_token_limit")),
    }


def model_label(info):
    """コンボの表示テキスト。価格があれば 'id   $in/$out' 形式。"""
    return (f"{info['id']}   {info['price']}" if info.get("price")
            else info["id"])


def model_tooltip(info):
    """コンボ項目のツールチップ(複数行)。"""
    lines = [info["id"],
             f"種別: {MODEL_KIND_LABELS.get(info['kind'], info['kind'])}"]
    if info.get("price_desc"):
        src = "API応答値" if info["price_src"] == "api" else "参考値"
        lines.append(f"価格: {info['price_desc']} ({src})")
    if info.get("context"):
        ctx = fmt_tokens(info["context"])
        if ctx:
            lines.append(f"コンテキスト: {ctx} tokens")
    return "\n".join(lines)

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


def _post_form(url, fields, timeout=30.0):
    """application/x-www-form-urlencoded でPOSTして応答JSONを返す。"""
    body = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST", headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        })
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


# ---- GitHub Copilot: トークン交換 / OAuthデバイスフロー ----

# GitHubトークン → {"token","expires_at","api"} のキャッシュ
_COPILOT_CACHE = {}
_COPILOT_CACHE_LOCK = threading.Lock()


def _gh_headers(github_token):
    return {"Authorization": f"token {github_token}",
            "Accept": "application/json",
            **COPILOT_HEADERS}


def copilot_session(github_token, base):
    """GitHubトークン → (Copilot APIのBearerトークン, API base) に解決する。

    baseが既定(COPILOT_DEFAULT_BASE)の場合のみ、GitHubトークンを
    copilot_internal/v2/token で短期トークンに交換し、応答の
    endpoints.api (individual/business/enterprise) をAPI先に使う。
    トークンは期限切れ60秒前までモジュール内キャッシュする。
    v2/token が応答しない環境(404の報告あり)では
    copilot_internal/user でAPI先だけを解決し、GitHubトークンを
    そのままBearerに使う(@github/copilot CLIと同じ動作)。
    既定以外のbaseはcopilot-api互換プロキシ等とみなし、
    交換せずgithub_tokenをそのままBearerに使う。
    """
    u = (base or "").strip().rstrip("/") or COPILOT_DEFAULT_BASE
    if not github_token:
        raise ApiError(
            "APIキー欄にGitHubトークンを入力するか、"
            "「GitHubでサインイン」で取得してください")
    if u != COPILOT_DEFAULT_BASE:
        return github_token, u
    now = time.time()
    with _COPILOT_CACHE_LOCK:
        ent = _COPILOT_CACHE.get(github_token)
        if ent and ent["expires_at"] - now >= 60:
            return ent["token"], ent["api"]
        try:
            data = _get_json(COPILOT_TOKEN_URL, _gh_headers(github_token))
            tok = data.get("token")
            if not tok:
                raise ApiError(f"token無し: {str(data)[:200]}")
            ent = {
                "token": tok,
                "expires_at": float(
                    data.get("expires_at")
                    or now + float(data.get("refresh_in") or 1500)),
                "api": ((data.get("endpoints") or {}).get("api")
                        or COPILOT_DEFAULT_BASE),
            }
        except ApiError as e1:
            # フォールバック: copilot_internal/user でプラン別API先を
            # 解決し、GitHubトークンをそのままBearerに使う
            try:
                user = _get_json(COPILOT_USER_URL,
                                 _gh_headers(github_token))
            except ApiError as e2:
                raise ApiError(
                    "Copilotトークンを取得できません"
                    " (GitHubトークンが無効かCopilot未契約の可能性): "
                    f"{e1} / {e2}") from e2
            ent = {
                "token": github_token,
                "expires_at": now + 1500,
                "api": ((user.get("endpoints") or {}).get("api")
                        or COPILOT_DEFAULT_BASE),
            }
        _COPILOT_CACHE[github_token] = ent
        return ent["token"], ent["api"]


def github_device_code(scope="read:user"):
    """OAuthデバイスフローを開始する。

    @returns {"device_code","user_code","verification_uri",
              "interval","expires_in"} — ユーザにverification_uriで
      user_codeを入力させ、device_codeをポーリングに使う
    """
    d = _post_form(GITHUB_DEVICE_CODE_URL,
                   {"client_id": GITHUB_CLIENT_ID, "scope": scope})
    if not d.get("device_code") or not d.get("user_code"):
        raise ApiError(f"デバイスコードの応答が不正: {str(d)[:300]}")
    return d


def github_poll_access_token(device_code):
    """デバイスフローのトークンを1回ポーリングする。

    @returns API応答dict。{"access_token": ...} なら完了、
      {"error": "authorization_pending"|"slow_down"|...} は未完了/失敗
      (GitHubは未認可でもHTTP 200でerrorフィールドを返す)
    """
    return _post_form(GITHUB_ACCESS_TOKEN_URL, {
        "client_id": GITHUB_CLIENT_ID,
        "device_code": device_code,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code"})


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
                     timeout=180.0, extra=None, headers=None):
    """POST {base}/chat/completions (非ストリーミング)して応答JSONを返す。

    @param headers: Authorization以外に追加するヘッダ(Copilot用)
    @raises ApiError: HTTP/接続エラー・応答形式不正
    """
    body = {"model": model, "messages": messages}
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    if extra:
        body.update(extra)
    hdrs = dict(headers or {})
    if api_key:
        hdrs["Authorization"] = f"Bearer {api_key}"
    data = _post_json(endpoint_url(base), hdrs, body, timeout)
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
#   list_model_entries(base, key, timeout) -> [{id, メタ情報...}]


class OpenAIProvider:
    id = "openai"
    label = PROVIDERS["openai"]["label"]

    def list_model_entries(self, base, key, timeout=30.0):
        """GET {base}/models → [{id, 価格/modality等(あれば)}, ...]

        OpenRouter等は pricing・context_length・architecture.modality
        を返すため、あれば拾ってメタ情報表示に使う。
        """
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        data = _get_json(openai_models_url(base), headers, timeout)
        items = data.get("data") if isinstance(data, dict) else None
        if not isinstance(items, list):
            raise ApiError(f"応答形式が不正です: {str(data)[:300]}")
        out = []
        for i in items:
            if not isinstance(i, dict) or not i.get("id"):
                continue
            e = {"id": i["id"]}
            arch = i.get("architecture") or {}
            for k in ("modality", "input_modalities", "output_modalities"):
                if arch.get(k):
                    e[k] = arch[k]
            if i.get("pricing"):
                e["pricing"] = i["pricing"]
            if i.get("context_length"):
                e["context_length"] = i["context_length"]
            out.append(e)
        return sorted(out, key=lambda e: e["id"])

    def list_models(self, base, key, timeout=30.0):
        """GET {base}/models → data[].id をソートして返す。"""
        return [e["id"] for e in self.list_model_entries(base, key, timeout)]

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

    def list_model_entries(self, base, key, timeout=30.0):
        """GET {base}/models → generateContent対応モデルの
        [{id, input/output_token_limit}, ...] を返す。"""
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
            e = {"id": name}
            if m.get("inputTokenLimit"):
                e["input_token_limit"] = m["inputTokenLimit"]
            if m.get("outputTokenLimit"):
                e["output_token_limit"] = m["outputTokenLimit"]
            out.append(e)
        return sorted({e["id"]: e for e in out}.values(),
                      key=lambda e: e["id"])

    def list_models(self, base, key, timeout=30.0):
        """GET {base}/models → generateContent対応モデルを返す。

        応答の models[].name は "models/<id>" 形式なので接頭辞を剥がす。
        supportedGenerationMethods に generateContent が無いモデル
        (embed等)は除外する。
        """
        return [e["id"] for e in self.list_model_entries(base, key, timeout)]

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


class CopilotProvider(OpenAIProvider):
    """GitHub Copilot。

    メッセージ形式はOpenAI互換なので build_messages/parse/
    append_exchange は OpenAIProvider を継承。違いは認証だけ:
    APIキー欄のGitHubトークンを copilot_session() で短期トークンに
    交換し、契約種別に応じたAPI先(endpoints.api)を使う。
    """
    id = "copilot"
    label = PROVIDERS["copilot"]["label"]

    def list_model_entries(self, base, key, timeout=30.0):
        """GET {api}/models → chat対応モデル一覧。

        Copilot APIの応答は capabilities.type / policy.state /
        capabilities.limits.max_context_window_tokens /
        supports.vision を持つため、種別とコンテキスト長の判定に使う。
        capabilitiesを持たない応答(互換プロキシ等)は全件採用する。
        """
        tok, api_base = copilot_session(key, base)
        data = _get_json(
            api_base.rstrip("/") + "/models",
            {"Authorization": f"Bearer {tok}", **COPILOT_HEADERS},
            timeout)
        items = data.get("data") if isinstance(data, dict) else None
        if not isinstance(items, list):
            raise ApiError(f"応答形式が不正です: {str(data)[:300]}")
        out = []
        for m in items:
            if not isinstance(m, dict) or not m.get("id"):
                continue
            caps = m.get("capabilities")
            if not isinstance(caps, dict):
                out.append({"id": m["id"]})
                continue
            if caps.get("type") not in (None, "chat"):
                continue
            if (m.get("policy") or {}).get("state") == "disabled":
                continue
            e = {"id": m["id"],
                 "input_modalities":
                     ["text", "image"]
                     if (caps.get("supports") or {}).get("vision")
                     else ["text"]}
            lim = caps.get("limits") or {}
            if lim.get("max_context_window_tokens"):
                e["context_length"] = lim["max_context_window_tokens"]
            out.append(e)
        return sorted(out, key=lambda e: e["id"])

    def send(self, base, key, model, system, msgs, timeout=180.0):
        tok, api_base = copilot_session(key, base)
        return chat_completions(api_base, tok, model, msgs,
                                tools=openai_tools(), timeout=timeout,
                                headers=COPILOT_HEADERS)


_PROVIDERS = {"openai": OpenAIProvider, "gemini": GeminiProvider,
              "copilot": CopilotProvider}


def get_provider(provider):
    """プロバイダID → プロバイダインスタンス。"""
    try:
        return _PROVIDERS[provider]()
    except KeyError:
        raise ApiError(f"未知のプロバイダ: {provider}")


def list_models(provider, base, key, timeout=30.0):
    """プロバイダのエンドポイントから利用可能なモデルID一覧を返す。"""
    return get_provider(provider).list_models(base, key, timeout)


def list_model_infos(provider, base, key, timeout=30.0):
    """モデル一覧をメタ情報付きで返す。

    @returns [model_info()のdict, ...] (idでソート済み)
    """
    entries = get_provider(provider).list_model_entries(base, key, timeout)
    return [model_info(e) for e in entries]
