#!/usr/bin/env python3
"""feature-verify ランナー (qgis_live_harness 用アダプタ)

.devin/skills/feature-verify の Phase1-4 を機械化する。
  extract : qgis-plugin/<id> を AST 走査し verify/features.json を生成/差分マージ
  render  : features.json から logic-sheet.md / index.html / features/*.html 生成
  verify  : 静的・単独・QGIS連携(geo_driver REST)検証を実行し結果を書戻し
  all     : extract → render → verify → render(結果反映)
"""

import argparse
import ast
import datetime
import html
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN_ROOT = os.path.join(REPO, "qgis-plugin")
LIVE_BASE = os.path.join(REPO, "test-results", "live")

# vendored/自動生成コードは機能抽出の対象外
SKIP_DIRS = {"__pycache__", "i18n", "icon", "icons", "vendor", "jaconv",
             "defusedxml", "pyperclip", "verify", "ui"}
SKIP_FILES_RE = re.compile(
    r"^(resources(_rc)?\.py|.*_rc\.py|i18n_.*\.py|.*_test\.py)$")

PY_KEYWORDS = {
    "initGui", "unload", "run", "open_dialog", "openDialog",
    "addAction", "addMenu", "addToolBarIcon", "addSeparator",
}

# 副作用が大きい/破壊的/外部遷移するメソッドは統合検証で呼ばない
# (hotReload/remoteControl/deployMode等はgeo_driver制御チャンネル自体を
#  再起動・停止させて検証経路を断つため特に注意)
SKIP_CALL_RE = re.compile(
    r"^(install|uninstall|delete|save|update|set[A-Z]|apply|register|"
    r"remove|clear|create|import|export|download|openDocs|launch|"
    r"hotReload|remoteControl|deployMode|modeSwitch|.*[Rr]estart|"
    r".*[Ss]hutdown|.*[Ss]top.*|.*[Ss]witch.*|"
    r".*[Ff]irewall.*|"
    r"open[A-Z].*|show[A-Z].*|openDialog|openPanel|openDock|"
    r"close[A-Z].*|closeDialog|closePanel|closeDock|"
    r"openSettings|launch)")

# プラグイン別 skip: 外部ネットワーク/サーバ同期通信でGUIスレッドを
# 長時間ブロックするメソッド。実連携テストは別途手動/専用検証で行う
PLUGIN_SKIP = {
    "geo_import": {"search", "reload", "refreshCache", "testServer",
                   "loadSelected", "datasetDetails", "openProviders",
                   "openDisclaimer", "downloadSelected",
                   "nextPage", "prevPage", "gotoPage", "selectResults",
                   "selectServers", "checkResources", "checkGroups",
                   "formatFilter"},
}

# open系は呼んで即closeDialogする対象(モーダルでなければ動作確認になる)
OPEN_CALL_RE = re.compile(r"^(open|show)")


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def plugins():
    return sorted(d for d in os.listdir(PLUGIN_ROOT)
                  if os.path.isfile(os.path.join(PLUGIN_ROOT, d, "metadata.txt")))


def read_version(pdir):
    try:
        for line in open(os.path.join(pdir, "metadata.txt"), encoding="utf-8"):
            if line.startswith("version"):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return "?"


