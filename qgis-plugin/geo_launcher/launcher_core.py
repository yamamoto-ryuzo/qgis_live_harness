# -*- coding: utf-8 -*-
"""kasugai_qgis (qgis_launcher.exe) の Python 移植コア。

Rust 版 src/main.rs の機能を QGIS プラグイン内で再現する。
QGIS/Qt 非依存の標準ライブラリのみで構成し、bridge/dialog の双方から使う。

対象機能:
- qgis_settings.json 読み書き (force/user オーバーライド・未知キー温存)
- パスエイリアス/環境変数展開
- プロファイル/プロジェクト/QGIS・QField バージョン列挙
- プロジェクトのバージョンに合った QGIS の自動選択
- ロール customization / global settings ini / startup.py 引数つき QGIS 起動
- 開発モード環境変数 (WEBENGINE_*) 注入
- drive_mappings (subst / rclone sync / rclone mount)
- KASUGAI/yr-qgis-launcher 方式 local_sync (robocopy)
- 配布プロファイルのシード/リセット
- NSIS 自動更新 (update.json 確認 + installer 適用)
- QGIS Live Harness セッション列挙 (~/.qgis-live)
"""

import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
import zipfile

PLUGIN_ID = "geo_launcher"
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))

IS_WINDOWS = os.name == "nt"
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

DEFAULT_API_PORT = 8500
SETTINGS_FILE = "qgis_settings.json"
ROLES = ("Viewer", "Editor", "Administrator")

_log = print


def set_logger(func):
    """進捗メッセージの出力先を差し替える (None で print に戻す)。"""
    global _log
    _log = func or print


def log(msg):
    _log(str(msg))


# ---------------------------------------------------------------------------
# JSON 読み込み補助
# ---------------------------------------------------------------------------

def fix_backslashes_in_json(text):
    """文字列リテラル内の無効な \\ を \\\\ に置換する (Rust版と同じ処理)。"""
    result = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c != '"':
            result.append(c)
            i += 1
            continue
        result.append('"')
        i += 1
        while i < n:
            c = text[i]
            i += 1
            if c == '"':
                result.append('"')
                break
            if c == '\\':
                if i < n and text[i] in '"\\/bfnrtu':
                    result.append('\\')
                    result.append(text[i])
                    i += 1
                else:
                    result.append('\\\\')
            else:
                result.append(c)
    return "".join(result)


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.loads(fix_backslashes_in_json(f.read()))
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 設定
# ---------------------------------------------------------------------------

def settings_path(settings_dir):
    return os.path.join(settings_dir, SETTINGS_FILE)


def _merge_override(base, override_path):
    """オーバーライド JSON を浅くマージする。

    - path_aliases: キー毎にマージ
    - drive_mappings: drive が一致する要素をキー毎にマージ、無ければ追加
    - その他: 上書き
    """
    over = _read_json(override_path)
    if not isinstance(over, dict) or not isinstance(base, dict):
        return base
    for key, val in over.items():
        if key == "path_aliases" and isinstance(val, dict):
            bm = base.setdefault("path_aliases", {})
            if isinstance(bm, dict):
                bm.update(val)
        elif key == "drive_mappings" and isinstance(val, list):
            bm = base.setdefault("drive_mappings", [])
            if isinstance(bm, list):
                for om in val:
                    drive = om.get("drive") if isinstance(om, dict) else None
                    hit = None
                    if drive:
                        for e in bm:
                            if isinstance(e, dict) and e.get("drive") == drive:
                                hit = e
                                break
                    if hit is not None and isinstance(om, dict):
                        hit.update(om)
                    else:
                        bm.append(om)
        else:
            base[key] = val
    return base


def load_settings(settings_dir):
    """qgis_settings.json + override + user override を読み込む。"""
    s = _read_json(settings_path(settings_dir))
    if not isinstance(s, dict):
        s = {}
    force = os.path.join(settings_dir, "qgis_settings_override.json")
    if os.path.exists(force):
        s = _merge_override(s, force)
    username = os.environ.get("USERNAME", "")
    if username:
        user = os.path.join(
            settings_dir, "qgis_settings_{}.json".format(username))
        if os.path.exists(user):
            s = _merge_override(s, user)
    pp = s.get("project_path")
    if isinstance(pp, str):
        s["project_path"] = [pp]
    elif not isinstance(pp, list):
        s["project_path"] = []
    ver = s.get("kasugai_qgis_version")
    if isinstance(ver, (int, float)):
        s["kasugai_qgis_version"] = str(ver)
    if not isinstance(s.get("path_aliases"), dict):
        s["path_aliases"] = {}
    if not isinstance(s.get("drive_mappings"), list):
        s["drive_mappings"] = []
    return s


def save_settings(settings_dir, new_values):
    """設定を保存する。既存ファイルの未知キーは温存する。"""
    p = settings_path(settings_dir)
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    merged = _read_json(p)
    if not isinstance(merged, dict):
        merged = {}
    merged.update(new_values)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    return p


# ---------------------------------------------------------------------------
# パス解決
# ---------------------------------------------------------------------------

def expand_env_vars(s):
    """%VAR% 形式の環境変数を最大10回展開する。"""
    for _ in range(10):
        prev = s
        s = re.sub(
            r"%([^%]+)%",
            lambda m: os.environ.get(m.group(1), m.group(0)),
            s,
        )
        if s == prev:
            break
    return s


def resolve_path(s, aliases):
    """パスエイリアス (ALIAS:\\...) を適用後、環境変数を展開する。"""
    if not s:
        return s
    resolved = s
    m = re.match(r"^([A-Za-z0-9_]{2,}):(.*)$", s)
    if m:
        alias = m.group(1).upper()
        rest = m.group(2).lstrip("\\/")
        root = aliases.get(alias)
        if root is None and alias == "BOX":
            root = os.path.join(
                os.environ.get("USERPROFILE", r"C:\Users\user"), "Box")
        if root is not None:
            resolved = root.rstrip("\\/") + ("\\" + rest if rest else "")
    return expand_env_vars(resolved)


def normalize_drive_root(s):
    """'C:' や 'c:\\' のみの指定をドライブルート 'C:\\' に正規化する。"""
    t = s.strip()
    if len(t) >= 2 and t[0].isalpha() and t[1] == ":":
        rest = t[2:]
        if not rest or all(c in "/\\" for c in rest):
            return t[0].upper() + ":\\"
    return s


def compute_project_root(settings, settings_dir):
    """project_root 設定を解決する。未設定時は settings_dir。"""
    r = (settings.get("project_root") or "").strip()
    if not r:
        return settings_dir
    expanded = normalize_drive_root(
        expand_env_vars(resolve_path(r, settings.get("path_aliases", {}))))
    if os.path.isabs(expanded):
        return expanded
    return os.path.join(settings_dir, expanded)


def resolve_settings_dir(settings_dir):
    """project_root 配下に qgis_settings.json があればそちらを優先する。

    戻り値: (settings, resolved_settings_dir, project_root)
    """
    settings = load_settings(settings_dir)
    project_root = compute_project_root(settings, settings_dir)
    ps = os.path.join(project_root, SETTINGS_FILE)
    if (os.path.normcase(project_root) != os.path.normcase(settings_dir)
            and os.path.exists(ps)):
        settings = load_settings(project_root)
        settings_dir = project_root
        project_root = compute_project_root(settings, settings_dir)
    return settings, settings_dir, project_root


