#!/usr/bin/env python3
"""qgis-plugin/<id>/docs/ の共有アセットを整備する。

使い方:
    python scripts/build-plugin-docs.py   (npm run docs)

プラグイン同梱ドキュメントの正本は qgis-plugin/<id>/docs/(日本語 HTML。
GitHub 上で直接参照する運用。qgis_live_harness/docs/ 側には
プラグイン文書を置かない)。このスクリプトが行うのは:

1. docs/index.html が無いプラグインに目次ページを seed(既存は触らない)
2. scripts/plugin_docs/style.css(KASUGAI Canvas 準拠)を各 docs/ へ同期
3. docs/ 内 HTML から nav.js(左サイドバー)を自動生成して配置
"""

import html
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = ROOT / "qgis-plugin"
REPO = "https://github.com/yamamoto-ryuzo/qgis_live_harness"
TREE = f"{REPO}/tree/master"
BLOB = f"{REPO}/blob/master"

# 整備対象プラグイン(metadata.txt 必須)
ORDER = [
    "geo_driver",
    "geo_userfunc",
    "geo_import",
    "geo_search",
    "geo_webview",
    "geo_report",
    "geo_excel",
    "geo_legend",
    "geo_launcher",
]

DOCS_ASSETS = Path(__file__).resolve().parent / "plugin_docs"

# qgis-plugin/<id>/docs/nav.js のページ並び順(未記載は末尾にアルファベット順)
DOCS_ORDER = {
    "geo_webview": [
        "index.html", "spec.html", "getting-started.html",
        "architecture.html", "features.html", "engines.html",
        "technical.html", "integration.html", "license.html",
    ],
}

# ナビを KASUGAI Canvas 式(nav-section セクション構成)にするプラグインの
# 定義。セクションは {"section": 見出し, "href": 見出しリンク(任意),
# "pages": [ファイル名…] または "spec_tabs"/"use_tabs"}。
# "spec_tabs" = spec.html のタブ別節(h2 が "N. "、N=1-7)を項目として
# 切り出す(仕様書の子リンクからは除く)。
# "use_tabs" = docs/use/*.html をファイル名順に項目化し、各項目の
# 子リンクを「使い方」節の h3(機能名)として列挙する
# (KASUGAI Canvas docs/use/ 準拠)。"extra" でタブ項目へ
# 資料ページを子リンクとして追加できる(資料セクションからの移管)。
NAV_SECTIONS = {
    "geo_webview": [
        {"section": "概要", "href": "index.html",
         "pages": ["index.html", "spec.html", "getting-started.html",
                    "architecture.html"]},
        {"section": "タブ別機能", "pages": "use_tabs",
         "extra": {
             "1-1-Webタブ.html": ["features.html", "engines.html"],
             "1-6-Otherタブ.html": ["integration.html"],
             "1-7-パネル下部.html": ["technical.html"],
         }},
        {"section": "資料", "pages": ["license.html"]},
    ],
}

# ナビ上部(nav-demos)へ追加するプラグイン別リンク
NAV_DEMOS = {
    "geo_webview": [
        ("https://yamamoto-ryuzo.github.io/kasugai_canvas/web/cesium/",
         "▶ サンプルサイト(KASUGAI Canvas)"),
    ],
}


def parse_metadata(path: Path) -> dict:
    """metadata.txt を key=value に分解(複数行はインデント継続)。"""
    meta = {}
    key = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_\[\]]+?)\s*=\s*(.*)$", line)
        if m and not line.startswith((" ", "\t")):
            key = m.group(1)
            meta[key] = m.group(2).strip()
        elif key and line.startswith((" ", "\t")):
            meta[key] += "\n" + line.strip()
    return meta


def short_description(meta: dict) -> str:
    desc = meta.get("description[ja]") or meta.get("description") or ""
    # literal \n エスケープを実改行に戻し、空セグメントを捨てる
    parts = [p.strip() for p in desc.replace("\\n", "\n").split("\n") if p.strip()]
    jp = [p for p in parts if re.search(r"[぀-ヿ一-鿿]", p)]
    desc = " ".join(jp) if jp else (parts[0] if parts else "")
    # "EN / JP" 併記なら日本語側だけ残す
    if " / " in desc:
        segs = [s.strip() for s in desc.split(" / ")]
        jsegs = [s for s in segs if re.search(r"[぀-ヿ一-鿿]", s)]
        if jsegs:
            desc = " / ".join(jsegs)
    return desc