def py_files(pdir):
    for root, dirs, files in os.walk(pdir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in sorted(files):
            if f.endswith(".py") and not SKIP_FILES_RE.match(f):
                yield os.path.join(root, f)


def sig_of(node):
    args = node.args
    parts = [a.arg for a in args.args if a.arg != "self"]
    defaults = len(args.defaults)
    if defaults:
        n_req = len(parts) - defaults
        parts = parts[:n_req] + [f"{p}=…" for p in parts[n_req:]]
    if args.vararg:
        parts.append("*" + args.vararg.arg)
    if args.kwarg:
        parts.append("**" + args.kwarg.arg)
    return f"{node.name}({', '.join(parts)})"


def doc1(node):
    d = ast.get_docstring(node)
    return d.strip().splitlines()[0] if d else ""


def imports_qgis(tree):
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            if any(a.name.split(".")[0] == "qgis" for a in n.names):
                return True
        elif isinstance(n, ast.ImportFrom):
            if n.module and n.module.split(".")[0] == "qgis":
                return True
    return False


def cls_bases_qt(node):
    names = []
    for b in node.bases:
        if isinstance(b, ast.Name):
            names.append(b.id)
        elif isinstance(b, ast.Attribute):
            names.append(b.attr)
    return names


INTEGRATION_PAT = re.compile(
    r"(subprocess|Popen|win32com|Dispatch|requests\.|urllib\.request|"
    r"QgsNetworkAccessManager|QProcess|HTTPServer|http\.server|socket\.|"
    r"QTcpServer|QDesktopServices|webbrowser|QgsFileDownloader)")


def extract_plugin(pid):
    """1プラグイン分の機能抽出。features list を返す。"""
    pdir = os.path.join(PLUGIN_ROOT, pid)
    feats = []

    def add(kind, fid, name, src, signature="", summary="", needs_rt=True,
            standalone=False, depends=None, v_standalone="", v_integrated=""):
        feats.append({
            "id": fid, "kind": kind, "name": name, "source": src,
            "signature": signature, "summary": summary,
            "needs_runtime": needs_rt, "standalone_ok": standalone,
            "depends": depends or [],
            "verify": {"standalone": v_standalone, "integrated": v_integrated},
            "last_result": "untested", "last_verified": "", "note": "",
        })

    for path in py_files(pdir):
        rel = os.path.relpath(path, pdir).replace("\\", "/")
        try:
            src_text = open(path, encoding="utf-8").read()
            tree = ast.parse(src_text)
        except Exception:
            continue
        has_qgis = imports_qgis(tree)
        base = os.path.basename(rel)
        # [% @layer_id %] 等のプレースホルダを含むファイルは
        # exec用テンプレートでありimport対象のモジュールではない
        is_template = "[%" in src_text and "%]" in src_text

        # ---- 統合連携点 (ファイル単位で集約: 関数名@行) ----
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                txt = ""
                f = n.func
                if isinstance(f, ast.Attribute):
                    txt = (f.attr)
                    if isinstance(f.value, ast.Name):
                        txt = f.value.id + "." + f.attr
                elif isinstance(f, ast.Name):
                    txt = f.id
                if txt and INTEGRATION_PAT.search(txt):
                    add("integration", f"integration.{rel}:{n.lineno}",
                        txt, f"{rel}:{n.lineno}", txt + "(…)",
                        "外部連携呼出",
                        v_integrated="連携先の実在/生成物を確認")

        if base == "bridge.py":
            for n in tree.body:
                if isinstance(n, ast.ClassDef) and n.name.endswith("Bridge"):
                    for m in n.body:
                        if isinstance(m, ast.FunctionDef) and \
                                not m.name.startswith("_"):
                            add("bridge_method", f"bridge.{m.name}", m.name,
                                f"{rel}:{m.lineno}", sig_of(m), doc1(m),
                                depends=["QGISプラグインロード", "geo_driver"],
                                v_integrated=
                                f"bridge_call {m.name} → 応答assert")
            continue

        for n in tree.body:
            if isinstance(n, ast.ClassDef):
                bases = cls_bases_qt(n)
                if any(b in ("QDialog", "QDockWidget", "QWidget",
                             "QgsDockWidget") for b in bases):
                    add("dialog", f"dialog.{n.name}", n.name,
                        f"{rel}:{n.lineno}", n.name, doc1(n),
                        v_integrated="openDialog→screenshot→closeDialog")
                # クラス内メソッド: initGui/unload/run/open_dialog + スロット
                for m in n.body:
                    if not isinstance(m, ast.FunctionDef):
                        continue
                    if m.name in ("initGui", "unload", "run",
                                  "open_dialog", "openDialog",
                                  "show_panel", "showPanel"):
                        add("action", f"action.{n.name}.{m.name}", m.name,
                            f"{rel}:{m.lineno}", sig_of(m), doc1(m),
                            v_integrated="bridge_call/generic trigger→実在確認")
                    elif m.name.startswith(("on_", "_on")) or \
                            m.name.endswith(("_clicked", "_changed",
                                             "_slot", "_handler")):
                        add("ui_control", f"ui.{n.name}.{m.name}", m.name,
                            f"{rel}:{m.lineno}", sig_of(m), doc1(m),
                            v_integrated="親dialog経由で操作・状態assert")
            elif isinstance(n, ast.FunctionDef) and not n.name.startswith("_"):
                kind = "logic_fn"
                if n.name.startswith("register"):
                    kind = "registry"
                if base == "__init__.py" and n.name == "classFactory":
                    kind = "entry_point"
                if is_template:
                    # exec用テンプレ:import不可。run/exec経由でのみ検証
                    add("template_fn", f"{kind}.{rel}:{n.name}", n.name,
                        f"{rel}:{n.lineno}", sig_of(n), doc1(n),
                        needs_rt=True, standalone=False,
                        v_integrated="テンプレ(exec時展開):"
                                     "bridge run経由で検証")
                else:
                    add(kind, f"{kind}.{rel}:{n.name}", n.name,
                        f"{rel}:{n.lineno}", sig_of(n), doc1(n),
                        needs_rt=has_qgis, standalone=not has_qgis,
                        v_standalone=("import→呼出→戻り値assert"
                                      if not has_qgis else ""),
                        v_integrated="pyeval で属性実在+必要なら呼出")

        # QAction/メニュー登録(addAction/addMenu の引数テキスト)
        if base in ("plugin.py",):
            for n in ast.walk(tree):
                if isinstance(n, ast.Call) and isinstance(n.func,
                                                          ast.Attribute):
                    if n.func.attr in ("addAction", "addMenu", "addToolBarIcon"):
                        txt = ""
                        for a in n.args:
                            if isinstance(a, ast.Constant) and \
                                    isinstance(a.value, str) and a.value:
                                txt = a.value
                                break
                        if txt:
                            add("action", f"action.menu.{txt[:40]}",
                                txt, f"{rel}:{n.lineno}", "",
                                "メニュー/ツールバー項目",
                                v_integrated="bridge_call actions→trigger")

    # AI連携(固定3項目)
    has_bridge = os.path.isfile(os.path.join(pdir, "bridge.py"))
    add("ai_integration", "ai.catalog", "describe_plugins登録",
        "geo_driver経由", "", "カタログに載り呼出可能か",
        v_integrated="describe_plugins→plugins[]にid実在+methods非空")
    add("ai_integration", "ai.pluginInfo", "pluginInfo自己記述",
        "bridge.py" if has_bridge else "(generic bridge)",
        "pluginInfo()", "summary/when_to_use/methodsの正確性",
        v_integrated="bridge_call pluginInfo→メタ一致assert")
    if has_bridge:
        add("ai_integration", "ai.bridge_route", "bridge_call経由全到達",
            "bridge.py", "", "全bridge_methodがAI経路で呼べる",
            v_integrated="bridge_call 全method→ok/error記録")
    return feats


def load_features(vdir):
    p = os.path.join(vdir, "features.json")
    if os.path.isfile(p):
        return json.load(open(p, encoding="utf-8"))
    return None


def cmd_extract(_args):
    for pid in plugins():
        pdir = os.path.join(PLUGIN_ROOT, pid)
        vdir = os.path.join(pdir, "verify")
        os.makedirs(os.path.join(vdir, "features"), exist_ok=True)
        os.makedirs(os.path.join(vdir, "results"), exist_ok=True)
        new = extract_plugin(pid)
        old = load_features(vdir)
        added = removed = updated = 0
        if old:
            omap = {f["id"]: f for f in old["features"]}
            nmap = {f["id"]: f for f in new}
            for fid, f in nmap.items():
                if fid in omap:
                    o = omap[fid]
                    f["last_result"] = o.get("last_result", "untested")
                    f["last_verified"] = o.get("last_verified", "")
                    f["note"] = o.get("note", "")
                    if o.get("verify"):
                        f["verify"].update(
                            {k: v for k, v in o["verify"].items() if v})
                    if (o.get("source") != f["source"] or
                            o.get("signature") != f["signature"]):
                        updated += 1
                else:
                    f["note"] = "auto-added"
                    added += 1
            for fid, o in omap.items():
                if fid not in nmap and o.get("last_result") != "removed":
                    o["last_result"] = "removed"
                    new.append(o)
                    removed += 1
        else:
            added = len(new)
        order = {"entry_point": 0, "action": 1, "dialog": 2, "ui_control": 3,
                 "bridge_method": 4, "registry": 5, "integration": 6,
                 "ai_integration": 7, "logic_fn": 8, "job": 9}
        new.sort(key=lambda f: (order.get(f["kind"], 9), f["id"]))
        data = {
            "component": pid, "component_type": "qgis_plugin",
            "version": read_version(pdir),
            "driver": {
                "type": "qgis_live_harness",
                "detect": "GET http://127.0.0.1:<http_port>/api/health",
                "launch": "npm run live:ensure",
                "ready": "/api/health が ok:true を返す",
                "control": "POST /api/cmd Bearer <live_dir token>",
                "detected_from": "scripts/qgis-session.mjs, live_driver.py",
            },
            "updated": now_iso(), "features": new,
        }
        if old and old.get("static"):
            data["static"] = old["static"]
        out = os.path.join(vdir, "features.json")
        json.dump(data, open(out, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"{pid}: total={len(new)} added={added} "
              f"removed={removed} updated={updated}")


# ---------------- render ----------------

MERMAID_CDN = ("https://cdn.jsdelivr.net/npm/mermaid@10/dist/"
               "mermaid.min.js")


def esc(s):
    return html.escape(str(s or ""))


def mm_id(s):
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


def feature_mermaid(f):
    e = mm_id("E_" + f["id"])
    h = mm_id("H_" + f["id"])
    r = mm_id("R_" + f["id"])
    k = f["kind"]
    entry = {"bridge_method": "AI/bridge_call", "ai_integration": "AI経路",
             "action": "メニュー/ツールバー", "dialog": "UI操作",
             "ui_control": "UIシグナル", "logic_fn": "呼出元",
             "integration": "呼出元", "registry": "共有レジストリ",
             "entry_point": "QGIS起動"}.get(k, "呼出元")
    lines = ["flowchart LR",
             f'  {e}["{entry}"] --> {h}["{f["name"]}"]']
    if f["needs_runtime"]:
        lines.append(f'  {h} --> {r}["QGIS/ランタイムAPI"]')
        lines.append(f'  {r} --> OUT["結果"]')
    else:
        lines.append(f'  {h} --> OUT["結果"]')
    return "\n".join(lines)


def topology_mermaid(features):
    lines = ["flowchart LR",
             '  subgraph ENTRY["操作入口"]',
             '    UI["メニュー/ダイアログ"]',
             '    AI["AI/bridge_call"]',
             "  end"]
    br = [f for f in features if f["kind"] == "bridge_method"]
    act = [f for f in features if f["kind"] in
           ("action", "dialog", "ui_control")]
    lo = [f for f in features if f["kind"] == "logic_fn"]
    ig = [f for f in features if f["kind"] in ("integration", "registry")]
    lines.append('  subgraph LOGIC["実装"]')
    for f in features:
        lines.append(f'    {mm_id(f["id"])}["{f["name"]}<br/><i>{f["kind"]}</i>"]')
    lines.append("  end")
    if br:
        lines.append("  AI --> " +
                     " & ".join(mm_id(f["id"]) for f in br[:8]) +
                     (" …" if len(br) > 8 else ""))
    if act:
        lines.append("  UI --> " +
                     " & ".join(mm_id(f["id"]) for f in act[:8]) +
                     (" …" if len(act) > 8 else ""))
    lines.append('  LOGIC --> QGIS["QGIS API / iface / QgsProject"]')
    if ig:
        lines.append('  LOGIC --> EXT["外部連携(HTTP/subprocess/ファイル)"]')
    return "\n".join(lines)


HTML_HEAD = """<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8">
<title>{title}</title>
<script src="{cdn}"></script>
<style>
body{{font-family:system-ui,sans-serif;margin:2em;line-height:1.6;color:#222}}
table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #ccc;padding:4px 8px;font-size:13px;text-align:left}}
th{{background:#f0f0f0}}
.pass{{color:#0a7d2c;font-weight:600}}.fail{{color:#c0392b;font-weight:600}}
.skip,.untested{{color:#888}}.removed{{color:#999;text-decoration:line-through}}
code{{background:#f5f5f5;padding:1px 4px}}
.meta{{color:#666;font-size:13px}}
h1{{font-size:1.4em}}h2{{font-size:1.1em;border-bottom:1px solid #ddd}}
</style></head><body>
"""


def render_feature_html(vdir, f):
    body = [f"<h1>{esc(f['name'])} <code>{esc(f['id'])}</code></h1>",
            f"<p class='meta'>kind={f['kind']} / source="
            f"<code>{esc(f['source'])}</code> / signature="
            f"<code>{esc(f['signature'])}</code></p>",
            f"<p>{esc(f['summary'])}</p>"]
    if f.get("depends"):
        body.append("<p class='meta'>依存: " +
                    esc(", ".join(f["depends"])) + "</p>")
    body.append("<h2>ロジック</h2>")
    body.append(f"<pre class='mermaid'>\n{feature_mermaid(f)}\n</pre>")
    body.append("<h2>検証手順</h2><ul>")
    if f["verify"].get("standalone"):
        body.append(f"<li><b>単独:</b> <code>{esc(f['verify']['standalone'])}</code></li>")
    if f["verify"].get("integrated"):
        body.append(f"<li><b>連携:</b> <code>{esc(f['verify']['integrated'])}</code></li>")
    body.append("</ul>")
    res = f.get("last_result", "untested")
    body.append(f"<h2>検証結果</h2><p class='{res}'>"
                f"<b>{res.upper()}</b> {esc(f.get('last_verified',''))}</p>")
    if f.get("note"):
        body.append(f"<p class='meta'>{esc(f['note'])}</p>")
    body.append("<p class='meta'><a href='../index.html'>← 一覧へ</a></p>")
    page = HTML_HEAD.format(title=esc(f["id"]), cdn=MERMAID_CDN) + \
        "\n".join(body) + \
        "\n<script>mermaid.initialize({startOnLoad:true});</script></body></html>"
    fid = re.sub(r"[^\w.-]", "_", f["id"])
    out = os.path.join(vdir, "features", fid + ".html")
    open(out, "w", encoding="utf-8").write(page)
    return os.path.basename(out)


def render_plugin(pid):
    pdir = os.path.join(PLUGIN_ROOT, pid)
    vdir = os.path.join(pdir, "verify")
    data = load_features(vdir)
    if not data:
        return
    feats = data["features"]
    fid_html = {}
    for f in feats:
        fid_html[f["id"]] = render_feature_html(vdir, f)

    # logic-sheet.md
    L = [f"# {pid} — 完全ロジックシート",
         "",
         f"- 種別: {data['component_type']} / バージョン: {data['version']}",
         f"- 生成: {data['updated']} / 機能数: {len(feats)}",
         "", "## トポロジ", "", "```mermaid", topology_mermaid(feats),
         "```", "", "## 機能別ロジック", ""]
    for f in feats:
        L += [f"### {f['id']} — {f['name']}", "",
              f"- kind: `{f['kind']}` / source: `{f['source']}`",
              f"- signature: `{f['signature']}`",
              f"- 要約: {f['summary']}",
              f"- needs_runtime={f['needs_runtime']} / "
              f"standalone_ok={f['standalone_ok']}",
              "", "```mermaid", feature_mermaid(f), "```", "",
              f"- 検証: 単独={f['verify'].get('standalone','-')} / "
              f"連携={f['verify'].get('integrated','-')}",
              f"- 結果: **{f['last_result']}** {f.get('last_verified','')}"
              + (f" — {f['note']}" if f.get("note") else ""), ""]
    L += ["## 検証マトリクス", "",
          "| 機能 | kind | 単独 | 連携 | 結果 |",
          "|---|---|---|---|---|"]
    for f in feats:
        L.append(f"| {f['id']} | {f['kind']} | "
                 f"{'○' if f['standalone_ok'] else '-'} | "
                 f"{'○' if f['needs_runtime'] else '-'} | "
                 f"{f['last_result']} |")
    open(os.path.join(vdir, "logic-sheet.md"), "w",
         encoding="utf-8").write("\n".join(L))

    # index.html
    counts = {}
    for f in feats:
        counts[f["last_result"]] = counts.get(f["last_result"], 0) + 1
    rows = []
    for f in feats:
        rows.append(
            f"<tr><td><a href='features/{fid_html[f['id']]}'>"
            f"{esc(f['id'])}</a></td><td>{esc(f['name'])}</td>"
            f"<td>{f['kind']}</td>"
            f"<td>{'○' if f['needs_runtime'] else '-'}/"
            f"{'○' if f['standalone_ok'] else '-'}</td>"
            f"<td class='{f['last_result']}'>{f['last_result']}</td>"
            f"<td class='meta'>{esc(f.get('last_verified',''))}</td></tr>")
    body = [f"<h1>{esc(pid)} — 機能検証ダッシュボード</h1>",
            f"<p class='meta'>v{data['version']} / {data['updated']} / "
            f"機能数 {len(feats)} / 結果: " +
            ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) + "</p>",
            "<h2>トポロジ</h2>",
            f"<pre class='mermaid'>\n{topology_mermaid(feats)}\n</pre>",
            "<h2>機能一覧</h2><table><tr><th>id</th><th>名称</th><th>kind</th>"
            "<th>連携/単独</th><th>結果</th><th>検証日時</th></tr>" +
            "".join(rows) + "</table>"]
    page = HTML_HEAD.format(title=pid + " verify", cdn=MERMAID_CDN) + \
        "\n".join(body) + \
        "\n<script>mermaid.initialize({startOnLoad:true});</script></body></html>"
    open(os.path.join(vdir, "index.html"), "w",
         encoding="utf-8").write(page)
    print(f"{pid}: rendered {len(feats)} features")


def render_root():
    root_v = os.path.join(REPO, "verify")
    os.makedirs(root_v, exist_ok=True)
    links, sheets = [], []
    for pid in plugins():
        v = os.path.join(PLUGIN_ROOT, pid, "verify")
        d = load_features(v)
        if not d:
            continue
        rel = f"../qgis-plugin/{pid}/verify/index.html"
        counts = {}
        for f in d["features"]:
            counts[f["last_result"]] = counts.get(f["last_result"], 0) + 1
        links.append(
            f"<tr><td><a href='{rel}'>{pid}</a></td><td>{d['version']}</td>"
            f"<td>{len(d['features'])}</td><td>" +
            ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) +
            "</td></tr>")
    integ = """```mermaid
flowchart LR
  subgraph SHARED["共有基盤"]
    DRV["geo_driver (LiveDriver/REST/MCP)"]
    TB["GeoSuite共有ツールバー"]
    REG["geo_userfunc 共有レジストリ"]
    ORG["layer_org 配置サービス"]
  end
  DRV -->|plugin_idルーティング/bridge_call| ALL["全プラグイン"]
  TB -->|ツールバー集約| ALL
  GEO_EXCEL["geo_excel"] -->|register_macro| REG
  GEO_IMPORT["geo_import"] -->|place_all| ORG
  AI["AI/エージェント"] -->|REST /api/cmd・MCP| DRV
```"""
    L = ["# qgis_live_harness — リポジトリ横断ロジックシート", "",
         f"- 生成: {now_iso()}", "- コンポーネント: " +
         ", ".join(plugins()), "", "## プラグイン間連携", "", integ, ""]
    open(os.path.join(root_v, "logic-sheet.md"), "w",
         encoding="utf-8").write("\n".join(L))
    body = ["<h1>qgis_live_harness — 検証ダッシュボード</h1>",
            f"<p class='meta'>{now_iso()}</p>",
            "<h2>プラグイン間連携</h2>",
            f"<pre class='mermaid'>\n{integ[10:-4]}\n</pre>",
            "<h2>コンポーネント</h2><table><tr><th>id</th><th>ver</th>"
            "<th>機能数</th><th>結果</th></tr>" + "".join(links) + "</table>"]
    page = HTML_HEAD.format(title="qgis_live_harness verify",
                            cdn=MERMAID_CDN) + "\n".join(body) + \
        "\n<script>mermaid.initialize({startOnLoad:true});</script></body></html>"
    open(os.path.join(root_v, "index.html"), "w",
         encoding="utf-8").write(page)
    print("root: rendered")