def candidate_settings_dirs():
    """設定ディレクトリ候補を優先順で返す (存在チェックは呼び出し側)。"""
    out = []
    for env in ("GEO_LAUNCHER_DIR", "KASUGAI_QGIS_DIR"):
        v = os.environ.get(env, "").strip()
        if v:
            out.append(v)
    out.append(r"C:\kasugai\kasugai_qgis")
    # harness 内配置時は sibling の launcher バンドルも候補
    harness = detect_harness_root()
    if harness:
        out.append(os.path.join(
            harness, "launcher", "qgis_launcher", "download"))
    kasugai_root = r"C:\kasugai"
    if os.path.isdir(kasugai_root):
        try:
            for name in sorted(os.listdir(kasugai_root)):
                p = os.path.join(kasugai_root, name)
                if os.path.isdir(p):
                    out.append(p)
        except OSError:
            pass
    return out


def find_settings_dir(preferred=None):
    """qgis_settings.json を持つ最初の候補ディレクトリを返す。"""
    if preferred:
        if os.path.exists(settings_path(preferred)):
            return preferred
        if os.path.isdir(preferred):
            return preferred
    for c in candidate_settings_dirs():
        if os.path.exists(settings_path(c)):
            return c
    return preferred or candidate_settings_dirs()[0]


# ---------------------------------------------------------------------------
# プロファイル / プロジェクト / バージョン列挙
# ---------------------------------------------------------------------------

def qgis_profile_paths():
    """OS 上の QGIS4 プロファイルルート候補。"""
    out = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        out.append(os.path.join(appdata, "QGIS", "QGIS4"))
    return out


def _is_version_container(name):
    return (len(name) > 4 and name.startswith("QGIS")
            and name[4:].isdigit())


def _collect_profile_items(d, names, out):
    """dir 直下の非空ディレクトリをプロファイル候補として集める。

    QGIS{major} はバージョン別コンテナとして内側の profiles\\ を辿る。
    """
    try:
        entries = sorted(os.scandir(d), key=lambda e: e.name)
    except OSError:
        return
    for e in entries:
        if not e.is_dir():
            continue
        name = e.name
        if _is_version_container(name):
            inner = os.path.join(e.path, "profiles")
            _collect_profile_items(
                inner if os.path.isdir(inner) else e.path, names, out)
            continue
        try:
            if next(os.scandir(e.path), None) is None:
                continue  # 空ディレクトリは除外
        except OSError:
            continue
        if name not in names:
            names.add(name)
            out.append({"name": name, "path": e.path})


def list_profiles(settings_dir):
    """配布プロファイル + システムプロファイルの一覧。"""
    out, names = [], set()
    dist = os.path.join(settings_dir, "profiles")
    if os.path.isdir(dist):
        _collect_profile_items(dist, names, out)
    for base in qgis_profile_paths():
        probe = os.path.join(base, "profiles")
        _collect_profile_items(
            probe if os.path.isdir(probe) else base, names, out)
    out.sort(key=lambda p: p["name"])
    return out


def _is_qgis_project(path):
    return path.lower().endswith((".qgs", ".qgz"))


def list_projects(settings, project_root):
    """project_path から .qgs/.qgz を解決して列挙する。"""
    out, seen = [], set()
    aliases = settings.get("path_aliases", {})
    for src in settings.get("project_path", []):
        src = (src or "").strip()
        if not src:
            continue
        expanded = expand_env_vars(resolve_path(src, aliases))
        pb = expanded if os.path.isabs(expanded) else os.path.join(
            project_root, expanded)
        if os.path.isfile(pb) and _is_qgis_project(pb):
            rp = os.path.normpath(pb)
            if rp not in seen:
                seen.add(rp)
                out.append({"display": os.path.basename(pb), "path": pb})
        elif os.path.isdir(pb):
            try:
                files = sorted(
                    f for f in os.listdir(pb)
                    if _is_qgis_project(f)
                    and os.path.isfile(os.path.join(pb, f)))
            except OSError:
                files = []
            for f in files:
                p = os.path.join(pb, f)
                rp = os.path.normpath(p)
                if rp in seen:
                    continue
                seen.add(rp)
                out.append({
                    "display": "{}\\{}".format(os.path.basename(pb), f),
                    "path": p,
                })
    return out


def _extract_first_command_token(s):
    s = s.strip()
    if not s:
        return None
    if s.startswith('"'):
        end = s.find('"', 1)
        return s[1:end] if end > 0 else s[1:]
    return s.split()[0]


def find_qgis_path_from_registry():
    """.qgs の関連付けからシステム既定 QGIS のパスを返す。"""
    if not IS_WINDOWS:
        return None
    try:
        import winreg
    except ImportError:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, ".qgs") as k:
            prog_id = winreg.QueryValue(k, None)
        if not prog_id:
            return None
        with winreg.OpenKey(
                winreg.HKEY_CLASSES_ROOT,
                prog_id + r"\shell\open\command") as k:
            cmd = winreg.QueryValue(k, None)
        exe = _extract_first_command_token(cmd or "")
        if exe and os.path.exists(exe):
            return exe
    except OSError:
        pass
    return None


def list_qgis_versions(portable_base=None):
    """インストール済み QGIS/QField を列挙する。

    portable_base: ポータブル版 (QGIS*/qgis/bin/*.bat, QField*/usr/bin/
    qfield.exe) を探すベースディレクトリ。Rust版は current_dir を使う。
    戻り値: [{"name": str, "path": str}]
    """
    versions = []
    default_path = find_qgis_path_from_registry()
    default_base_dir = None

    if default_path:
        cur = os.path.dirname(os.path.normpath(default_path))
        while cur:
            name = os.path.basename(cur)
            if name.lower().startswith("qgis"):
                default_base_dir = os.path.dirname(cur)
                break
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent

    base_dirs = []
    if default_base_dir:
        base_dirs.append(default_base_dir)
    pf = os.environ.get("ProgramFiles")
    if pf and pf not in base_dirs:
        base_dirs.append(pf)
    osgeo = r"C:\OSGeo4W"
    if osgeo not in base_dirs:
        base_dirs.append(osgeo)

    def add(name, path):
        if all(p.lower() != path.lower() for _, p in versions):
            versions.append((name, path))

    for base in base_dirs:
        try:
            entries = sorted(os.scandir(base), key=lambda e: e.name)
        except OSError:
            continue
        for e in entries:
            if not e.is_dir():
                continue
            name = e.name
            lower = name.lower()
            if lower.startswith("qgis"):
                bin_dir = os.path.join(e.path, "bin")
                for fn, label in (("qgis.bat", "qgis.bat"),
                                  ("qgis-ltr.bat", "qgis-ltr.bat"),
                                  ("qgis-qt6.bat", "qgis-qt6.bat")):
                    p = os.path.join(bin_dir, fn)
                    if os.path.exists(p):
                        add("{} ({})".format(name, label), p)
                exe = os.path.join(bin_dir, "qgis-bin.exe")
                if (not any(os.path.exists(os.path.join(bin_dir, f)) for f in
                            ("qgis.bat", "qgis-ltr.bat", "qgis-qt6.bat"))
                        and os.path.exists(exe)):
                    add("{} (qgis-bin.exe)".format(name), exe)
            elif lower.startswith("qfield"):
                exe = os.path.join(e.path, "usr", "bin", "qfield.exe")
                if os.path.exists(exe):
                    add("QFieldインストール版 {}".format(name), exe)

    # ポータブル版 (base 直下の QGIS*/qgis/bin/*.bat, QField*/usr/bin/qfield.exe)
    if portable_base and os.path.isdir(portable_base):
        try:
            entries = sorted(os.scandir(portable_base), key=lambda e: e.name)
        except OSError:
            entries = []
        for e in entries:
            if not e.is_dir():
                continue
            name = e.name
            lower = name.lower()
            if lower.startswith("qgis"):
                root = os.path.join(e.path, "qgis", "bin")
                ltr = os.path.join(root, "qgis-ltr.bat")
                bat = os.path.join(root, "qgis.bat")
                if os.path.exists(ltr):
                    add("ポータブル版 {} (LTR)".format(name), ltr)
                elif os.path.exists(bat):
                    add("ポータブル版 {}".format(name), bat)
            elif lower.startswith("qfield"):
                exe = os.path.join(e.path, "usr", "bin", "qfield.exe")
                if os.path.exists(exe):
                    add("QFieldポータブル版 {}".format(name), exe)

    # システム既定を先頭に寄せる
    if default_path:
        folder_name = ""
        cur = os.path.dirname(os.path.normpath(default_path))
        while cur:
            n = os.path.basename(cur)
            low = n.lower()
            if ((low.startswith("qgis") or low.startswith("qfield"))
                    and not low.endswith((".bat", ".exe"))):
                folder_name = n
                break
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent
        filename = os.path.basename(default_path)
        display = ("{} ({})".format(folder_name, filename)
                   if folder_name else "システム既定のQGIS")
        for i, (n, p) in enumerate(versions):
            if p.lower() == default_path.lower():
                versions[i] = ("{} (システム既定)".format(display), p)
                break
        else:
            versions.insert(0, ("{} (システム既定)".format(display),
                                default_path))

    return [{"name": n, "path": p} for n, p in versions]