def _page_title(path: Path) -> str:
    m = re.search(r"<title>(.*?)</title>",
                  path.read_text(encoding="utf-8"), re.S)
    title = re.sub(r"\s*\|.*$", "", m.group(1)).strip() if m else path.stem
    return re.sub(r"\s+", " ", title)


def _page_children(path: Path) -> list:
    """ページ内の h2 id をナビの子リンクとして抽出する。"""
    out = []
    for m in re.finditer(
            r'<h2\s+id="([^"]+)"[^>]*>(.*?)</h2>',
            path.read_text(encoding="utf-8"), re.S):
        text = re.sub(r"<[^>]+>", "", m.group(2))
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            out.append((f"{path.name}#{m.group(1)}", text))
    return out


def write_docs_nav(plugin_id: str, ddir: Path) -> None:
    """qgis-plugin/<id>/docs/ 用の nav.js を生成する(常に再生成)。

    KASUGAI Canvas ドキュメント(docs/nav.js)と同型の左サイドバー
    (nav-section セクション + nav-group-label + 項目 + 子リンク)を
    #site-nav として描画する。ページ一覧・h2 アンカーは docs/ 内の
    HTML から自動収集する。
    """
    order = {name: i for i, name in enumerate(DOCS_ORDER.get(plugin_id, []))}
    htmls = sorted(
        ddir.glob("*.html"),
        key=lambda f: (order.get(f.name, 999), f.name),
    )
    page_map = {}
    for f in htmls:
        if f.name == "index.html":
            continue
        page_map[f.name] = (f.name, _page_title(f), _page_children(f))

    # spec.html のタブ別節(h2 が "N. "、N=1-7)を切り出し、
    # spec.html の子リンクからは除く("use_tabs" の N-2 子リンクで使う)
    tab_items = []
    if any(s["pages"] in ("spec_tabs", "use_tabs")
           for s in NAV_SECTIONS.get(plugin_id, [])) \
            and "spec.html" in page_map:
        name, title, children = page_map["spec.html"]
        keep = []
        for href, text in children:
            if re.match(r"^[1-7]\.\s", text):
                tab_items.append((href, text))
            else:
                keep.append((href, text))
        page_map["spec.html"] = (name, title, keep)

    # "use_tabs": docs/use/*.html をファイル名順に項目化。
    # 子リンクは「使い方」節内の h3(機能ごとの見出し)を
    # "N-M <機能名>" として列挙する
    use_items = []
    if any(s["pages"] == "use_tabs"
           for s in NAV_SECTIONS.get(plugin_id, [])):
        udir = ddir / "use"
        if udir.is_dir():
            for i, f in enumerate(sorted(udir.glob("*.html"))):
                rel = f"use/{f.name}"
                src = f.read_text(encoding="utf-8")
                # 「使い方」h2〜次の h2 までの範囲の h3 を拾う
                seg = re.split(r'<h2\s+id="使い方"', src, maxsplit=1)
                seg = re.split(r'<h2\s', seg[-1], maxsplit=1)[0] \
                    if len(seg) > 1 else ""
                children = []
                for j, m in enumerate(re.finditer(
                        r'<h3\s+id="([^"]+)"[^>]*>(.*?)</h3>',
                        seg, re.S)):
                    text = re.sub(r"<[^>]+>", "", m.group(2))
                    text = re.sub(r"\s+", " ", text).strip()
                    if text:
                        children.append(
                            (f"{rel}#{m.group(1)}",
                             f"{i + 1}-{j + 1} {text}"))
                use_items.append((rel, _page_title(f), children))

    groups = []
    for sec in NAV_SECTIONS.get(plugin_id, []):
        if sec["pages"] == "spec_tabs":
            items = [(h, t, []) for h, t in tab_items]
        elif sec["pages"] == "use_tabs":
            # "extra": タブ項目へ資料ページを子リンクとして追加する
            items = []
            for rel, title, children in use_items:
                fname = rel.rsplit("/", 1)[-1]
                for extra in sec.get("extra", {}).get(fname, []):
                    if extra in page_map:
                        children = children + [page_map[extra][:2]]
                items.append((rel, title, children))
        else:
            items = []
            for n in sec["pages"]:
                if n == "index.html":
                    if (ddir / "index.html").exists():
                        items.append(("index.html", "概要", []))
                elif n in page_map:
                    items.append(page_map[n])
        groups.append((sec["section"], sec.get("href"), items))
    if not groups:
        pages = list(page_map.values())
        if (ddir / "index.html").exists():
            pages.insert(0, ("index.html", "概要", []))
        groups = [(None, None, pages)]

    demos = [
        ("https://yamamoto-ryuzo.github.io/qgis_live_harness/"
         "plugins.html", "プラグイン一覧(サイト)"),
        (f"{TREE}/qgis-plugin/{plugin_id}", "GitHub(プラグイン)"),
    ] + NAV_DEMOS.get(plugin_id, [])
    ext = " target=\"_blank\" rel=\"noopener noreferrer\""

    def js_str(s: str) -> str:
        return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"

    lines = ["// 自動生成: scripts/build-plugin-docs.py(再実行で上書きされます)",
             "// KASUGAI Canvas docs/nav.js と同型(セクション + 項目 + 子リンク)",
             "(function () {",
             f"  var TITLE = {js_str(plugin_id)};",
             "  var GROUPS = ["]
    for label, shref, gpages in groups:
        g = "    { section: " + (js_str(label) if label else "null")
        if shref:
            g += f", sectionHref: {js_str(shref)}"
        g += ", items: ["
        lines.append(g)
        for href, title, children in gpages:
            lines.append(
                f"      {{ href: {js_str(href)}, text: {js_str(title)},")
            if children:
                lines.append("        children: [")
                for chref, ctext in children:
                    lines.append(
                        f"          {{ href: {js_str(chref)}, text: {js_str(ctext)} }},")
                lines.append("        ]")
                lines.append("      },")
            else:
                lines[-1] += " },"
        lines.append("    ]},")
    lines.append("  ];")
    lines.append("  var DEMOS = [")
    for dhref, dtext in demos:
        lines.append(
            f"    {{ href: {js_str(dhref)}, text: {js_str(dtext)} }},")
    lines += [
        "  ];",
        "  var base = new URL('.', document.currentScript.src).pathname;",
        "  function norm(p) {",
        "    p = p.replace(/#.*$/, '').replace(/index\\.html$/, '')",
        "      .replace(/\\/$/, '');",
        "    try { p = decodeURIComponent(p); } catch (e) {}",
        "    return p;",
        "  }",
        "  var current = norm(location.pathname);",
        "  function isActive(href) {",
        "    return href.indexOf('#') < 0 && norm(base + href) === current;",
        "  }",
        "  var nav = document.createElement('aside');",
        "  nav.id = 'site-nav';",
        "  var h = '<div class=\"nav-title\"><a href=\"' + base"
        " + 'index.html\">' +"
        " TITLE + '</a>"
        "<span class=\"nav-version\" data-plugin-version hidden></span></div>';",
        "  h += '<div class=\"nav-demos\">';",
        "  for (var i = 0; i < DEMOS.length; i++) {",
        f"    h += '<a class=\"nav-demo\" href=\"' + DEMOS[i].href + '\"{ext}>'"
        " + DEMOS[i].text + '</a>';",
        "  }",
        "  h += '</div>';",
        "  for (var g = 0; g < GROUPS.length; g++) {",
        "    var grp = GROUPS[g];",
        "    if (grp.section) h += grp.sectionHref",
        "      ? '<div class=\"nav-section\"><a href=\"' + base + grp.sectionHref"
        " + '\">' + grp.section + '</a></div>'",
        "      : '<div class=\"nav-section\">' + grp.section + '</div>';",
        "    h += '<div class=\"nav-group\"><ul>';",
        "    for (var i = 0; i < grp.items.length; i++) {",
        "      var p = grp.items[i];",
        "      h += '<li><a href=\"' + base + p.href + '\"' +",
        "        (isActive(p.href) ? ' class=\"active\"' : '') + '>'"
        " + p.text + '</a>';",
        "      if (p.children) {",
        "        h += '<ul class=\"nav-sub\">';",
        "        for (var j = 0; j < p.children.length; j++) {",
        "          var c = p.children[j];",
        "          h += '<li><a href=\"' + base + c.href + '\"' +",
        "            (isActive(c.href) ? ' class=\"active\"' : '') + '>'",
        " + c.text + '</a></li>';",
        "        }",
        "        h += '</ul>';",
        "      }",
        "      h += '</li>';",
        "    }",
        "    h += '</ul></div>';",
        "  }",
        "  nav.innerHTML = h;",
        "  document.body.prepend(nav);",
        "  document.body.classList.add('has-nav');",
        "  var SCROLL_KEY = 'plugin-docs-nav-scroll';",
        "  try {",
        "    var st = sessionStorage.getItem(SCROLL_KEY);",
        "    if (st) nav.scrollTop = parseInt(st, 10) || 0;",
        "    var st_ = null;",
        "    nav.addEventListener('scroll', function () {",
        "      if (st_) clearTimeout(st_);",
        "      st_ = setTimeout(function () {",
        "        try { sessionStorage.setItem(SCROLL_KEY,",
        " String(nav.scrollTop)); } catch (e) {}",
        "      }, 80);",
        "    });",
        "  } catch (e) {}",
        "  var btn = document.createElement('button');",
        "  btn.className = 'nav-toggle'; btn.type = 'button';",
        "  btn.setAttribute('aria-label', 'メニュー'); btn.textContent = '☰';",
        "  btn.addEventListener('click', function () {",
        "    document.body.classList.toggle('nav-open'); });",
        "  document.body.prepend(btn);",
        "  nav.addEventListener('click', function (e) {",
        "    if (e.target.closest('a')) document.body.classList.remove('nav-open');",
        "  });",
        "})();",
    ]
    (ddir / "nav.js").write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_docs_index(plugin_id: str, meta: dict) -> None:
    """qgis-plugin/<id>/docs/index.html が無ければ目次ページを生成する。

    生成は未存在時のみ(一度作ればプラグイン側で自由編集できる正本)。
    KASUGAI Canvas スタイル(style.css + nav.js)に準拠。
    """
    ddir = PLUGIN_DIR / plugin_id / "docs"
    index = ddir / "index.html"
    if index.exists():
        return
    ddir.mkdir(parents=True, exist_ok=True)
    desc = short_description(meta) or plugin_id
    files = sorted(
        p.name for p in ddir.glob("*.html")
        if p.name != "index.html"
    )
    if files:
        doc_links = "\n".join(
            f'  <li><a href="{html.escape(f)}">'
            f'{html.escape(_page_title(ddir / f))}</a>'
            f' <small>({html.escape(f)})</small></li>'
            for f in files
        )
        doc_section = f"<h2>ドキュメント</h2>\n<ul>\n{doc_links}\n</ul>"
    else:
        doc_section = (
            "<p>このプラグインの詳細文書はありません。"
            "README・CHANGELOG(プラグイン直下)を参照してください。</p>"
        )
    body = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{plugin_id} ドキュメント | QGIS Live Harness</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="stylesheet" href="style.css">