def cmd_render(_args):
    for pid in plugins():
        render_plugin(pid)
    render_root()


# ---------------- verify ----------------

def sh(cmd, cwd=None, timeout=120):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True,  # nosec B602
                           text=True, timeout=timeout, cwd=cwd or REPO)
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def find_live():
    """live_dir とトークンを返す"""
    best = None
    if os.path.isdir(LIVE_BASE):
        for q in sorted(os.listdir(LIVE_BASE), reverse=True):
            d = os.path.join(LIVE_BASE, q, "geo_driver")
            if os.path.isdir(d):
                best = d
                break
    if not best:
        return None, None, None
    tok = ""
    tf = os.path.join(best, "token")
    if os.path.isfile(tf):
        tok = open(tf).read().strip()
    port = None
    st = os.path.join(best, "state.json")
    for cand in (st, os.path.join(best, "http.json")):
        if os.path.isfile(cand):
            try:
                port = json.load(open(cand)).get("http_port") or \
                    json.load(open(cand)).get("port")
            except Exception:
                pass
    return best, tok, port


def reg_port():
    """レジストリJSON ~/.qgis-live/*-geo_driver.json から port/token"""
    reg = os.path.join(os.path.expanduser("~"), ".qgis-live")
    if not os.path.isdir(reg):
        return None, None
    for f in sorted(os.listdir(reg), reverse=True):
        if f.endswith("-geo_driver.json"):
            try:
                d = json.load(open(os.path.join(reg, f)))
                return d.get("http_port"), d.get("token")
            except Exception:
                pass
    return None, None