# ---------------------------------------------------------------------------
# プロジェクトバージョンからの QGIS 自動選択
# ---------------------------------------------------------------------------

_QGIS_TAG_RE = re.compile(rb"<qgis[^>]*\bversion=\"([^\"]+)\"")


def _parse_qgs_version(xml_bytes):
    m = _QGIS_TAG_RE.search(xml_bytes)
    if m:
        try:
            return m.group(1).decode("utf-8", "replace")
        except Exception:
            return None
    return None


def get_project_file_version(path):
    """.qgs/.qgz プロジェクトの <qgis version=...> を返す。"""
    try:
        if path.lower().endswith(".qgz"):
            with zipfile.ZipFile(path) as z:
                for name in z.namelist():
                    if name.lower().endswith(".qgs"):
                        return _parse_qgs_version(z.read(name))
            return None
        with open(path, "rb") as f:
            return _parse_qgs_version(f.read())
    except (OSError, zipfile.BadZipFile, KeyError):
        return None


def parse_version_parts(s):
    """先頭から現れる数字ドット区切りを最大3セグメント抽出。"""
    m = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", s)
    if not m:
        return []
    return [g for g in m.groups() if g is not None]


def _extract_major(s):
    m = re.search(r"\d+", s)
    return m.group(0) if m else None


def find_matching_version(project_ver, available):
    """プロジェクトのバージョンに合う list_qgis_versions エントリを返す。"""
    pv = (project_ver or "").strip()
    if not pv:
        return None
    pv_parts = parse_version_parts(pv)
    if not pv_parts:
        return available[0] if available else None
    if len(pv_parts) >= 2:
        for item in available:
            av = parse_version_parts(item["name"] + " " + item["path"])
            if len(av) >= 2 and av[0] == pv_parts[0] and av[1] == pv_parts[1]:
                return item
    for item in available:
        av = parse_version_parts(item["name"] + " " + item["path"])
        if av and av[0] == pv_parts[0]:
            return item
    return None


# ---------------------------------------------------------------------------
# 開発モード (QGIS Live Harness 連携)
# ---------------------------------------------------------------------------

def detect_harness_root():
    """KASUGAI_HARNESS_DIR または本ファイル祖先の harness ルートを返す。"""
    def is_harness(p):
        return os.path.exists(os.path.join(
            p, "qgis-plugin", "qgis_live_driver", "metadata.txt"))

    env = os.environ.get("KASUGAI_HARNESS_DIR", "").strip()
    if env and is_harness(env):
        return env
    cur = os.path.abspath(PLUGIN_DIR)
    while True:
        if is_harness(cur):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def _is_reparse_point(path):
    if not IS_WINDOWS:
        return os.path.islink(path)
    try:
        import ctypes
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        if attrs == -1:
            return False
        return bool(attrs & 0x400)
    except Exception:
        return os.path.islink(path)


def is_junction_deploy(harness_root, profile_name):
    """プロファイルの python/plugins が dev 配置 (junction) かを判定する。"""
    plugins_src = os.path.join(harness_root, "qgis-plugin")
    plugins_root = os.path.join(
        os.environ.get("APPDATA", ""), "QGIS", "QGIS4", "profiles",
        profile_name, "python", "plugins")
    saw_junction = saw_dir = False
    try:
        entries = list(os.scandir(plugins_src))
    except OSError:
        return False
    for e in entries:
        if not e.is_dir():
            continue
        if not os.path.exists(os.path.join(e.path, "metadata.txt")):
            continue
        dst = os.path.join(plugins_root, e.name)
        if not os.path.lexists(dst):
            continue
        if _is_reparse_point(dst):
            saw_junction = True
        else:
            saw_dir = True
    return saw_junction and not saw_dir


def build_dev_env(profile_name):
    """開発モード時に QGIS プロセスへ注入する環境変数を構築する。"""
    envs = {}

    def set_default(key, val):
        if not os.environ.get(key, "").strip():
            envs[key] = val

    set_default("QTWEBENGINE_REMOTE_DEBUGGING", "9222")
    set_default("QTWEBENGINE_CHROMIUM_FLAGS",
                "--disable-gpu --no-sandbox --disable-gpu-compositing")
    envs["WEBENGINE_AUTOOPEN"] = "1"

    harness = detect_harness_root()
    if harness:
        test_results = os.path.join(harness, "test-results")
        envs["WEBENGINE_LIVE_DIR"] = os.path.join(test_results, "live")
        envs["WEBENGINE_LOG_PATH"] = os.path.join(
            test_results, "plugin_load.log")
        if is_junction_deploy(harness, profile_name):
            envs["WEBENGINE_DEV_SRC"] = harness
        else:
            log("devモード(junction配置)以外のため WEBENGINE_DEV_SRC 未設定"
                "(配置済み実体dirが動作)")
    else:
        log("QGIS Live Harness が見つかりません。"
            "KASUGAI_HARNESS_DIR で指定できます。")
    return envs


# ---------------------------------------------------------------------------
# QGIS 起動
# ---------------------------------------------------------------------------

def _resolve_project_to_file(path_str, base_dir):
    """project_path エントリを .qgs/.qgz ファイルへ解決する。"""
    if not path_str:
        return None
    is_qgis_file = _is_qgis_project(path_str)
    candidates = ([path_str] if os.path.isabs(path_str)
                  else [path_str, os.path.join(base_dir, path_str)])
    for eff in candidates:
        if is_qgis_file:
            if os.path.isfile(eff):
                return eff
        elif os.path.isdir(eff):
            files = sorted(
                f for f in os.listdir(eff)
                if _is_qgis_project(f)
                and os.path.isfile(os.path.join(eff, f)))
            return os.path.join(eff, files[0]) if files else None
    return None


