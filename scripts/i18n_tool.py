# -*- coding: utf-8 -*-
"""i18n ツール(全プラグイン共通)。

カタログは <plugin>/i18n/<lang>.json (UTF-8、{context: {source: translation}})。
Qt Linguist/.ts/.qm は使わない(AGENTS.md「国際化(i18n)」参照)。

使い方:
  python scripts/i18n_tool.py convert [plugin_id ...]
      i18n/ 内の *.ts を <lang>.json に変換する(upstream .ts 取り込み用)
  python scripts/i18n_tool.py check [plugin_id ...]
      ソース(.pyの tr()/translate()/QT_TRANSLATE_NOOP と .ui の <string>)を
      走査し、カタログに存在しないキーとカタログ側の不要キーを報告する

引数省略時は qgis-plugin/ 下の i18n/ を持つ全プラグインが対象。
check は未登録があれば終了コード1。
"""

import json
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN_ROOT = os.path.join(ROOT, "qgis-plugin")
LANGS = ("de", "es", "fr", "hi", "it", "ja", "pt", "ru", "zh")


def _plugins(args):
    if args:
        return [os.path.join(PLUGIN_ROOT, a) for a in args]
    return sorted(
        os.path.join(PLUGIN_ROOT, d)
        for d in os.listdir(PLUGIN_ROOT)
        if os.path.isdir(os.path.join(PLUGIN_ROOT, d, "i18n")))


def _lang_of(ts_path):
    """geo_excel_ja.ts / ja.ts / LegendView_ja.ts → 'ja'"""
    stem = os.path.splitext(os.path.basename(ts_path))[0]
    return stem.rsplit("_", 1)[-1].lower()


def convert_ts(ts_path, out_path=None):
    """1つの .ts を {context: {source: translation}} dict に変換。

    空・vanished/obsolete の訳は除外。numerus は先頭の訳文のみ採用
    (辞書方式では複数形を扱わない簡易仕様)。
    """
    tree = ET.parse(ts_path)
    catalog = {}
    for ctx in tree.getroot().iter("context"):
        name = (ctx.findtext("name") or "").strip() or "default"
        messages = catalog.setdefault(name, {})
        for msg in ctx.iter("message"):
            if msg.get("numerus") == "yes":
                tr_el = msg.find("translation")
                text = None
                if tr_el is not None:
                    nf = tr_el.find("numerusform")
                    text = nf.text if nf is not None else tr_el.text
            else:
                tr_el = msg.find("translation")
                if tr_el is None or tr_el.get("type") in ("vanished", "obsolete"):
                    continue
                text = tr_el.text
            source = msg.findtext("source")
            if source is None or not text or not text.strip():
                continue
            messages[source] = text
    catalog = {c: m for c, m in catalog.items() if m}
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2,
                      sort_keys=True)
            f.write("\n")
    return catalog


def cmd_convert(args):
    for plugin_dir in _plugins(args):
        i18n_dir = os.path.join(plugin_dir, "i18n")
        for name in sorted(os.listdir(i18n_dir)):
            if not name.endswith(".ts"):
                continue
            lang = _lang_of(name)
            out = os.path.join(i18n_dir, lang + ".json")
            cat = convert_ts(os.path.join(i18n_dir, name), out)
            n = sum(len(m) for m in cat.values())
            print(f"{os.path.basename(plugin_dir)}: {name} -> "
                  f"{lang}.json ({n} entries)")


# ---- check ---------------------------------------------------------------

_RE_CTX_TR = re.compile(
    r'(?:translate|QT_TRANSLATE_NOOP)\(\s*'
    r'([ur]*)(["\'])((?:\\.|(?!\2).)*?)\2'
    r'\s*,\s*'
    r'([ur]*)(["\'])((?:\\.|(?!\5).)*?)\5')
_RE_SELF_TR = re.compile(
    r'\.tr\(\s*([ur]*)(["\'])((?:\\.|(?!\2).)*?)\2')
