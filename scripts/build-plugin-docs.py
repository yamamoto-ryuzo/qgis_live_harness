#!/usr/bin/env python3
"""qgis-plugin/*/ の metadata.txt + README から docs/plugins/*.html を生成する。

使い方:
    python scripts/build-plugin-docs.py

各プラグインの README_JP.md(無ければ README.md)と metadata.txt を読み、
docs/ サイト共通テンプレート(assets/style.css + assets/site.js)に流し込んで
docs/plugins/<id>.html と docs/plugins/index.html を出力する。
要: pip install mistune
"""

import html
import re
import sys
from pathlib import Path

import mistune

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = ROOT / "qgis-plugin"
OUT_DIR = ROOT / "docs" / "plugins"
REPO = "https://github.com/yamamoto-ryuzo/qgis_live_harness"
BLOB = f"{REPO}/blob/master"
RAW = "https://raw.githubusercontent.com/yamamoto-ryuzo/qgis_live_harness/master"

# 表示順 = GeoSuite のワークフロー順 + 基盤/連携
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

# メタデータに無い補足情報(役割・upstream・関連ページ)
EXTRA = {
    "geo_driver": {
        "role": "Harness 中核ドライバ(制御ハブ)",
        "origin": "Harness 生まれ",
        "site_links": [
            ("../driver.html", "QGIS Live Driver(詳細設計)"),
            ("../security.html", "セキュリティ・脅威モデル"),
        ],
    },
    "geo_userfunc": {
        "role": "GeoSuite 前段 — ユーザー定義コード整備",
        "origin": "Harness 生まれ(初期同梱: QGIS_user_function)",
        "geosuite": True,
        "site_links": [],
    },
    "geo_import": {
        "role": "GeoSuite — データ取り込み(CKAN/ローカル)",
        "origin": "upstream: qgis-data-catalog-integration",
        "upstream": "https://github.com/yamamoto-ryuzo/qgis-data-catalog-integration",
        "geosuite": True,
        "site_links": [],
    },
    "geo_search": {
        "role": "GeoSuite — 地図内検索",
        "origin": "upstream: GEO-search-plugin",
        "upstream": "https://github.com/yamamoto-ryuzo/GEO-search-plugin",
        "geosuite": True,
        "site_links": [
            (f"{BLOB}/qgis-plugin/geo_search/SEARCH_JP.md", "SEARCH_JP.md(検索仕様)"),
            (f"{BLOB}/qgis-plugin/geo_search/THEMES_JP.md", "THEMES_JP.md(テーマ)"),
        ],
    },
    "geo_webview": {
        "role": "GeoSuite — スタイル込 Web 共有(.kasc)",
        "origin": "upstream: geo_webview",
        "upstream": "https://github.com/yamamoto-ryuzo/geo_webview",
        "geosuite": True,
        "site_links": [
            ("../geo_webview/", "geo_webview ドキュメントサイト"),
            ("../geo_webview.html", "外部サービス・クライアント連携"),
            (f"{BLOB}/qgis-plugin/geo_webview/SPEC_JP.md", "SPEC_JP.md(.kasc仕様/API)"),
            (f"{BLOB}/qgis-plugin/geo_webview/INTEGRATION_JP.md", "INTEGRATION_JP.md(連携方針)"),
        ],
    },
    "geo_report": {
        "role": "GeoSuite — 報告書(PNG/PDF)",
        "origin": "upstream: qgis-layoutitem-selector",
        "upstream": "https://github.com/yamamoto-ryuzo/qgis-layoutitem-selector",
        "geosuite": True,
        "site_links": [],
    },
    "geo_excel": {
        "role": "GeoSuite — 報告書(Excel 帳票)",
        "origin": "upstream: QGIS-exportExcel",
        "upstream": "https://github.com/yamamoto-ryuzo/QGIS-exportExcel",
        "geosuite": True,
        "site_links": [],
    },
    "geo_legend": {
        "role": "凡例ドック(将来 GeoReport へ統合予定)",
        "origin": "upstream: QGIS-legendView",
        "upstream": "https://github.com/yamamoto-ryuzo/QGIS-legendView",
        "site_links": [],
    },
    "geo_launcher": {
        "role": "kasugai_qgis ランチャー連携",
        "origin": "Harness 生まれ(連携先: kasugai_qgis)",
        "upstream": "https://github.com/yamamoto-ryuzo/kasugai_qgis",
        "site_links": [],
    },
}

IMG_EXT = re.compile(r"\.(png|jpe?g|gif|svg|webp|mp4|webm)(\?|#|$)", re.I)


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