def role_customization_path(settings_dir, role):
    """ini/<role>.xml (QGIS4 カスタマイズ) を返す。"""
    p = os.path.join(settings_dir, "ini", "{}.xml".format(role))
    if os.path.exists(p):
        return p
    log("QGIS4 用ロールカスタマイズが見つかりません (期待: {})".format(p))
    return None


def write_global_settings_ini(settings_dir, role):
    """ini/qgis_global_settings.ini を生成しパスを返す。"""
    ini_dir = os.path.join(settings_dir, "ini")
    try:
        os.makedirs(ini_dir, exist_ok=True)
    except OSError as e:
        log("ini ディレクトリ作成失敗: {}".format(e))
        return None
    path = os.path.join(ini_dir, "qgis_global_settings.ini")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("[Variables]\nuserrole={}\n".format(role))
        return path
    except OSError as e:
        log("グローバル設定INI書き込み失敗: {}".format(e))
        return None


def launch_qgis(profile_name, project_paths, project_root, exe_path,
                role, dev_mode, settings_dir):
    """QGIS/QField を起動する。

    Rust版 launch_qgis の移植。project_paths の各要素を解決し、
    1プロジェクトにつき1プロセス起動する。
    戻り値: 起動したプロセス数。
    """
    qgis_path = exe_path
    if not qgis_path or not os.path.exists(qgis_path):
        qgis_path = find_qgis_path_from_registry() or ""
        if qgis_path:
            log("システム既定の QGIS を使用します: {}".format(qgis_path))
    if not qgis_path:
        log("QGISの実行ファイルが見つかりません。"
            "レジストリの関連付けを確認してください。")
        return 0

    is_qfield = "qfield" in os.path.basename(qgis_path).lower()
    customization = role_customization_path(settings_dir, role)
    global_ini = write_global_settings_ini(settings_dir, role)
    dev_env = build_dev_env(profile_name) if dev_mode else {}

    startup = os.path.join(settings_dir, "ini", "startup.py")
    if not os.path.exists(startup):
        startup = None

    env = dict(os.environ)
    env["PORTAL_USERROLE"] = role
    env.update(dev_env)

    launched = 0

    def spawn(project):
        nonlocal launched
        lower = qgis_path.lower()
        if lower.endswith((".bat", ".cmd")):
            args = ["cmd.exe", "/C", qgis_path]
        else:
            args = [qgis_path]
        if not is_qfield:
            args += ["--profile", profile_name]
            if customization:
                args += ["--customizationfile", customization]
            if global_ini:
                args += ["--globalsettingsfile", global_ini]
            if startup:
                args += ["--code", startup]
        if project:
            args.append(str(project))
        try:
            subprocess.Popen(  # nosec B603 - 引数はユーザ設定由来の信頼パス
                args, env=env, cwd=settings_dir,
                creationflags=CREATE_NO_WINDOW)
            launched += 1
            log("QGISの起動リクエストに成功しました: {}".format(
                project or "(プロジェクトなし)"))
        except OSError as e:
            log("QGISの起動に失敗しました: {}".format(e))

    if not project_paths:
        spawn(None)
        return launched
    for path_str in project_paths:
        spawn(_resolve_project_to_file((path_str or "").strip(), project_root))
    return launched


def auto_select_executable(settings, project_root, available=None):
    """CLI 自動選択: プロジェクトのバージョンに合う QGIS を返す。

    戻り値: exe パス (自動選択不可なら現行設定値または "")。
    """
    available = available if available is not None else list_qgis_versions()
    qgis_exe = settings.get("qgis_executable") or ""
    proj = settings.get("current_project") or (
        settings.get("project_path") or [None])[0]
    if not proj:
        return qgis_exe
    eff = proj if os.path.isabs(proj) else os.path.join(project_root, proj)
    ver = get_project_file_version(eff)
    if not ver:
        return qgis_exe
    match = find_matching_version(ver, available)
    if match:
        ql_major = _extract_major(qgis_exe.lower()) or ""
        if not qgis_exe or ql_major != ver.split(".")[0].lower():
            return match["path"]
        return qgis_exe
    log("プロジェクトファイルのバージョン {} に一致する QGIS が"
        "見つかりませんでした。システム既定で起動します。".format(ver))
    return ""


# ---------------------------------------------------------------------------
# drive_mappings (subst / rclone sync / mount)
# ---------------------------------------------------------------------------

def find_rclone(settings_dir=None):
    """rclone 実行ファイルを探す (PATH → 隣接 tools → C:\\devin\\tools)。"""
    exe = "rclone.exe" if IS_WINDOWS else "rclone"
    hit = shutil.which("rclone")
    if hit:
        return hit
    cands = []
    if settings_dir:
        cands += [
            os.path.join(settings_dir, "tools", "rclone", exe),
            os.path.join(settings_dir, "rclone", exe),
            os.path.join(settings_dir, exe),
        ]
    cands.append(os.path.join(r"C:\devin\tools", "rclone", exe))
    cands.append(os.path.join(r"C:\devin\tools", exe))
    for c in cands:
        if os.path.exists(c):
            return c
    return None


def run_robocopy(src, dst, exclude, aliases=None):
    """robocopy /MIR 同期。exit < 8 を成功とする。"""
    if aliases:
        src = expand_env_vars(resolve_path(src, aliases))
        dst = expand_env_vars(resolve_path(dst, aliases))
        exclude = [expand_env_vars(resolve_path(e, aliases)) for e in exclude]
    if not os.path.exists(src):
        log("robocopy: コピー元フォルダ '{}' が見つかりません"
            "。スキップします。".format(src))
        return False
    try:
        os.makedirs(dst, exist_ok=True)
    except OSError as e:
        log("robocopy: コピー先フォルダ作成失敗 ({}): {}".format(dst, e))
        return False
    log("robocopy: {} → {} コピー中...".format(src, dst))
    cmd = ["robocopy", src, dst, "/MIR", "/MT:8", "/R:1", "/W:0", "/NP"]
    if exclude:
        cmd.append("/XD")
        cmd += list(exclude)
    try:
        rc = subprocess.call(cmd, creationflags=CREATE_NO_WINDOW)  # nosec B603
    except OSError as e:
        log("robocopy 起動エラー: {}".format(e))
        return False
    if rc < 8:
        log("robocopy: 完了 (exit {})".format(rc))
        return True
    log("robocopy: エラー終了 (exit {})".format(rc))
    return False


def _drive_assigned(drive):
    return os.path.exists(drive.rstrip("\\/") + "\\")


def _subst_delete(drive):
    subprocess.call(["cmd", "/C", "subst", drive, "/D"],
                    creationflags=CREATE_NO_WINDOW)  # nosec B603


def _subst_assign(drive, folder):
    try:
        rc = subprocess.call(["subst", drive, folder],
                             creationflags=CREATE_NO_WINDOW)  # nosec B603
    except OSError as e:
        log("subst 起動エラー ({}): {}".format(drive, e))
        return False
    if rc == 0:
        log("subst: {} → {} を割り当てました".format(drive, folder))
        return True
    log("subst: {} の割り当てに失敗しました".format(drive))
    return False