_RE_UI_STRING = re.compile(
    r'<string(?:\s[^>]*)?>([^<]+)</string>')
_RE_UI_NOTR = re.compile(r'<string[^>]*\snotr\s*=\s*"true"')
_RE_UI_CLASS = re.compile(r"<class>([^<]+)</class>")
_SKIP_FILES = {"i18n_json.py"}


def _py_str(prefix, quote, body):
    """スキャンしたリテラル断片をPythonの文字列値に戻す。"""
    import ast
    literal = prefix + quote + body + quote
    try:
        return ast.literal_eval(literal)
    except (ValueError, SyntaxError):
        return body


def _iter_sources(plugin_dir):
    """(context|None, source, fname) を yield。context=None は全context検索。"""
    import html as _html
    for dirpath, _dirs, files in os.walk(plugin_dir):
        if "__pycache__" in dirpath:
            continue
        for fname in files:
            if fname in _SKIP_FILES:
                continue
            path = os.path.join(dirpath, fname)
            if fname.endswith(".py"):
                try:
                    with open(path, encoding="utf-8") as f:
                        text = f.read()
                except (OSError, UnicodeDecodeError):
                    continue
                for m in _RE_CTX_TR.finditer(text):
                    yield (_py_str(*m.group(1, 2, 3)),
                           _py_str(*m.group(4, 5, 6)), fname)
                for m in _RE_SELF_TR.finditer(text):
                    yield (None, _py_str(*m.group(1, 2, 3)), fname)
            elif fname.endswith(".ui"):
                try:
                    with open(path, encoding="utf-8") as f:
                        text = f.read()
                except (OSError, UnicodeDecodeError):
                    continue
                m = _RE_UI_CLASS.search(text)
                ctx = m.group(1) if m else None
                for sm in _RE_UI_STRING.finditer(text):
                    line_start = text.rfind("<string", 0, sm.end())
                    seg = text[line_start:sm.end()]
                    if _RE_UI_NOTR.search(seg):
                        continue
                    yield (ctx, _html.unescape(sm.group(1)), fname)


def _load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def cmd_check(args):
    missing_total = 0
    for plugin_dir in _plugins(args):
        pid = os.path.basename(plugin_dir)
        i18n_dir = os.path.join(plugin_dir, "i18n")
        sources = {}  # (ctx|None, source) -> set of files
        for ctx, src, fname in _iter_sources(plugin_dir):
            sources.setdefault((ctx, src), set()).add(fname)
        union_cat = {}
        for name in os.listdir(i18n_dir):
            if name.endswith(".json"):
                for c, msgs in _load_json(
                        os.path.join(i18n_dir, name)).items():
                    union_cat.setdefault(c, {}).update(msgs)

        missing = []
        for (ctx, src), files in sorted(
                sources.items(), key=lambda kv: (kv[0][0] or "", kv[0][1])):
            hit = union_cat.get(ctx, {}).get(src) if ctx else None
            if hit is None:
                hit = next(
                    (m[src] for m in union_cat.values()
                     if isinstance(m, dict) and src in m), None)
            if hit is None and any(
                    src in k for msgs in union_cat.values()
                    for k in msgs):
                # 複数リテラル連結の断片など、登録キーの部分文字列は除外
                continue
            if hit is None:
                missing.append((ctx, src, sorted(files)[0]))
        if missing:
            missing_total += len(missing)
            print(f"[{pid}] カタログ未登録 {len(missing)} 件 "
                  f"(実行時は英語にフォールバック):")
            for ctx, src, fname in missing:
                label = ctx or "(self.tr)"
                short = src if len(src) <= 70 else src[:67] + "..."
                print(f"  {label}: {short}   [{fname}]")
        else:
            print(f"[{pid}] OK ({len(sources)} sources)")
    return 1 if missing_total else 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    rest = sys.argv[2:]
    if cmd == "convert":
        sys.exit(cmd_convert(rest) or 0)
    elif cmd == "check":
        sys.exit(cmd_check(rest))
    else:
        print(__doc__)
        sys.exit(2)