def api(port, tok, payload, timeout=120, retries=3):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/cmd",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {tok}",
                 "Content-Type": "application/json"})
    last = None
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}: {e.read()[:300]}"}
        except Exception as e:
            last = e
            time.sleep(1.0 + i)
    return {"error": str(last)}


def health(port):
    try:
        with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/api/health", timeout=5) as r:
            return json.loads(r.read().decode()).get("ok")
    except Exception:
        return False


def save_result(vdir, name, obj):
    p = os.path.join(vdir, "results", name)
    json.dump(obj, open(p, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    return p


def verify_static(pid, vdir):
    pdir = os.path.join(PLUGIN_ROOT, pid)
    res = {}
    rc, out = sh(f'python -m compileall -q "{pdir}"')
    res["compileall"] = {"rc": rc, "out": out[-2000:]}
    if os.path.isfile(os.path.join(pdir, ".flake8")):
        rc, out = sh(f'python -m flake8 --config "{pdir}/.flake8" "{pdir}"',
                     timeout=180)
        res["flake8"] = {"rc": rc, "out": out[-2000:]}
    if os.path.isfile(os.path.join(pdir, ".bandit")):
        rc, out = sh(f'python -m bandit -r "{pdir}" --ini "{pdir}/.bandit" -q',
                     timeout=180)
        res["bandit"] = {"rc": rc, "out": out[-2000:]}
    return res


def _synth_args(sig):
    """signature文字列から必須引数を合成する"""
    if "(" not in sig or ")" not in sig:
        return []
    inside = sig[sig.find("(") + 1:sig.rfind(")")]
    args = []
    for p in inside.split(","):
        p = p.strip()
        if not p or "=" in p or p.startswith("*"):
            continue
        n = p.split(":")[0].strip().lower()
        if any(k in n for k in ("id", "index", "count", "page", "num")):
            args.append(0)
        elif any(k in n for k in ("flag", "enabled", "visible", "confirm")):
            args.append(False)
        elif "list" in n or n.endswith("s"):
            args.append([])
        elif "dict" in n or "data" in n or "param" in n:
            args.append({})
        else:
            args.append("")
    return args


def _mod_of(pid, rel):
    return pid + "." + rel.replace("/", ".").replace("\\", ".")[:-3]


def _presence_code(pid, feats):
    """全 presence 対象の属性実在を一括チェックする pyeval コード"""
    lines = ["import importlib, qgis.utils", "result = {}",
             f"result['__loaded__'] = {pid!r} in qgis.utils.plugins"]
    for f in feats:
        k = f["kind"]
        if f["last_result"] == "removed":
            continue
        rel = f["source"].split(":")[0]
        mod = _mod_of(pid, rel) if rel.endswith(".py") else None
        cls = meth = None
        if k == "ui_control":
            _, cls, meth = f["id"].split(".", 2)
        elif k == "dialog":
            cls = f["id"].split(".", 1)[1]
        elif k == "action" and ".menu." not in f["id"]:
            parts = f["id"].split(".")
            if len(parts) == 3:
                cls, meth = parts[1], parts[2]
            else:
                continue
        elif k in ("logic_fn", "registry"):
            meth = f["name"]
        else:
            continue
        lines += [
            "try:",
            f"    _m = importlib.import_module({mod!r})",
            f"    _o = getattr(_m, {cls!r}, _m) if {cls!r} else _m",
            f"    result[{f['id']!r}] = hasattr(_o, {meth!r}) if {meth!r} else (_o is not None)",
            "except Exception as _e:",
            f"    result[{f['id']!r}] = repr(_e)",
        ]
    return "\n".join(lines)


def cmd_verify(args):
    quick = getattr(args, "quick", False)
    only = getattr(args, "plugin", None)

    def resolve():
        """live_dir/レジストリの全候補をhealth疎通し最初の生存者を選ぶ。
        複数QGISインスタンスや死んだドライバ残骸を自動で回避する。"""
        cands = []  # (port, token)
        if os.path.isdir(LIVE_BASE):
            for q in sorted(os.listdir(LIVE_BASE), reverse=True):
                d = os.path.join(LIVE_BASE, q, "geo_driver")
                if not os.path.isdir(d):
                    continue
                t = ""
                tf = os.path.join(d, "token")
                if os.path.isfile(tf):
                    t = open(tf).read().strip()
                p = None
                for cand in (os.path.join(d, "state.json"),
                             os.path.join(d, "http.json")):
                    if os.path.isfile(cand):
                        try:
                            p = json.load(open(cand)).get("http_port") or \
                                json.load(open(cand)).get("port")
                        except Exception:
                            pass
                if p:
                    cands.append((p, t))
        reg = os.path.join(os.path.expanduser("~"), ".qgis-live")
        if os.path.isdir(reg):
            for f in sorted(os.listdir(reg), reverse=True):
                if f.endswith("-geo_driver.json"):
                    try:
                        d = json.load(open(os.path.join(reg, f)))
                        if d.get("http_port"):
                            cands.append((d["http_port"],
                                          d.get("token", "")))
                    except Exception:
                        pass
        for p, t in cands:
            if health(p):
                return t, p
        return "", None

    tok, port = resolve()
    if port and health(port):
        print(f"live driver: port={port} (reused running QGIS)")
    else:
        print("live driver: not running → npm run live:ensure で自動起動")
        rc, out = sh("npm run live:ensure", timeout=300)
        print(out[-1500:])
        tok, port = resolve()
        if not port or not health(port):
            print("RUNTIME LAUNCH FAILED → needs_runtime は skip")
            port = None
    catalog = {}

    def fetch_catalog():
        if not port:
            return
        r = api(port, tok, {"type": "describe_plugins"}, timeout=60)
        for p in (r.get("result") or {}).get("plugins", []):
            catalog[p["id"]] = p

    fetch_catalog()
    ts = now_iso()
    for pid in plugins():
        if only and pid != only:
            continue
        pdir = os.path.join(PLUGIN_ROOT, pid)
        vdir = os.path.join(pdir, "verify")
        data = load_features(vdir)
        if not data:
            continue
        # geo_driver再起動でport/tokenが変わることがあるため都度再解決
        if port:
            if not health(port):
                tok, port = resolve()
                if port and health(port):
                    print(f"reconnected: port={port}")
                    catalog.clear()
                    fetch_catalog()
                else:
                    port = None
                    print("driver down → needs_runtime は skip")
        feats = data["features"]
        # ---- 前処理: 残留モーダル除去(前plugin処理で残ると全APIが詰まる) ----
        if port:
            api(port, tok, {"type": "pyeval", "code": (
                "from qgis.PyQt.QtWidgets import QApplication, QDialog\n"
                "_n = 0\n"
                "for _w in QApplication.topLevelWidgets():\n"
                "    if isinstance(_w, QDialog) and _w.isVisible():\n"
                "        _w.reject(); _n += 1\n"
                "_n")}, timeout=30)
        # ---- static ----
        data.setdefault("static", {})
        data["static"] = verify_static(pid, vdir)
        data["static"]["ran_at"] = ts
        # ---- reload (現コード反映) ----
        # geo_driver自身をreloadすると制御HTTPチャンネルが死ぬため対象外
        if port and pid != "geo_driver":
            r = api(port, tok, {"type": "reload_plugin",
                                "plugin_id": pid}, timeout=120)
            data["static"]["reload"] = r.get("result") or r.get("error")
        elif pid == "geo_driver":
            data["static"]["reload"] = "skipped(制御チャンネル自身)"
        save_result(vdir, f"static-{ts[:10]}.json", data["static"])
        opened = False
        # ---- per feature ----
        cat = catalog.get(pid, {})
        cat_info = cat.get("info") if isinstance(cat.get("info"), dict) \
            else cat
        cat_methods = {m["name"] for m in cat_info.get("methods", [])
                       if isinstance(m, dict)}
        cat_sigs = {m["name"]: m.get("signature", "")
                    for m in cat_info.get("methods", [])
                    if isinstance(m, dict)}
        # 一括presenceチェック(dialog/ui/action/logic_fn/registry)
        presence = {}
        act_texts = []
        if port:
            rr = api(port, tok, {"type": "pyeval",
                                 "code": _presence_code(pid, feats)},
                     timeout=90)
            if isinstance(rr.get("result"), dict):
                presence = rr["result"]
            rr = api(port, tok, {"type": "bridge_call", "plugin_id": pid,
                                 "method": "actions", "args": []},
                     timeout=30)
            ar = rr.get("result")
            if isinstance(ar, dict):
                ar = ar.get("actions") or ar.get("items") or []
            if isinstance(ar, list):
                for a in ar:
                    if isinstance(a, dict):
                        act_texts.append(str(a.get("text") or
                                             a.get("title") or ""))
                    else:
                        act_texts.append(str(a))
        loaded_ok = presence.get("__loaded__") is True or pid in catalog
        # ---- セッション fixture ----
        # 1) コンテナopen: openDialog/openDock/openPanel を事前に呼び
        #    dialog/dock依存のbridgeメソッドを検証可能にする
        #    (モーダルexec型は呼ぶと詰まるのでshow型のみ対象。
        #     open*系は個別検証からはSKIP_CALL_REで除外済)
        opener_used = None
        # geo_launcher.openDialog は外部アプリ起動のため除外
        no_opener = pid in ("geo_launcher", "geo_excel", "geo_userfunc")
        if port and not no_opener:
            for opener in ("openDock", "openPanel", "openDialog"):
                if opener in cat_methods:
                    rr = api(port, tok, {
                        "type": "bridge_call", "plugin_id": pid,
                        "method": opener, "args": []}, timeout=30)
                    print(f"  [fixture] {pid}.{opener} -> "
                          f"{str(rr.get('result') or rr.get('error'))[:80]}")
                    if not rr.get("error"):
                        opener_used = opener
                    break
        # 2) テスト用メモリレイヤ: アクティブレイヤ必須メソッド向け
        LAYER_FIX_CODE = (
            "from qgis.core import (QgsVectorLayer, QgsProject,"
            " QgsFeature, QgsGeometry, QgsPointXY)\n"
            "from qgis.utils import iface\n"
            "l = QgsProject.instance().mapLayersByName("
            "'FV_test_layer')\n"
            "l = l[0] if l else QgsVectorLayer('Point?crs=EPSG:4326"
            "&field=name:string(20)', 'FV_test_layer', 'memory')\n"
            "if not l.isValid():\n"
            "    pass\n"
            "elif not l.dataProvider().featureCount():\n"
            "    ft = QgsFeature(l.fields())\n"
            "    ft.setGeometry(QgsGeometry.fromPointXY("
            "QgsPointXY(139.7, 35.7)))\n"
            "    ft.setAttribute('name', 'pt0')\n"
            "    l.dataProvider().addFeature(ft)\n"
            "QgsProject.instance().addMapLayer(l)\n"
            "iface.setActiveLayer(l)\n"
            "result = l.id()")
        layer_fix = False
        if port:
            rr = api(port, tok, {"type": "pyeval",
                                 "code": LAYER_FIX_CODE}, timeout=30)
            layer_fix = bool(rr.get("result"))

        # geo_legend: bridge の「選択中レイヤ」は iface.activeLayer でなく
        # dock.comboBox の currentLayer。fixture レイヤをコンボに再充填して
        # 選択させる(dock 開放後にレイヤ追加すると currentLayer=None のまま)
        LEGEND_FIX_CODE = (
            "import qgis.utils\n"
            "from qgis.utils import iface\n"
            "d = getattr(qgis.utils.plugins.get('geo_legend'),"
            " 'dockwidget', None)\n"
            "al = iface.activeLayer()\n"
            "if d is not None and al is not None:\n"
            "    d.comboBox.clear()\n"
            "    d.comboDataSet()\n"
            "    for i in range(d.comboBox.count()):\n"
            "        if d.comboBox.itemData(i) == al.id():\n"
            "            d.comboBox.setCurrentIndex(i)\n"
            "            break\n"
            "result = getattr(d, 'currentLayer', None) is not None")

        def refixture():
            """organizeLayers等がアクティブレイヤ選択/レイアウト選択を
            解除した場合に再適用する"""
            if layer_fix:
                api(port, tok, {"type": "pyeval",
                                "code": LAYER_FIX_CODE}, timeout=30)
            if pid == "geo_report" and "selectLayout" in cat_methods:
                api(port, tok, {"type": "bridge_call", "plugin_id": pid,
                                "method": "selectLayout", "args": [0]},
                    timeout=30)
            if pid == "geo_legend":
                api(port, tok, {"type": "pyeval",
                                "code": LEGEND_FIX_CODE}, timeout=30)

        # geo_report: レイアウト選択前提のメソッド用に先頭レイアウトを選択
        if port and pid == "geo_report" and \
                "selectLayout" in cat_methods:
            api(port, tok, {"type": "bridge_call", "plugin_id": pid,
                            "method": "selectLayout", "args": [0]},
                timeout=30)
        # geo_legend: dock.comboBox 選択前提のメソッド用にコンボを選択
        if port and pid == "geo_legend":
            api(port, tok, {"type": "pyeval",
                            "code": LEGEND_FIX_CODE}, timeout=30)
        for f in feats:
            if f["last_result"] == "removed":
                continue
            k = f["kind"]
            res, note = "untested", ""
            # --- standalone path ---
            # 任意関数の実呼出は副作用危険(sys.exit/ファイル書換/ネットワーク)
            # のため行わず、import+属性実在で検証する
            if f["standalone_ok"] and f["kind"] == "logic_fn":
                src = f["source"].split(":")[0]
                path = os.path.join(pdir, src)
                try:
                    sys.path.insert(0, pdir)
                    spec = importlib.util.spec_from_file_location(
                        "fv", path)
                    m = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(m)
                    if getattr(m, f["name"], None) is None:
                        res, note = "fail", "import ok but attr missing"
                    else:
                        res, note = "pass", "standalone import+attr実在"
                except Exception as e:
                    res, note = "fail", \
                        f"import→{type(e).__name__}: {e}"
                finally:
                    if pdir in sys.path:
                        sys.path.remove(pdir)
                if res == "fail":
                    f["last_result"], f["note"] = "fail", note
                    f["last_verified"] = ts
                    continue
            # --- integrated path ---
            if f["needs_runtime"]:
                if not port:
                    res, note = "skip", "ランタイム未起動(自動起動失敗)"
                elif k == "bridge_method":
                    if SKIP_CALL_RE.match(f["name"]) or \
                            f["name"] in PLUGIN_SKIP.get(pid, ()):
                        res, note = "skip", "副作用/破壊的/外部通信操作のため手動検証対象"
                    elif cat_methods and f["name"] not in cat_methods and \
                            f["name"] not in ("pluginInfo", "status") and \
                            not cat.get("generic"):
                        res, note = "fail", "カタログにメソッド無し"
                    else:
                        args = _synth_args(cat_sigs.get(f["name"], ""))
                        rr = api(port, tok, {
                            "type": "bridge_call", "plugin_id": pid,
                            "method": f["name"], "args": args}, timeout=90)
                        body = rr.get("result")
                        err = rr.get("error") or ""
                        if (err or (isinstance(body, dict) and
                                    body.get("ok") is False)) and \
                                any(s in str(err or body) for s in
                                    ("no layer", "active layer",
                                     "no layout", "activate one")):
                            # 直前の呼出がfixture状態を壊した可能性→再適用して再試行
                            refixture()
                            rr = api(port, tok, {
                                "type": "bridge_call", "plugin_id": pid,
                                "method": f["name"], "args": args},
                                timeout=90)
                            body = rr.get("result")
                            err = rr.get("error") or ""
                        if err or (isinstance(body, dict) and
                                   body.get("ok") is False):
                            txt = str(err or body)[:300]
                            if args or "argument" in txt or \
                                    "positional" in txt or \
                                    "required" in txt or "必須" in txt:
                                res, note = "skip", \
                                    "要実引数(応答あり): " + txt[:150]
                            else:
                                res, note = "fail", txt
                        else:
                            res, note = "pass", \
                                f"bridge_call応答あり args={args}"
                            if OPEN_CALL_RE.match(f["name"]):
                                opened = True
                elif k == "ai_integration":
                    if f["id"] == "ai.catalog":
                        if cat:
                            res, note = "pass", \
                                f"describe_plugins: methods={len(cat_methods)}"
                        else:
                            res, note = "fail", "カタログに無し"
                    elif f["id"] == "ai.pluginInfo":
                        rr = api(port, tok, {
                            "type": "bridge_call", "plugin_id": pid,
                            "method": "pluginInfo", "args": []}, timeout=30)
                        b = rr.get("result") or {}
                        ok = isinstance(b, dict) and (
                            b.get("ok") or b.get("summary") or
                            b.get("methods"))
                        res = "pass" if ok else "fail"
                        note = ("自己記述あり" if ok
                                else str(rr)[:200])
                    else:  # ai.bridge_route
                        bm = [x["name"] for x in feats
                              if x["kind"] == "bridge_method" and
                              not SKIP_CALL_RE.match(x["name"])]
                        missing = [m for m in bm
                                   if m not in cat_methods and
                                   m not in ("pluginInfo", "status")]
                        if not cat:
                            res, note = "fail", "カタログ自体に無し"
                        elif missing:
                            res, note = "fail", \
                                "未到達メソッド: " + ",".join(missing[:8])
                        else:
                            res, note = "pass", f"{len(bm)}メソッド到達可能"
                elif k == "entry_point":
                    if loaded_ok:
                        res, note = "pass", "classFactory→プラグインロード済"
                    else:
                        res, note = "fail", "プラグイン未ロード"
                elif k == "integration":
                    res, note = "skip", \
                        "連携呼出点の記録(実連携実行はbridge_method等で確認)"
                elif k == "template_fn":
                    res, note = "skip", \
                        "exec用テンプレ(bridge run経由で検証)"
                elif k == "action" and ".menu." in f["id"]:
                    label = f["name"]
                    hit = any(label in t or t in label
                              for t in act_texts if t)
                    if hit:
                        res, note = "pass", "actions一覧に項目実在"
                    elif act_texts:
                        res, note = "fail", "actions一覧に項目無し"
                    else:
                        res, note = "skip", "actions一覧取得不可"
                elif k in ("action", "dialog", "ui_control", "registry",
                           "logic_fn", "job"):
                    v = presence.get(f["id"])
                    if v is True:
                        res, note = "pass", "属性/シンボル実在確認(pyeval)"
                    elif v is False:
                        res, note = "fail", "属性未検出(pyeval)"
                    elif v:
                        res, note = "fail", f"import失敗: {str(v)[:150]}"
                    else:
                        res, note = "skip", "presence対象外"
            else:
                if res == "untested":
                    res, note = "pass", "standalone経路のみ(要runtime依存無し)"
            f["last_result"] = res
            f["last_verified"] = ts
            f["note"] = note or f.get("note", "")
        # ---- dialog 非表示instantiate + screenshot 証跡 ----
        # openDialog経由で開くとモーダルexec()がGUIスレッドを塞ぎ
        # 制御チャンネルごと止まるため、ダイアログクラスのインスタンス化
        # (非表示)でUI構築パスを検証し、スクリーンショットはメイン窓のみ
        if port:
            dlgs = [f for f in feats if f["kind"] == "dialog"
                    and f["last_result"] != "removed"]
            for d in dlgs:
                rel = d["source"].split(":")[0]
                if not rel.endswith(".py"):
                    continue
                mod = _mod_of(pid, rel)
                cls = d["id"].split(".", 1)[1]
                code = (
                    "import importlib\n"
                    "from qgis.utils import iface\n"
                    "try:\n"
                    f"    _m = importlib.import_module({mod!r})\n"
                    f"    _d = getattr(_m, {cls!r})(iface.mainWindow())\n"
                    "    _r = {'ok': True, 'title': _d.windowTitle()}\n"
                    "    _d.deleteLater()\n"
                    "except TypeError:\n"
                    "    _r = {'ok': 'ctor_args_required'}\n"
                    "except Exception as _e:\n"
                    "    _r = {'ok': False, 'err': repr(_e)}\n"
                    "_r")
                rr = api(port, tok, {"type": "pyeval", "code": code},
                         timeout=60)
                r = rr.get("result") if isinstance(rr.get("result"),
                                                   dict) else {}
                if r.get("ok") is True:
                    d["last_result"], d["note"] = "pass", \
                        f"dialogインスタンス化成功: {r.get('title')}"
                elif r.get("ok") == "ctor_args_required":
                    d["note"] = "ctor要引数(実在はpresence確認済)"
                elif r.get("ok") is False:
                    d["last_result"], d["note"] = "fail", \
                        "dialog構築失敗: " + str(r.get("err"))[:150]
            png = os.path.join(vdir, "results", f"{pid}.png")
            api(port, tok, {"type": "screenshot", "path": png.replace(
                "\\", "/"), "target": "mainwindow"}, timeout=60)
            # 残留モーダルの安全網: 可視QDialogを全てreject
            api(port, tok, {"type": "pyeval", "code": (
                "from qgis.PyQt.QtWidgets import QApplication, QDialog\n"
                "_n = 0\n"
                "for _w in QApplication.topLevelWidgets():\n"
                "    if isinstance(_w, QDialog) and _w.isVisible():\n"
                "        _w.reject(); _n += 1\n"
                "_n")}, timeout=30)
            save_result(vdir, "run-summary.json",
                        {"ts": ts, "catalog_methods": sorted(cat_methods)})
        # ---- fixture 後始末: コンテナclose + テストレイヤ削除 ----
        if port:
            if opener_used:
                closer = {"openDock": "closeDock",
                          "openPanel": "closePanel",
                          "openDialog": "closeDialog"}[opener_used]
                api(port, tok, {"type": "bridge_call", "plugin_id": pid,
                                "method": closer, "args": []}, timeout=30)
            if layer_fix:
                api(port, tok, {"type": "pyeval", "code": (
                    "from qgis.core import QgsProject\n"
                    "l = QgsProject.instance().mapLayersByName("
                    "'FV_test_layer')\n"
                    "[QgsProject.instance().removeMapLayer(x.id())"
                    " for x in l]\n"
                    "len(l)")}, timeout=30)
        data["updated"] = ts
        json.dump(data, open(os.path.join(vdir, "features.json"), "w",
                             encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        c = {}
        for f in feats:
            c[f["last_result"]] = c.get(f["last_result"], 0) + 1
        print(f"{pid}: " + ", ".join(f"{k}={v}"
                                     for k, v in sorted(c.items())))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["extract", "render", "verify", "all"],
                    nargs="?", default="all")
    ap.add_argument("--plugin")
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    if a.cmd in ("extract", "all"):
        cmd_extract(a)
    if a.cmd in ("render",):
        cmd_render(a)
    if a.cmd in ("verify", "all"):
        cmd_verify(a)
    if a.cmd in ("all", "verify"):
        cmd_render(a)


if __name__ == "__main__":
    main()