def _subst_drive(m, aliases):
    """subst モード: フォルダをドライブに割り当てる。"""
    drive = m.get("drive", "")
    folder = m.get("local_cache") or ""
    if not drive or not folder:
        log("subst: drive/local_cache が未設定です")
        return
    folder = expand_env_vars(resolve_path(folder, aliases))
    src = m.get("robocopy_src")
    if src:
        log("Running robocopy for {}".format(drive))
        run_robocopy(src, folder, m.get("robocopy_exclude") or [], aliases)
    if _drive_assigned(drive):
        log("{} は既に割り当て済み。いったん解除して再割当てします。".format(drive))
        _subst_delete(drive)
    if not os.path.exists(folder):
        log("subst: 割当先フォルダが存在しません: {}".format(folder))
        return
    _subst_assign(drive, folder)


def _sync_drive(m, rclone_path):
    """sync モード: rclone sync → subst。"""
    drive = m.get("drive", "")
    cache = m.get("local_cache") or ""
    if not cache:
        log("rclone: mode=sync の場合 local_cache の指定が必要です"
            " (drive: {})".format(drive))
        return
    remote = m.get("remote")
    if not remote:
        log("rclone sync: remote の指定が必要です (drive: {})".format(drive))
        return
    log("rclone sync: {} → {} 同期中（変更分のみ）...".format(remote, cache))
    rc = subprocess.call([rclone_path, "sync", remote, cache],
                         creationflags=CREATE_NO_WINDOW)  # nosec B603
    log("rclone sync: {}".format("完了" if rc == 0 else "失敗"))
    if _drive_assigned(drive):
        log("{} は既に割り当て済み。いったん解除して再割当てします。".format(drive))
        _subst_delete(drive)
    _subst_assign(drive, cache)


def _mount_drive(m, rclone_path):
    """mount モード: rclone mount (要 WinFsp)。"""
    drive = m.get("drive", "")
    remote = m.get("remote")
    if not remote:
        log("rclone mount: remote の指定が必要です (drive: {})".format(drive))
        return
    if _drive_assigned(drive):
        log("{} は既にマウント済み。いったん解除して再マウントします。".format(
            drive))
        subprocess.call(["mountvol", drive, "/D"],
                        creationflags=CREATE_NO_WINDOW)  # nosec B603
    args = [rclone_path, "mount", remote, drive, "--no-console"]
    if m.get("read_only"):
        args.append("--read-only")
    for key, opt in (("vfs_cache_mode", "--vfs-cache-mode"),
                     ("vfs_cache_max_age", "--vfs-cache-max-age"),
                     ("vfs_cache_max_size", "--vfs-cache-max-size"),
                     ("vfs_cache_poll_interval",
                      "--vfs-cache-poll-interval"),
                     ("vfs_write_back", "--vfs-write-back")):
        v = m.get(key)
        if v is not None:
            args += [opt, str(v)]
    log("rclone: {} を {} にマウント開始しました。完了を待機中...".format(
        remote, drive))
    try:
        proc = subprocess.Popen(
            args, creationflags=CREATE_NO_WINDOW)  # nosec B603
    except OSError as e:
        log("rclone マウント失敗 ({} -> {}): {}".format(remote, drive, e))
        return
    deadline = time.time() + 30
    while time.time() < deadline:
        if _drive_assigned(drive):
            log("rclone: {} のマウント完了。".format(drive))
            return
        if proc.poll() is not None:
            break
        time.sleep(0.5)
    log("rclone: {} のマウントが30秒以内に完了しませんでした"
        "。続行します。".format(drive))


def mount_drive_mappings(mounts, settings):
    """drive_mappings の設定に従ってマウント/同期を実行する。"""
    if not mounts:
        return
    aliases = settings.get("path_aliases", {})
    for m in mounts:
        if (m.get("mode") or "subst") == "subst":
            _subst_drive(m, aliases)
    needs_rclone = any(
        (m.get("mode") or "subst") in ("sync", "mount") for m in mounts)
    rclone_path = find_rclone() if needs_rclone else None
    if needs_rclone and not rclone_path:
        log("rclone が見つかりません。sync/mount モードはスキップします。")
        return
    for m in mounts:
        mode = m.get("mode") or "subst"
        if mode == "sync":
            _sync_drive(m, rclone_path)
        elif mode == "mount":
            _mount_drive(m, rclone_path)


# ---------------------------------------------------------------------------
# local_sync (KASUGAI/yr-qgis-launcher 方式)
# ---------------------------------------------------------------------------