def localize(html_text: str, plugin_id: str) -> str:
    """README 由来 HTML の相対リンク/画像を GitHub 絶対 URL へ書き換える。"""
    base = f"qgis-plugin/{plugin_id}"

    def fix_url(url: str, is_img: bool) -> str:
        url = url.strip()
        if re.match(r"^(https?://|mailto:|#|data:)", url):
            return url
        url = url.lstrip("./")
        if is_img or IMG_EXT.search(url):
            return f"{RAW}/{base}/{url}"
        return f"{BLOB}/{base}/{url}"

    html_text = re.sub(
        r'href="([^"]+)"',
        lambda m: f'href="{fix_url(m.group(1), False)}"',
        html_text,
    )
    html_text = re.sub(
        r'src="([^"]+)"',
        lambda m: f'src="{fix_url(m.group(1), True)}"',
        html_text,
    )
    # 装飾用の giphy 動画ブロックは docs では落とす
    html_text = re.sub(
        r'<p align="center">.*?giphy.*?</p>', "", html_text, flags=re.S
    )
    return html_text


def readme_html(plugin_id: str) -> str:
    pdir = PLUGIN_DIR / plugin_id
    src = pdir / "README_JP.md"
    if not src.exists():
        src = pdir / "README.md"
    if not src.exists():
        return "<p>(README なし)</p>"
    md = mistune.create_markdown(
        plugins=["strikethrough", "footnotes", "table", "task_lists", "url"],
        escape=False,
    )
    text = src.read_text(encoding="utf-8")
    # 先頭の H1 はページヘッダと重複するので除去
    text = re.sub(r"^#[^\n]*\n", "", text, count=1)
    return localize(md(text), plugin_id)


def sidebar(active: str, prefix: str = "") -> str:
    """共通サイドバー。active はファイル名 or 'plugins/<id>.html'。"""
    top = [
        ("はじめに", [
            ("index.html", "概要"),
            ("usage.html", "使い方・セットアップ"),
            ("security.html", "セキュリティ"),
        ]),
        ("コンポーネント", [
            ("driver.html", "QGIS Live Driver"),
            ("harness.html", "QGIS Live Harness"),
        ]),
        ("ガイド", [
            ("distribution.html", "プラグイン配布"),
            ("internals.html", "Harnessのプラグイン化"),
            ("plugins.html", "プラグイン一覧"),
            ("geosuite.html", "GeoSuite"),
            ("geo_webview.html", "geo_webview"),
        ]),
        ("プラグイン", [("plugins/index.html", "すべてのプラグイン")]
         + [(f"plugins/{pid}.html", pid) for pid in ORDER]),
    ]
    out = []
    for group, links in top:
        out.append(f'      <div class="group">{group}</div>')
        for href, label in links:
            cls = "navlink active" if href == active else "navlink"
            out.append(f'      <a class="{cls}" href="{prefix}{href}">{html.escape(label)}</a>')
    out.append('      <div class="group">リンク</div>')
    out.append(f'      <a class="navlink ext" href="{REPO}">GitHub リポジトリ</a>')
    body = "\n".join(out)
    return f"""  <nav class="sidebar">
    <div class="site"><span class="logo">Q</span>QGIS Live Harness</div>
    <div class="links">
{body}
    </div>
  </nav>"""


def page(title: str, description: str, active: str, body: str, prefix: str = "") -> str:
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} | QGIS Live Harness</title>
<meta name="description" content="{html.escape(description)}">
<link rel="stylesheet" href="{prefix}assets/style.css">
</head>
<body>
{sidebar(active, prefix)}
  <div class="content">
  <main>
{body}
  </main>
  <aside class="toc"></aside>
  </div>