<script src="nav.js" defer></script>
</head>
<body>
<div class="container">
<header>
<h1>{plugin_id}</h1>
<p>{html.escape(desc)}</p>
</header>
<main>
{doc_section}
<h2>関連リンク</h2>
<ul>
  <li><a href="https://yamamoto-ryuzo.github.io/qgis_live_harness/plugins.html">プラグイン一覧(サイト)</a></li>
  <li><a href="{BLOB}/qgis-plugin/{plugin_id}/README.md">README(GitHub)</a></li>
  <li><a href="{BLOB}/qgis-plugin/{plugin_id}/CHANGELOG.md">CHANGELOG(GitHub)</a></li>
</ul>
</main>
</div>
</body>
</html>
"""
    index.write_text(body, encoding="utf-8")
    print(f"qgis-plugin/{plugin_id}/docs/index.html (seeded)")


def sync_docs_assets() -> None:
    """各プラグイン docs/ へ共通アセット(style.css/nav.js)を配置する。

    style.css は scripts/plugin_docs/style.css(KASUGAI Canvas 準拠)を
    常にコピーして統一。nav.js はページ構成から自動生成する。
    """
    src_css = DOCS_ASSETS / "style.css"
    for pdir in sorted(PLUGIN_DIR.iterdir()):
        ddir = pdir / "docs"
        if not ddir.is_dir():
            continue
        shutil.copyfile(src_css, ddir / "style.css")
        write_docs_nav(pdir.name, ddir)


def main() -> int:
    for pid in ORDER:
        mpath = PLUGIN_DIR / pid / "metadata.txt"
        if not mpath.exists():
            print(f"skip {pid}: metadata.txt なし", file=sys.stderr)
            continue
        ensure_docs_index(pid, parse_metadata(mpath))
    sync_docs_assets()
    return 0


if __name__ == "__main__":
    sys.exit(main())