def read_version_file(d, filename):
    try:
        with open(os.path.join(d, filename), "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def write_version_file(d, filename, value):
    try:
        with open(os.path.join(d, filename), "w", encoding="utf-8") as f:
            f.write(value)
    except OSError as e:
        log("local_sync: バージョンファイル書き込み失敗 ({}): {}".format(
            os.path.join(d, filename), e))


def find_prefixed_folders(src, prefix):
    try:
        return sorted(
            e.name for e in os.scandir(src)
            if e.is_dir() and e.name.lower().startswith(prefix.lower()))
    except OSError:
        return []


def read_qgislocalsync_config(settings_dir):
    """qgislocalsync.config (key=value) を読み込む。"""
    p = os.path.join(settings_dir, "qgislocalsync.config")
    if not os.path.exists(p):
        return None
    cfg = {"sync_src": None, "sync_dst": None, "qfield_version": None,
           "qgis_version": None, "exclude_dirs": [],
           "portable_profile_version": None}
    try:
        with open(p, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return None
    for line in lines:
        line = line.strip()
        if not line or line.startswith(("#", ";")) or "=" not in line:
            continue
        key, val = (x.strip() for x in line.split("=", 1))
        if key == "SYNC_SRC":
            cfg["sync_src"] = val
        elif key == "SYNC_DST":
            cfg["sync_dst"] = val
        elif key == "QFIELD_VERSION":
            cfg["qfield_version"] = val
        elif key == "QGIS_VERSION":
            cfg["qgis_version"] = val
        elif key == "EXCLUDE_DIRS":
            cfg["exclude_dirs"] = [x for x in val.split() if x]
        elif key == "PORTABLE_PROFILE_VERSION":
            cfg["portable_profile_version"] = val
    return cfg


def resolve_local_sync_config(settings, settings_dir):
    """JSON local_sync と qgislocalsync.config を統合する。"""
    json_cfg = settings.get("local_sync")
    if not isinstance(json_cfg, dict):
        return None
    file = read_qgislocalsync_config(settings_dir) or {
        "sync_src": None, "sync_dst": None, "qfield_version": None,
        "qgis_version": None, "exclude_dirs": [],
        "portable_profile_version": None}
    for k in ("sync_src", "sync_dst", "qfield_version", "qgis_version",
              "portable_profile_version"):
        if file.get(k) is None:
            file[k] = json_cfg.get(k)
    if not file["exclude_dirs"]:
        file["exclude_dirs"] = list(json_cfg.get("exclude_dirs") or [])
    src = file.get("sync_src")
    if src:
        src_path = expand_env_vars(
            resolve_path(src, settings.get("path_aliases", {})))
        server = read_qgislocalsync_config(src_path)
        if server:
            for k in ("qfield_version", "qgis_version",
                      "portable_profile_version"):
                if server.get(k) is not None:
                    file[k] = server[k]
            if server["exclude_dirs"]:
                file["exclude_dirs"] = server["exclude_dirs"]
            if file.get("sync_dst") is None:
                file["sync_dst"] = server.get("sync_dst")
    return file


def resolve_kasugai_qgis_version(settings, settings_dir):
    """配布元 (SYNC_SRC) → ローカルの順で kasugai_qgis_version を返す。"""
    cfg = settings.get("local_sync")
    src = (cfg or {}).get("sync_src")
    if src:
        src_path = expand_env_vars(
            resolve_path(src, settings.get("path_aliases", {})))
        s = _read_json(os.path.join(src_path, SETTINGS_FILE))
        if isinstance(s, dict):
            v = s.get("kasugai_qgis_version")
            if v is not None:
                return str(v)
    v = settings.get("kasugai_qgis_version")
    return str(v) if v is not None else None


def local_sync_needed(settings, settings_dir):
    """local_sync の実行要否を判定する。"""
    config = resolve_local_sync_config(settings, settings_dir)
    if not config:
        return False
    src, dst = config.get("sync_src"), config.get("sync_dst")
    if not src or not dst:
        return False
    aliases = settings.get("path_aliases", {})
    src = expand_env_vars(resolve_path(src, aliases))
    dst = expand_env_vars(resolve_path(dst, aliases))
    if not os.path.exists(src):
        return False
    if not os.path.exists(dst):
        return True
    qfield_folders = find_prefixed_folders(src, "QField")
    if config.get("qfield_version"):
        if (read_version_file(dst, "LOCAL_QFIELD_VERSION")
                != config["qfield_version"] and qfield_folders):
            return True
    qgis_folders = find_prefixed_folders(src, "QGIS")
    if config.get("qgis_version"):
        if (read_version_file(dst, "LOCAL_QGIS_VERSION")
                != config["qgis_version"] and qgis_folders):
            return True
    if config.get("portable_profile_version"):
        if (read_version_file(dst, "portable.ver")
                != config["portable_profile_version"]
                and os.path.exists(os.path.join(src, "portable_profile"))):
            return True
    ver = resolve_kasugai_qgis_version(settings, settings_dir)
    if ver and read_version_file(dst, "LOCAL_KASUGAI_QGIS_VERSION") != ver:
        return True
    return False


def _robocopy_local(src, dst, exclude, label):
    if not os.path.exists(src):
        log("local_sync: {}: コピー元 '{}' が見つかりません。".format(label, src))
        return
    try:
        os.makedirs(dst, exist_ok=True)
    except OSError as e:
        log("local_sync: {}: コピー先作成失敗 ({}): {}".format(label, dst, e))
        return
    log("local_sync: {}: {} → {}".format(label, src, dst))
    cmd = ["robocopy", src, dst, "/MIR", "/MT:8", "/R:1", "/W:0", "/NP"]
    if exclude:
        cmd.append("/XD")
        cmd += list(exclude)
    try:
        rc = subprocess.call(cmd, creationflags=CREATE_NO_WINDOW)  # nosec B603
    except OSError as e:
        log("local_sync: {}: robocopy 起動エラー: {}".format(label, e))
        return
    if rc < 8:
        log("local_sync: {}: 完了 (exit {})".format(label, rc))
    else:
        log("local_sync: {}: robocopy エラー終了 (exit {})".format(label, rc))


def run_local_sync(settings, settings_dir):
    """KASUGAI/yr-qgis-launcher 方式のローカル自動同期を実行する。"""
    if not local_sync_needed(settings, settings_dir):
        log("local_sync: アップデートは不要です。")
        return False
    config = resolve_local_sync_config(settings, settings_dir)
    aliases = settings.get("path_aliases", {})
    src = expand_env_vars(resolve_path(config["sync_src"], aliases))
    dst = expand_env_vars(resolve_path(config["sync_dst"], aliases))
    log("local_sync: {} → {}".format(src, dst))
    if not os.path.exists(src):
        log("local_sync: SYNC_SRC '{}' が見つかりません"
            "。スキップします。".format(src))
        return False
    try:
        os.makedirs(dst, exist_ok=True)
    except OSError as e:
        log("local_sync: SYNC_DST 作成失敗 ({}): {}".format(dst, e))
        return False

    exclude = list(config.get("exclude_dirs") or [])
    qfield_folders = find_prefixed_folders(src, "QField")
    qgis_folders = find_prefixed_folders(src, "QGIS")
    top_excludes = list(exclude)
    for f in qfield_folders + qgis_folders:
        if f not in top_excludes:
            top_excludes.append(f)
    _robocopy_local(src, dst, top_excludes, "トップレベル")

    if config.get("qfield_version"):
        ver = config["qfield_version"]
        if read_version_file(dst, "LOCAL_QFIELD_VERSION") != ver \
                and qfield_folders:
            log("local_sync: QField 更新 ({} → {})".format(
                read_version_file(dst, "LOCAL_QFIELD_VERSION"), ver))
            for folder in qfield_folders:
                s = os.path.join(src, folder)
                if os.path.exists(s):
                    _robocopy_local(s, os.path.join(dst, folder),
                                    exclude, "QField {}".format(folder))
            write_version_file(dst, "LOCAL_QFIELD_VERSION", ver)

    if config.get("qgis_version"):
        ver = config["qgis_version"]
        if read_version_file(dst, "LOCAL_QGIS_VERSION") != ver \
                and qgis_folders:
            log("local_sync: QGIS 更新 ({} → {})".format(
                read_version_file(dst, "LOCAL_QGIS_VERSION"), ver))
            for folder in qgis_folders:
                s = os.path.join(src, folder)
                if os.path.exists(s):
                    _robocopy_local(s, os.path.join(dst, folder),
                                    exclude, "QGIS {}".format(folder))
            write_version_file(dst, "LOCAL_QGIS_VERSION", ver)

    if config.get("portable_profile_version"):
        ver = config["portable_profile_version"]
        s = os.path.join(src, "portable_profile")
        if read_version_file(dst, "portable.ver") != ver \
                and os.path.exists(s):
            log("local_sync: portable_profile 更新 ({} → {})".format(
                read_version_file(dst, "portable.ver"), ver))
            _robocopy_local(s, os.path.join(dst, "portable_profile"),
                            exclude, "portable_profile")
            write_version_file(dst, "portable.ver", ver)

    ver = resolve_kasugai_qgis_version(settings, settings_dir)
    if ver:
        write_version_file(dst, "LOCAL_KASUGAI_QGIS_VERSION", ver)
    log("local_sync: 完了")
    return True


# ---------------------------------------------------------------------------
# 配布プロファイルのシード/リセット
# ---------------------------------------------------------------------------

def _copy_dir_contents_skip(src, dst):
    """src 直下を dst へコピー。既存ファイルは上書きしない。

    コピー先が junction/symlink の場合は中に書き込まない。
    """
    os.makedirs(dst, exist_ok=True)
    for entry in os.scandir(src):
        to = os.path.join(dst, entry.name)
        if entry.is_dir(follow_symlinks=False):
            if os.path.lexists(to) and _is_reparse_point(to):
                continue
            if not os.path.exists(to):
                os.makedirs(to)
            _copy_dir_contents_skip(entry.path, to)
        elif entry.is_file(follow_symlinks=False):
            if not os.path.exists(to):
                shutil.copy2(entry.path, to)


def copy_profiles_at_startup(settings_dir, settings=None):
    """配布 profiles を %APPDATA%\\QGIS\\ 配下へシードする。

    settings に profile_source_url がある場合は先にリモート同期する。
    """
    if settings:
        try:
            sync_remote_profiles(settings, settings_dir)
        except RuntimeError as e:
            log("profile_source_url 同期失敗 (ローカルで続行): {}".format(e))
    base = os.path.join(settings_dir, "profiles")
    if not os.path.isdir(base):
        log("distribution profiles not found")
        return
    for target in qgis_profile_paths():
        qgis_dir = os.path.dirname(target)
        try:
            os.makedirs(qgis_dir, exist_ok=True)
        except OSError as e:
            log("failed to create target {}: {}".format(qgis_dir, e))
            continue
        log("Copying profiles from {} -> {}".format(base, qgis_dir))
        try:
            _copy_dir_contents_skip(base, qgis_dir)
        except OSError as e:
            log("profile copy error: {}".format(e))
        # --code ini/startup.py に一本化したため旧 startup.py を除去
        profiles_dir = os.path.join(target, "profiles")
        if os.path.isdir(profiles_dir):
            for name in os.listdir(profiles_dir):
                startup = os.path.join(
                    profiles_dir, name, "python", "startup.py")
                if os.path.exists(startup):
                    try:
                        os.remove(startup)
                        log("startup.py を削除（--code に一本化）: {}".format(
                            startup))
                    except OSError:
                        pass
    if settings and settings.get("required_plugins"):
        try:
            ensure_plugins(settings, settings_dir)
        except RuntimeError as e:
            log("required_plugins 導入失敗 (続行): {}".format(e))


def reset_profiles(settings_dir, settings=None):
    """既存 QGIS プロファイルを削除して配布プロファイルを再コピーする。"""
    if settings:
        try:
            sync_remote_profiles(settings, settings_dir)
        except RuntimeError as e:
            log("profile_source_url 同期失敗 (ローカルで続行): {}".format(e))
    base = os.path.join(settings_dir, "profiles")
    if not os.path.isdir(base):
        return "distribution profiles not found"
    log("既存プロファイルを削除しています")
    for p in qgis_profile_paths():
        probe = os.path.join(p, "profiles")
        target_dir = probe if os.path.isdir(probe) else p
        if not os.path.isdir(target_dir):
            continue
        for name in os.listdir(target_dir):
            path = os.path.join(target_dir, name)
            if not os.path.isdir(path):
                continue
            if target_dir == p and name.lower() == "profiles":
                continue
            try:
                shutil.rmtree(path)
                log("削除: {}".format(path))
            except OSError as e:
                log("プロファイル削除失敗 {}: {}".format(path, e))
    log("配布プロファイルをコピーしています")
    copy_profiles_at_startup(settings_dir, settings)
    return None


# ---------------------------------------------------------------------------
# リモートプロファイル配布 (profile_source_url)
# ---------------------------------------------------------------------------

PROFILES_VERSION_FILE = "profiles_version"


def _fetch_json(url, timeout=15):
    req = urllib.request.Request(
        url, headers={"User-Agent": "geo_launcher/1.0"})
    try:
        # nosec B310 - profile_source_url はユーザー設定由来
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        raise RuntimeError("マニフェスト取得失敗 ({}): {}".format(url, e))


def _verify_sha256(path, expected):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().lower() == expected.strip().lower()


def _safe_extract_zip(zip_path, dst):
    """zip を dst へ展開する。パストラバーサルは拒否。"""
    root = os.path.realpath(dst)
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            name = info.filename.replace("\\", "/")
            target = os.path.realpath(os.path.join(dst, name))
            if target != root and not target.startswith(root + os.sep):
                raise RuntimeError(
                    "zip 内に不正なパスがあります: {}".format(info.filename))
        z.extractall(dst)


def sync_remote_profiles(settings, settings_dir):
    """profile_source_url のマニフェストから配布プロファイルを同期する。

    マニフェスト形式::
        {"version": "...", "url": ".../profiles.zip", "sha256": "..."}

    - url 未設定時: False を返して何もしない (ローカル profiles/ を使う)
    - version が profiles_version と同じ: 最新とみなし False
    - 取得成功時: <settings_dir>/profiles を zip 内容で丸ごと置換し
      バージョンを記録して True を返す
    """
    url = (settings.get("profile_source_url") or "").strip()
    if not url:
        return False
    manifest = _fetch_json(url)
    version = str(manifest.get("version") or "")
    dl_url = manifest.get("url")
    if not version or not dl_url:
        raise RuntimeError(
            "マニフェストに version/url がありません: {}".format(url))
    local_ver = read_version_file(settings_dir, PROFILES_VERSION_FILE)
    if local_ver == version:
        log("profiles: リモートは最新です (version={})".format(version))
        return False
    log("profiles: リモート更新 {} → {} を取得します".format(
        local_ver or "(なし)", version))

    fd, tmp = tempfile.mkstemp(
        prefix="geo_launcher_profiles_", suffix=".zip")
    os.close(fd)
    req = urllib.request.Request(
        dl_url, headers={"User-Agent": "geo_launcher/1.0"})
    try:
        # nosec B310 - profile_source_url はユーザー設定由来
        with urllib.request.urlopen(req, timeout=300) as r, \
                open(tmp, "wb") as f:
            shutil.copyfileobj(r, f)
    except Exception as e:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise RuntimeError(
            "profiles.zip 取得失敗 ({}): {}".format(dl_url, e))
    sha = manifest.get("sha256")
    if sha and sha.strip():
        if not _verify_sha256(tmp, sha):
            raise RuntimeError(
                "profiles.zip の SHA-256 が一致しません")
        log("profiles: SHA-256 検証 OK")

    # まず temp に展開してから profiles/ を丸ごと差し替える (ミラー)
    base = os.path.join(settings_dir, "profiles")
    new_dir = base + ".new"
    old_dir = base + ".old"
    shutil.rmtree(new_dir, ignore_errors=True)
    shutil.rmtree(old_dir, ignore_errors=True)
    os.makedirs(new_dir, exist_ok=True)
    try:
        _safe_extract_zip(tmp, new_dir)
    except Exception:
        shutil.rmtree(new_dir, ignore_errors=True)
        raise
    try:
        if os.path.isdir(base):
            os.replace(base, old_dir)
        os.replace(new_dir, base)
        shutil.rmtree(old_dir, ignore_errors=True)
    except OSError as e:
        # 差し替え失敗時は in-place 展開へフォールバック
        log("profiles/ 差し替え失敗 ({}). in-place 展開します".format(e))
        _safe_extract_zip(tmp, base)
        shutil.rmtree(new_dir, ignore_errors=True)
        shutil.rmtree(old_dir, ignore_errors=True)
    try:
        os.remove(tmp)
    except OSError:
        pass
    write_version_file(settings_dir, PROFILES_VERSION_FILE, version)
    log("profiles: リモート配布 version={} を適用しました".format(version))
    return True


# ---------------------------------------------------------------------------
# QGIS Live Harness セッション
# ---------------------------------------------------------------------------

def live_registry_dir():
    env = os.environ.get("QGIS_LIVE_REGISTRY", "").strip()
    if env:
        return env
    home = os.environ.get("USERPROFILE") or os.environ.get("HOME") or ""
    return os.path.join(home, ".qgis-live")


def _port_alive(port):
    try:
        with socket.create_connection(("127.0.0.1", int(port)), 0.2):
            return True
    except (OSError, ValueError):
        return False


def list_live_sessions():
    """~/.qgis-live/<pid>-qgis_live_driver.json を列挙し生存判定する。"""
    out = []
    reg = live_registry_dir()
    try:
        entries = sorted(os.listdir(reg))
    except OSError:
        return out
    for name in entries:
        if not name.endswith("-qgis_live_driver.json"):
            continue
        v = _read_json(os.path.join(reg, name))
        if not isinstance(v, dict):
            continue
        port = v.get("http_port")
        alive = _port_alive(port) if port else False
        if not alive:
            started = v.get("started")
            try:
                stale = (time.time() - float(started)) > 120
            except (TypeError, ValueError):
                stale = False
            if stale:
                try:
                    os.remove(os.path.join(reg, name))
                except OSError:
                    pass
                continue
        v.pop("token", None)
        v["alive"] = alive
        v["registry_file"] = name
        out.append(v)
    out.sort(key=lambda x: -(x.get("started") or 0))
    return out


# ---------------------------------------------------------------------------
# 必須プラグインの自動インストール (required_plugins)
# ---------------------------------------------------------------------------

PLUGINS_XML_URL = "https://plugins.qgis.org/plugins.xml"


def _ver_key(s):
    parts = parse_version_parts(s or "")
    return tuple(int(p) for p in parts) or (0,)


def resolve_plugin_download(pid, qgis_version="4.0"):
    """公式リポジトリの plugins.xml から (version, download_url) を解決する。

    見つからない場合は None。
    """
    import xml.etree.ElementTree as ET
    url = "{}?qgis={}".format(PLUGINS_XML_URL, qgis_version)
    req = urllib.request.Request(
        url, headers={"User-Agent": "geo_launcher/1.0"})
    try:
        # nosec B310 - 公式リポジトリ固定URL
        with urllib.request.urlopen(req, timeout=30) as r:
            root = ET.fromstring(r.read())
    except Exception as e:
        raise RuntimeError("plugins.xml 取得失敗: {}".format(e))
    best = None
    for el in root.iter("pyqgis_plugin"):
        name = (el.get("package_name") or "").strip() \
            or (el.get("name") or "").strip() \
            or (el.findtext("name") or "").strip()
        if name != pid:
            continue
        ver = (el.findtext("version") or "").strip()
        dl = (el.findtext("download_url") or "").strip()
        if dl and (best is None or _ver_key(ver) > _ver_key(best[0])):
            best = (ver, dl)
    return best


def _target_profile_names(settings_dir, settings, profile_names=None):
    """プラグインをインストールする対象プロファイル名の集合。"""
    if profile_names:
        return sorted(set(profile_names))
    names = set()
    cur = settings.get("profile")
    if cur:
        names.add(cur)
    for root in qgis_profile_paths():
        pd = os.path.join(root, "profiles")
        if os.path.isdir(pd):
            names.update(
                d for d in os.listdir(pd)
                if os.path.isdir(os.path.join(pd, d)))
    base = os.path.join(settings_dir, "profiles")
    if os.path.isdir(base):
        for dirpath, dirnames, _ in os.walk(base):
            if os.path.basename(dirpath) == "profiles":
                names.update(dirnames)
    return sorted(names)


def _set_ini_flag(ini_path, section, key, value):
    """INI の [section] key=value を設定する(ファイルが無ければ作成)。

    行ベースで編集する。configparser は QGIS4.ini の重複キーや
    独自構文で全体を失う可能性があるため使わない。
    """
    lines = []
    if os.path.exists(ini_path):
        with open(ini_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    header = "[{}]".format(section)
    in_sec = False
    sec_end = -1  # セクション最終行の次の index
    key_idx = -1
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            in_sec = (s == header)
            if in_sec:
                sec_end = i + 1
            continue
        if in_sec:
            sec_end = i + 1
            if s.split("=", 1)[0].strip() == key:
                key_idx = i
    entry = "{}={}".format(key, value)
    if key_idx >= 0:
        lines[key_idx] = entry
    elif sec_end >= 0:
        lines.insert(sec_end, entry)
    else:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend([header, entry])
    os.makedirs(os.path.dirname(ini_path) or ".", exist_ok=True)
    with open(ini_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def _download(url, dst, timeout=300):
    req = urllib.request.Request(
        url, headers={"User-Agent": "geo_launcher/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r, \
                open(dst, "wb") as f:  # nosec B310 - ユーザー設定/公式リポジトリ由来
            shutil.copyfileobj(r, f)
    except Exception as e:
        raise RuntimeError("ダウンロード失敗 ({}): {}".format(url, e))


def ensure_plugins(settings, settings_dir, qgis_version="4.0",
                   profile_names=None):
    """required_plugins の指定プラグインを対象プロファイルへ自動インストールする。

    settings["required_plugins"] の形式::

        [{"id": "geo_search"},                       # 公式リポジトリ最新版
         {"id": "mmqgis", "version": "2024.11.8"},   # 版指定(メモ用・解決は最新)
         {"id": "x_plugin",
          "url": "https://.../x_plugin.zip",
          "sha256": "..."}]                          # 任意URL(sha256推奨)

    - 各対象プロファイルの python/plugins/<id> が無ければ zip を
      ダウンロードして展開し、QGIS4.ini [PythonPlugins] <id>=true で
      有効化する(実体はこのプラグイン内に持たない)
    - url 未指定時は公式リポジトリ plugins.xml から最新版を解決
    - 戻り値: 新たにインストールしたプラグイン id のリスト
    """
    reqs = [r for r in (settings.get("required_plugins") or [])
            if isinstance(r, dict)]
    if not reqs:
        return []
    names = _target_profile_names(settings_dir, settings, profile_names)
    if not names:
        log("required_plugins: 対象プロファイルがありません")
        return []
    roots = qgis_profile_paths()
    targets = [
        (root, name, os.path.join(
            root, "profiles", name, "python", "plugins"))
        for root in roots for name in names]
    installed = []
    tmpdir = tempfile.mkdtemp(prefix="geo_launcher_plugins_")
    try:
        for req in reqs:
            pid = (req.get("id") or req.get("name") or "").strip()
            if not pid:
                continue
            missing = [d for _, _, d in targets
                       if not os.path.isdir(os.path.join(d, pid))]
            if not missing:
                log("required_plugins: {} は全プロファイルに導入済み"
                    .format(pid))
                continue
            url = (req.get("url") or "").strip()
            if not url:
                resolved = resolve_plugin_download(pid, qgis_version)
                if not resolved:
                    log("required_plugins: {} が公式リポジトリに"
                        "見つかりません".format(pid))
                    continue
                log("required_plugins: {} version={} を取得します"
                    .format(pid, resolved[0]))
                url = resolved[1]
            zpath = os.path.join(tmpdir, pid + ".zip")
            _download(url, zpath)
            sha = (req.get("sha256") or "").strip()
            if sha:
                if not _verify_sha256(zpath, sha):
                    raise RuntimeError(
                        "required_plugins: {} の SHA-256 が"
                        "一致しません".format(pid))
                log("required_plugins: {} SHA-256 検証 OK".format(pid))
            for d in missing:
                os.makedirs(d, exist_ok=True)
                _safe_extract_zip(zpath, d)
            for root, name, d in targets:
                if d in missing:
                    ini = os.path.join(
                        root, "profiles", name, "QGIS", "QGIS4.ini")
                    try:
                        _set_ini_flag(
                            ini, "PythonPlugins", pid, "true")
                    except OSError as e:
                        log("required_plugins: ini 更新失敗 {}: {}"
                            .format(ini, e))
            log("required_plugins: {} を {} プロファイルへ導入しました"
                .format(pid, len(missing)))
            installed.append(pid)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    return installed