<script type="module" src="{prefix}assets/site.js"></script>
</body>
</html>
"""


def pager(prev_item, next_item) -> str:
    parts = ['<nav class="pager">']
    if prev_item:
        href, label = prev_item
        parts.append(
            f'  <a href="{href}"><span class="dir">前へ</span>'
            f'<span class="title">{html.escape(label)}</span></a>'
        )
    if next_item:
        href, label = next_item
        parts.append(
            f'  <a class="next" href="{href}"><span class="dir">次へ</span>'
            f'<span class="title">{html.escape(label)}</span></a>'
        )
    parts.append("</nav>")
    return "\n".join(parts)


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


def plugin_page(plugin_id: str, meta: dict, idx: int) -> str:
    extra = EXTRA.get(plugin_id, {})
    desc = short_description(meta)
    version = meta.get("version", "?")
    minqgis = meta.get("qgisMinimumVersion", "?")
    license_ = meta.get("license", "GPL-3.0")

    rows = [
        ("プラグイン ID", f"<code>{plugin_id}</code>"),
        ("バージョン", html.escape(version)),
        ("最小 QGIS", html.escape(minqgis)),
        ("ライセンス", html.escape(license_)),
        ("役割", html.escape(extra.get("role", "—"))),
        ("出自", html.escape(extra.get("origin", "—"))),
    ]
    if extra.get("upstream"):
        rows.append(("関連リポジトリ", f'<a href="{extra["upstream"]}">{extra["upstream"].rsplit("/", 1)[-1]}</a>'))
    rows.append((
        "ソース",
        f'<a href="{BLOB}/qgis-plugin/{plugin_id}/">qgis-plugin/{plugin_id}/</a> · '
        f'<a href="{BLOB}/qgis-plugin/{plugin_id}/CHANGELOG.md">CHANGELOG</a>',
    ))
    info = "\n".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows)

    related = []
    for href, label in extra.get("site_links", []):
        related.append((href, label))
    if extra.get("geosuite"):
        related.insert(0, ("../geosuite.html", "GeoSuite(スイート概要)"))
    related.extend([
        ("index.html", "プラグイン別ドキュメント一覧"),
        ("../plugins.html", "プラグイン一覧(Harness 概要)"),
    ])
    related_html = "\n".join(
        f'<li><a class="card" href="{h}"><b>{html.escape(t)}</b></a></li>'
        for h, t in related
    )

    prev_item = (
        (f"{ORDER[idx - 1]}.html", ORDER[idx - 1]) if idx > 0
        else ("index.html", "すべてのプラグイン")
    )
    next_item = (
        (f"{ORDER[idx + 1]}.html", ORDER[idx + 1]) if idx < len(ORDER) - 1
        else ("index.html", "すべてのプラグイン")
    )

    body = f"""<header class="page-header">
<p class="eyebrow">Plugin</p>
<h1><code>{plugin_id}</code></h1>
<p class="lead">{html.escape(desc)}</p>
</header>
<table>
<tbody>
{info}
</tbody>
</table>
{readme_html(plugin_id)}
<h2>関連ドキュメント</h2>
<ul class="cards">
{related_html}
</ul>
{pager(prev_item, next_item)}"""
    return page(f"{plugin_id} プラグイン", desc, f"plugins/{plugin_id}.html",
               body, prefix="../")


def index_page(metas: dict) -> str:
    cards = []
    for pid in ORDER:
        meta = metas[pid]
        extra = EXTRA.get(pid, {})
        desc = short_description(meta)
        ver = meta.get("version", "")
        role = extra.get("role", "")
        cards.append(
            f'<li><a class="card" href="{pid}.html"><b>{pid}</b>'
            f'<span>{html.escape(desc)}<br>'
            f'<small>v{html.escape(ver)} — {html.escape(role)}</small></span></a></li>'
        )
    body = f"""<header class="page-header">
<p class="eyebrow">Plugins</p>
<h1>プラグイン別ドキュメント</h1>
<p class="lead">qgis-plugin/ 配下の全プラグインのドキュメント。各ページは
プラグインの README・metadata.txt から生成しています。</p>
</header>
<blockquote>
<p>このページ群は <code>python scripts/build-plugin-docs.py</code> で
<code>qgis-plugin/&lt;id&gt;/README_JP.md</code>(無ければ <code>README.md</code>)
から自動生成されます。元ファイル更新後に再実行してください。</p>
</blockquote>
<ul class="cards">
{chr(10).join(cards)}
</ul>
<h2>スイートとしての位置づけ</h2>
<p><code>geo_userfunc</code> → <code>geo_import</code> → <code>geo_search</code> →
<code>geo_webview</code> → <code>geo_report</code> / <code>geo_excel</code> は
<a href="../geosuite.html">GeoSuite</a> のワークフロー(取り込み → 検索 → Web 共有 →
帳票出力)を構成します。<code>geo_driver</code> は全プラグインを遠隔操作する
制御ハブ(<a href="../driver.html">QGIS Live Driver</a>)で、各プラグインの
<code>bridge</code> API はこれ経由で AI から呼び出せます。</p>
{pager(("../plugins.html", "プラグイン一覧(Harness 概要)"), (f"{ORDER[0]}.html", ORDER[0]))}"""
    return page("プラグイン別ドキュメント", "qgis-plugin/ 配下の全プラグインのドキュメント一覧",
                "plugins/index.html", body, prefix="../")


def main() -> int:
    metas = {}
    for pid in ORDER:
        mpath = PLUGIN_DIR / pid / "metadata.txt"
        if not mpath.exists():
            print(f"skip {pid}: metadata.txt なし", file=sys.stderr)
            continue
        metas[pid] = parse_metadata(mpath)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for i, pid in enumerate(ORDER):
        if pid not in metas:
            continue
        (OUT_DIR / f"{pid}.html").write_text(
            plugin_page(pid, metas[pid], i), encoding="utf-8"
        )
        print(f"docs/plugins/{pid}.html")
    (OUT_DIR / "index.html").write_text(index_page(metas), encoding="utf-8")
    print("docs/plugins/index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
