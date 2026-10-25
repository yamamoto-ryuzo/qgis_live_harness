# -*- coding: utf-8 -*-
"""KASUGAI Canvas 連携エクスポート。

QGIS プロジェクトの表示中ベクターレイヤーを GeoJSON + QGISスタイル(.qml)
として出力し、KASUGAI Canvas プロジェクト形式(.kasc + DATA/)を生成する。

KASUGAI Canvas は ``geojson: タイトル | DATA/x.geojson | on | style=DATA/x.qml``
形式の .kasc 行を読み、.qml の <renderer-v2> を Cesium 描画へコンパイルする。
ネイティブ参照できるソースは ``gpkg:``/``geojson:``/``geoparquet:``/
``flatgeobuf:``、CSV/TSV・フィルタ付きソースは ``duckdb:``、
3D Tiles レイヤは ``3dtiles:``、XYZ タイルは ``xyz:``/``base:`` 行になる。
ローカルサーバー版(port 8510)が起動していれば
``POST /api/projects/register {path: <kasc>}`` で外部プロジェクトとして
登録でき、そのまま ``?project=<id>`` で開ける(登録フォルダの DATA/ が
そのまま配信される)。``POST /api/command`` の switchProject で
起動中の画面を切り替えることもできる。
起動エンジンは ``/cesium/`` ``/maplibre/`` ``/openlayers/`` ``/leaflet/``
の実パスで直接指定できる(``?engine=`` リダイレクトへの依存を避ける)。

このモジュールは PyQGIS 環境でのみ使用する(ユニットテスト不可)。
ネットワーク呼び出しは全て短いタイムアウト付きのベストエフォート。
"""

import json
import os
import re
import shutil
import subprocess  # nosec B404  # kasugai_canvas.exe の連携起動用
import time
import urllib.error
import urllib.parse
import urllib.request

# KASUGAI Canvas ローカルサーバーの既定ポート(run.py _get_port と同じ)
DEFAULT_KASUGAI_PORT = 8510
SETTINGS_KEY_OUTPUT = 'kasugai_output_path'
SETTINGS_KEY_PORT = 'kasugai_port'

# KASUGAI Canvas の起動エンジン(web/index.html の engine パラメータと同じ)
VALID_ENGINES = ('cesium', 'maplibre', 'openlayers', 'leaflet')
DEFAULT_ENGINE = 'cesium'

KASUGAI_EXE_NAME = 'kasugai_canvas.exe'
_KASUGAI_UNINSTALL_KEY = (
    r'Software\Microsoft\Windows\CurrentVersion\Uninstall\KASUGAI Canvas')

# .kasc と同じ場所に出力するエンジン起動HTML(サーバレス配布用)。
# 各HTMLは ?kasc=<.kascの絶対URL> 付きでエンジンへ転送するだけの
# 自己完結ページ。エンジン本体(web/ の中身)は ./ ../ ../../ / の順に
# 自動探索し、見つからなければHTML内の CANVAS_BASE を編集してもらう
_LAUNCHER_ENGINES = ('cesium', 'maplibre', 'openlayers', 'leaflet')

_ENGINE_LAUNCHER_HTML = '''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>KASUGAI Canvas — __ENGINE__</title>
<style>
  body { font-family: system-ui,"Segoe UI","Yu Gothic",sans-serif; margin: 28px; line-height: 1.65; color: #1d2b35; }
  code { background: #eef2f5; padding: 1px 5px; border-radius: 4px; }
  #tried a { color: #2c5ea8; }
  .note { color: #52636d; font-size: 0.9em; }
</style>
</head>
<body>
<h1 style="font-size:1.15em">KASUGAI Canvas — __ENGINE__</h1>
<p id="status">エンジンを探しています…</p>
<div id="notfound" hidden>
  <p>エンジン（<code>web/</code> の中身）が見つかりませんでした。<br />
  このフォルダ（<code>__KASC__</code>・<code>DATA/</code>）とエンジンを同じ Web サーバーへ
  アップしてください。確認した場所:</p>
  <ul id="tried"></ul>
  <p class="note">エンジンを別の場所に置く場合は、この HTML 内の
  <code>CANVAS_BASE</code> にその URL（末尾 <code>/</code> 付き）を設定してください。</p>
</div>
<noscript><p>このページには JavaScript が必要です。</p></noscript>
<script>
(function () {
  "use strict";
  // KASUGAI Canvas エンジン本体（web/ の中身）の配置先。
  // 内部に cesium/ maplibre/ openlayers/ leaflet/ shared/ がある階層を
  // 末尾 / 付きで指定する（例: "https://example.com/canvas/"）。
  // 空 "" のままでは ./ ../ ../../ / の順に __ENGINE__/index.html を自動探索する
  var CANVAS_BASE = "";
  // 公開ホスト版エンジンの URL（末尾 / 付き。例: "https://example.com/canvas/"）。
  // 設定すると file:// でローカルCanvas未検出時に「ホスト版で開く」
  // （ブラウザのみでローカルフォルダを読む ?kasc=local モード）の
  // 選択肢を表示する
  var HOSTED_BASE = "https://yamamoto-ryuzo.github.io/kasugai-canvas-web/latest/";
  var ENGINE = "__ENGINE__";
  var KASC = "__KASC__";
  var kascUrl = new URL(KASC, location.href).href;
  var ENGINES = ["cesium", "maplibre", "openlayers", "leaflet"];
  function engineBase(base) {
    // ベースの末尾がエンジン名ディレクトリなら差し替え、違えば ENGINE を付ける
    var u = new URL(base, location.href);
    u.search = ""; u.hash = "";
    var seg = u.pathname.replace(/[/]+$/, "").split("/").pop().toLowerCase();
    if (ENGINES.indexOf(seg) >= 0) {
      u.pathname = u.pathname.replace(/[^/]+\/?$/, ENGINE + "/");
      return u.href;
    }
    return new URL(ENGINE + "/", u).href;
  }
  function target(base) {
    return engineBase(base) + "?kasc=" + encodeURIComponent(kascUrl);
  }
  // file:// で開かれた場合はローカルの KASUGAI Canvas(127.0.0.1:8510)へ
  // .kasc を外部プロジェクト登録し /<engine>/?project=<id> へ転送する。
  // ブラウザは file:// ページからローカルファイルを fetch できないため
  // WEB 用の探索は行わない（CANVAS_BASE 指定時はそちら優先）
  if (!CANVAS_BASE && location.protocol === "file:") {
    var kascPath = decodeURIComponent(new URL(KASC, location.href).pathname)
      .replace(/^\\/([A-Za-z]:)/, "$1").replace(/\\//g, "\\\\");
    function localHelp() {
      document.getElementById("status").innerHTML =
        "ローカルの KASUGAI Canvas（<a href='http://127.0.0.1:8510/'>127.0.0.1:8510</a>）に接続できません。" +
        "アプリを起動してからこのページを再読み込みしてください。" +
        "（外部 WEB で使う場合は、このフォルダとエンジンを同じサーバーへアップしてください）";
      // ホスト版で開く: HOSTED_BASE 未設定でも手入力できる。
      // 入力値は localStorage に保持(file:// 共通オリジンで全ランチャー共有)
      var row = document.createElement("div");
      row.style.cssText = "margin-top:10px";
      var inp = document.createElement("input");
      inp.placeholder = "ホスト版URL（例: https://example.com/canvas/）";
      inp.style.cssText = "width:65%;padding:4px";
      try {
        inp.value = HOSTED_BASE || localStorage.getItem("kasugai_hosted_base") || "";
      } catch (e) { inp.value = HOSTED_BASE; }
      var go = document.createElement("button");
      go.textContent = "ホスト版で開く";
      go.style.cssText = "padding:4px 10px;margin-left:4px";
      go.onclick = function () {
        var base = inp.value.trim();
        if (!base) return;
        if (!/[\\/]$/.test(base)) base += "/";
        try { localStorage.setItem("kasugai_hosted_base", base); } catch (e) {}
        // このフォルダ名を dirhint として渡し、ホスト版の選択UIで案内する
        var dirName = "";
        try {
          dirName = decodeURIComponent(location.pathname.replace(/\/[^/]*$/, "")
            .split("/").filter(Boolean).pop() || "");
        } catch (e) {}
        location.href = engineBase(base) + "?kasc=local" +
          (dirName ? "&dirhint=" + encodeURIComponent(dirName) : "");
      };
      row.appendChild(inp); row.appendChild(go);
      var hint = document.createElement("div");
      hint.style.cssText = "font-size:11px;color:#667;margin-top:4px";
      hint.textContent = "ブラウザのみで動作します（このフォルダを選択 → ?kasc=local）";
      row.appendChild(hint);
      document.getElementById("status").appendChild(row);
    }
    fetch("http://127.0.0.1:8510/api/projects/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: kascPath })
    }).then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (res) {
        if (res && res.id) {
          location.replace("http://127.0.0.1:8510/" + ENGINE + "/?project=" + encodeURIComponent(res.id));
        } else { localHelp(); }
      }).catch(localHelp);
    return;
  }
  if (CANVAS_BASE) {
    location.replace(target(new URL(CANVAS_BASE, location.href)));
    return;
  }
  var bases = ["./", "../", "../../", "/"];
  var i = 0;
  function next() {
    if (i >= bases.length) {
      document.getElementById("status").hidden = true;
      document.getElementById("notfound").hidden = false;
      return;
    }
    var base = new URL(bases[i], location.href); i += 1;
    var probe = new URL(ENGINE + "/index.html", base).href;
    var li = document.createElement("li");
    var a = document.createElement("a");
    a.href = target(base); a.textContent = probe;
    li.appendChild(a);
    document.getElementById("tried").appendChild(li);
    fetch(probe, { method: "HEAD", cache: "no-store" })
      .then(function (r) { if (r.ok) location.replace(target(base)); else next(); })
      .catch(function () { next(); });
  }
  next();
})();
</script>
</body>
</html>
'''

_LAUNCHER_INDEX_HTML = '''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>KASUGAI Canvas プロジェクト — __KASC__</title>
<style>
  body { font-family: system-ui,"Segoe UI","Yu Gothic",sans-serif; margin: 28px; line-height: 1.65; color: #1d2b35; }
  code { background: #eef2f5; padding: 1px 5px; border-radius: 4px; }
  li { margin: 4px 0; }
  a { color: #2c5ea8; }
  .note { color: #52636d; font-size: 0.9em; }
</style>
</head>
<body>
<h1 style="font-size:1.15em">KASUGAI Canvas プロジェクト</h1>
<p><code>__KASC__</code> を各エンジンで開きます:</p>
<ul>
  <li><a href="cesium.html">Cesium（3D・既定エンジン）</a></li>
  <li><a href="maplibre.html">MapLibre GL</a></li>
  <li><a href="openlayers.html">OpenLayers</a></li>
  <li><a href="leaflet.html">Leaflet</a></li>
</ul>
<p class="note">このフォルダとエンジン（web/ の中身）を同じ Web サーバーへ
アップすればサーバーレスで動作します。エンジンの自動探索に失敗する場合は
各 HTML 内の <code>CANVAS_BASE</code> を設定してください。</p>
</body>
</html>
'''



def normalize_engine(engine):
    """engine 名を正規化。無効値は None を返す。"""
    e = str(engine or '').strip().lower()
    return e if e in VALID_ENGINES else None


def _qsettings():
    from qgis.PyQt.QtCore import QSettings
    return QSettings('GeoWebView', 'geo_webview')


def default_output_dir():
    """既定出力先: <ドキュメント>/kasugai_canvas_qgis。"""
    try:
        from qgis.PyQt.QtCore import QStandardPaths
        loc = getattr(
            getattr(QStandardPaths, 'StandardLocation', QStandardPaths),
            'DocumentsLocation')
        docs = QStandardPaths.writableLocation(loc)
        if docs:
            return os.path.join(docs, 'kasugai_canvas_qgis')
    except Exception:  # nosec B110  # 設計上の許容
        pass
    import tempfile
    return os.path.join(tempfile.gettempdir(), 'kasugai_canvas_qgis')


def get_output_dir():
    """QSettings の kasugai_output_path(空/'__default__'は既定)を返す。"""
    try:
        saved = _qsettings().value(SETTINGS_KEY_OUTPUT, '') or ''
        saved = str(saved).strip()
        if saved and saved != '__default__':
            return saved
    except Exception:  # nosec B110  # 設計上の許容
        pass
    return default_output_dir()


def get_kasugai_install_dir():
    """QSettings の kasugai_install_path（KASUGAI Canvas インストール先）を返す。

    設定済みでディレクトリが存在する場合のみ返し、それ以外は None。
    空/'__default__' は未設定扱い。
    """
    try:
        saved = (_qsettings().value('kasugai_install_path', '') or '').strip()
        if saved and saved != '__default__' and os.path.isdir(saved):
            return saved
    except Exception:  # nosec B110  # 設計上の許容
        pass
    return None


def _registry_install_dir():
    """Windows インストーラが登録するインストール先をレジストリから返す。

    HKCU\\...\\Uninstall\\KASUGAI Canvas\\InstallLocation。
    未登録・非 Windows は None。
    """
    if os.name != 'nt':
        return None
    try:
        import winreg
        with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, _KASUGAI_UNINSTALL_KEY) as key:
            loc = winreg.QueryValueEx(key, 'InstallLocation')[0]
        if loc and os.path.isdir(loc):
            return loc
    except Exception:  # nosec B110  # レジストリ未登録は正常系
        pass
    return None


def detect_kasugai_install_dir():
    """KASUGAI Canvas のインストール先を特定して返す（見つからなければ None）。

    1) QSettings ``kasugai_install_path``（設定で明示登録）
    2) Windows インストーラのレジストリ InstallLocation（設定未登録でも
       インストール済みなら一体運用に使う）
    """
    return get_kasugai_install_dir() or _registry_install_dir()


def kasugai_projects_dir():
    """KASUGAI インストール先の projects/ ディレクトリを返す（未設定なら None）。

    <install>/projects/ を優先し、無ければ <install>/web/projects/、
    どちらも無ければ <install>/projects/ を作成して返す。
    """
    install = detect_kasugai_install_dir()
    if not install:
        return None
    for cand in (os.path.join(install, 'projects'),
                 os.path.join(install, 'web', 'projects')):
        if os.path.isdir(cand):
            return cand
    cand = os.path.join(install, 'projects')
    os.makedirs(cand, exist_ok=True)
    return cand


def kasugai_qgis_projects_dir():
    """QGIS 連携プロジェクト専用の ``<install>/QGIS_projects/`` を返す。

    Canvas 本体の ``projects/``（ユーザー管理）と分離し、QGIS 由来の
    エクスポートを専用フォルダに置く。Canvas への表示は
    ``/api/projects/register`` の外部プロジェクト登録経由。
    インストール先を検出できなければ None（設定未登録でもレジストリ
    検出で一体運用になる）。ディレクトリは必要時に作成する。
    """
    install = detect_kasugai_install_dir()
    if not install:
        return None
    cand = os.path.join(install, 'QGIS_projects')
    os.makedirs(cand, exist_ok=True)
    return cand


def preferred_output_dir(project_name=None):
    """QGIS 連携プロジェクトの出力先ディレクトリを決める。

    KASUGAI Canvas のインストール先が登録済みなら
    ``<install>/QGIS_projects/<QGISプロジェクト名>/`` を返す
    （Canvas 本体の projects/ と分離した QGIS 連携専用フォルダ。
    Canvas への表示は外部プロジェクト登録経由）。未登録なら
    ``get_output_dir()``（既定: ``<Documents>/kasugai_canvas_qgis``）。

    project_name 未指定時は QgsProject.instance().baseName()。
    """
    proj_dir = kasugai_qgis_projects_dir()
    if proj_dir:
        if not project_name:
            try:
                from qgis.core import QgsProject
                project_name = QgsProject.instance().baseName()
            except Exception:  # nosec B110  # 設計上の許容
                project_name = None
        return os.path.join(
            proj_dir, project_dir_slug(project_name or 'qgis_export'))
    return get_output_dir()


_last_export_dir = None


def last_export_dir():
    """直近のエクスポート出力先（/export-data/ の配信ルート）。

    セッション内で一度もエクスポートしていなければ get_output_dir()。
    """
    return _last_export_dir or get_output_dir()


def project_dir_slug(name):
    """プロジェクト名から projects/<id>/ 用の安全なスラッグを作る。"""
    import re as _re
    slug = _re.sub(r'[^A-Za-z0-9_-]+', '_', str(name or '').strip()).strip('_')
    return slug or 'qgis_export'


def get_kasugai_port():
    """QSettings の kasugai_port(未設定は8510)を返す。"""
    try:
        saved = _qsettings().value(SETTINGS_KEY_PORT, '') or ''
        if str(saved).strip():
            return int(str(saved).strip())
    except Exception:  # nosec B110  # 設計上の許容
        pass
    return DEFAULT_KASUGAI_PORT


def _slugify(name, used):
    """レイヤ名からDATA/用の安全なファイル名(ASCII)を作る。"""
    slug = re.sub(r'[^A-Za-z0-9_\-]+', '_', str(name or '')).strip('_')
    if not slug:
        slug = 'layer'
    base = slug
    i = 2
    while slug.lower() in used:
        slug = '{0}_{1}'.format(base, i)
        i += 1
    used.add(slug.lower())
    return slug


def _kasc_escape(text):
    """.kasc 行の | 区切り・改行を壊さないようサニタイズする。"""
    return re.sub(r'[|\r\n]+', ' ', str(text or '')).strip()


def _tree_layers():
    """レイヤツリー順(上から)に (layer, group_path, visible) で返す。

    visible はノード自身のチェックと全祖先の表示状態の積(実効表示状態)。
    """
    from qgis.core import QgsProject
    project = QgsProject.instance()
    root = project.layerTreeRoot()
    result = []

    def _walk(node, groups, visible):
        from qgis.core import QgsLayerTreeGroup, QgsLayerTreeLayer
        for child in node.children():
            try:
                checked = child.itemVisibilityChecked()
            except Exception:
                checked = True
            eff = visible and bool(checked)
            if isinstance(child, QgsLayerTreeGroup):
                _walk(child, groups + [child.name()], eff)
            elif isinstance(child, QgsLayerTreeLayer):
                lyr = child.layer()
                if lyr is not None:
                    result.append((lyr, list(groups), eff))

    _walk(root, [], True)
    return result


def _geo_equiv_crs(layer):
    """Canvas が再投影なしで扱える地理座標系か(4326 系・CRS84・JGD)。"""
    try:
        crs = layer.crs()
        if not crs or not crs.isValid():
            return False
        if crs.authid().upper() in ('EPSG:4326', 'EPSG:4269',
                                    'EPSG:4612', 'EPSG:6668'):
            return True
        return crs.isGeographic()
    except Exception:
        return False


def _source_path(layer):
    """ogr 系ソースの実ファイルパスを取り出す。なければ None。"""
    try:
        from qgis.core import QgsDataSourceUri
        db = QgsDataSourceUri(layer.source()).database()
    except Exception:
        db = ''
    cand = db or (layer.source() or '').split('|')[0]
    cand = urllib.parse.unquote(cand)
    if cand.startswith('file://'):
        cand = cand[7:]
    if re.match(r'^/[A-Za-z]:/', cand):
        cand = cand[1:]
    return cand if cand and os.path.exists(cand) else None


def _copy_to_data(src_path, data_dir, slug, copied):
    """ローカルファイルを DATA/<slug><ext> へコピーし 'DATA/...' を返す。"""
    src_abs = os.path.abspath(src_path)
    if src_abs in copied:
        return copied[src_abs]
    ext = os.path.splitext(src_abs)[1]
    dest_abs = os.path.join(data_dir, slug + ext)
    same = False
    try:
        same = os.path.samefile(src_abs, dest_abs)
    except Exception:  # nosec B110  # 存在しない場合はコピー対象
        pass
    if not same:
        i = 2
        while os.path.exists(dest_abs):
            dest_abs = os.path.join(data_dir,
                                    '{0}_{1}{2}'.format(slug, i, ext))
            i += 1
        shutil.copy2(src_abs, dest_abs)
    rel = 'DATA/' + os.path.basename(dest_abs)
    copied[src_abs] = rel
    return rel


# DATA/ へ複製するローカルディレクトリツリー(3D Tiles / ローカルXYZタイル)の上限
_LOCAL_TREE_MAX_BYTES = 1024 ** 3  # 1 GiB

# duckdb: 行へ回せる区切りテキストの拡張子(delimitedtext / ogr 共通)
_DUCKDB_TEXT_EXTS = ('.csv', '.tsv')


def _local_path(s):
    """file:///・/C:/ 形式・クエリ/パイプ付きURIからローカルパスを取り出す。"""
    p = urllib.parse.unquote((s or '').split('?')[0].split('|')[0])
    if p.startswith('file://'):
        p = p[7:]
    if re.match(r'^/[A-Za-z]:/', p):
        p = p[1:]
    return p


def _tree_bytes(path, cap):
    """ディレクトリ以下の合計バイト数。cap 超過で打ち切り。"""
    total = 0
    for _root, _dirs, files in os.walk(path):
        for fn in files:
            try:
                total += os.path.getsize(os.path.join(_root, fn))
            except OSError:
                pass
            if total > cap:
                return total
    return total


def _copy_tree_to_data(src_dir, data_dir, slug, copied):
    """ローカルディレクトリを DATA/<slug>/ へ複製し 'DATA/<slug>' を返す。

    既存の同名ディレクトリは(前回エクスポート産物として)置き換える。
    """
    src_abs = os.path.abspath(src_dir)
    if src_abs in copied:
        return copied[src_abs]
    dest_abs = os.path.join(data_dir, slug)
    same = False
    try:
        same = os.path.samefile(src_abs, dest_abs)
    except Exception:  # nosec B110  # 存在しない場合はコピー対象
        pass
    if not same:
        if os.path.isdir(dest_abs):
            shutil.rmtree(dest_abs)
        shutil.copytree(src_abs, dest_abs)
    rel = 'DATA/' + slug
    copied[src_abs] = rel
    return rel


def _subset_filter(layer):
    """レイヤのプロバイダフィルタ(subsetString)を where= 値として返す。

    ``|`` を含む式は .kasc 行の区切りと衝突するため None を返す
    (呼び出し側は GeoJSON 再エクスポートでフィルタを反映する)。
    """
    try:
        raw = (layer.subsetString() or '').strip()
    except Exception:  # nosec B110  # 設計上の許容
        return None
    if not raw or '|' in raw:
        return None
    return _kasc_escape(raw) or None


def _has_unusable_subset(layer):
    """subsetString が設定済みだが | を含み where= に変換できないか。"""
    try:
        raw = (layer.subsetString() or '').strip()
    except Exception:  # nosec B110  # 設計上の許容
        return False
    return bool(raw and '|' in raw)


def _csv_geom_hints(path):
    """ローカル CSV/TSV のヘッダ行からジオメトリ列・経度/緯度列を推定する。

    戻り値 (geom_col, lon_col, lat_col)。読めなければ (None,None,None)。
    列名は Canvas 側の自動検出(geometry/geom/wkb/the_geom・lon/lat 慣用名)
    より広く、明示指定に使える名前(wkt/x/y)も拾う。
    """
    try:
        with open(path, 'rb') as f:
            raw = f.read(131072)
    except Exception:  # nosec B110  # 設計上の許容
        return None, None, None
    lines = raw.decode('utf-8-sig', errors='replace').splitlines()
    if not lines:
        return None, None, None
    head = lines[0]
    delim = max((',', ';', '\t', '|'), key=lambda d: head.count(d))
    names = [c.strip().strip('"').strip("'") for c in head.split(delim)]
    lower = {n.lower(): n for n in names if n}
    geom = next((lower[k] for k in
                 ('geometry', 'geom', 'wkt', 'wkb', 'the_geom')
                 if k in lower), None)
    lon = next((lower[k] for k in
                ('lon', 'lng', 'longitude', 'x') if k in lower), None)
    lat = next((lower[k] for k in
                ('lat', 'latitude', 'y') if k in lower), None)
    return geom, lon, lat


def _delimited_params(layer):
    """delimitedtext プロバイダのソースを (パスorURL, クエリparams) に分解。"""
    src = layer.source() or ''
    if '?' in src:
        path, _, qs = src.partition('?')
        params = {k.lower(): v for k, v in
                  urllib.parse.parse_qsl(qs, keep_blank_values=True)}
    else:
        path, params = src, {}
    return path, params


def _is_tiled_scene(layer):
    """QgsTiledSceneLayer(QGIS 3.34+ の 3D Tiles レイヤ)か。"""
    try:
        from qgis.core import QgsTiledSceneLayer
        return isinstance(layer, QgsTiledSceneLayer)
    except Exception:
        # 旧バージョン・独自型はプロバイダ名で判定
        # (QGIS3=tiled_scene / QGIS4=tiledscene・cesiumtiles・esrii3s)
        try:
            return (layer.providerType() or '') in (
                'tiled_scene', 'tiledscene', 'cesiumtiles', 'esrii3s')
        except Exception:  # nosec B110  # 設計上の許容
            return False


def _tiledscene_ref(layer, slug, data_dir, copied, warnings):
    """3D Tiles レイヤの参照先を返す。解決できなければ None。

    - http(s)/vsicurl URL → そのまま参照
    - ローカルの tileset.json(またはそのディレクトリ) → ディレクトリツリーを
      DATA/<slug>/ へ複製して DATA/<slug>/<basename> を返す
    """
    src = layer.source() or ''
    m = re.search(r'(?:^|&)url=([^&]+)', src)
    target = urllib.parse.unquote(m.group(1)) if m else src.strip()
    if not target:
        return None
    if target.startswith('/vsicurl/'):
        target = target[len('/vsicurl/'):]
    if re.match(r'https?://', target):
        # Cesium tileset.json のみ対応(Esri i3s 等の SceneServer URL は除外)
        if target.split('?')[0].lower().endswith('.json'):
            return target
        return None
    path = _local_path(target)
    if os.path.isdir(path):
        base_dir, ts_path = path, os.path.join(path, 'tileset.json')
    else:
        base_dir, ts_path = os.path.dirname(path) or path, path
    if not os.path.isfile(ts_path):
        return None
    if _tree_bytes(base_dir, _LOCAL_TREE_MAX_BYTES) > _LOCAL_TREE_MAX_BYTES:
        warnings.append(
            '{0}: 3dtiles ディレクトリが {1} 超のため複製を中止'.format(
                layer.name(), _LOCAL_TREE_MAX_BYTES))
        return None
    _copy_tree_to_data(base_dir, data_dir, slug, copied)
    return 'DATA/{0}/{1}'.format(slug, os.path.basename(ts_path))


def _local_xyz_template(url, slug, data_dir, copied, warnings):
    """ローカル XYZ テンプレート(file:///.../{z}/{x}/{y}.png)を DATA/ へ複製。

    戻り値 'DATA/<slug>/{z}/{x}/{y}.png' 形式の参照テンプレート。解決不可・
    サイズ超過時は None。
    """
    path = _local_path(url)
    if '{z}' not in path:
        return None
    base, _, rest = path.partition('{z}')
    base_dir = base.rstrip('/\\')
    template = '{z}' + rest
    if not os.path.isdir(base_dir):
        return None
    if _tree_bytes(base_dir, _LOCAL_TREE_MAX_BYTES) > _LOCAL_TREE_MAX_BYTES:
        warnings.append(
            '{0}: ローカルタイルツリーが {1} 超のため複製を中止'.format(
                slug, _LOCAL_TREE_MAX_BYTES))
        return None
    _copy_tree_to_data(base_dir, data_dir, slug, copied)
    return 'DATA/{0}/{1}'.format(slug, template.replace(os.sep, '/'))


def _maplayer_opacity(layer):
    """レイヤ不透明度(0-1)。1.0 または取得不可なら None。"""
    try:
        op = float(layer.opacity())
        return op if 0.0 <= op < 0.999 else None
    except Exception:  # nosec B110  # 設計上の許容
        return None


def _layer_extent_bbox(layer):
    """レイヤ範囲を EPSG:4326 の 'w,s,e,n' 文字列に。全域相当/失敗時 None。"""
    try:
        from qgis.core import (QgsCoordinateReferenceSystem,
                               QgsCoordinateTransform, QgsProject)
        ext = layer.extent()
        if not ext or not ext.isFinite() or ext.isEmpty():
            return None
        crs = layer.crs()
        if crs and crs.isValid() and crs.authid() != 'EPSG:4326':
            tr = QgsCoordinateTransform(
                crs, QgsCoordinateReferenceSystem('EPSG:4326'),
                QgsProject.instance())
            ext = tr.transform(ext)
        w, s, e, n = (ext.xMinimum(), ext.yMinimum(),
                      ext.xMaximum(), ext.yMaximum())
        if e - w >= 350.0 or n - s >= 170.0:
            return None
        return '{0:.6f},{1:.6f},{2:.6f},{3:.6f}'.format(w, s, e, n)
    except Exception:
        return None


def _skip_reason(layer):
    """skipped 記録用の種別文字列(クラス名+プロバイダ)。"""
    prov = ''
    try:
        prov = layer.providerType() or ''
    except Exception:  # nosec B110  # 設計上の許容
        pass
    cls = type(layer).__name__.replace('Qgs', '')
    return '{0}({1})'.format(cls, prov) if prov else cls


def _duckdb_target_ref(target, slug, data_dir, copied):
    """duckdb: 参照用に target(URL or ローカルパス)を ref へ変換する。"""
    if re.match(r'https?://', target):
        return target
    path = _local_path(target)
    if not path or not os.path.exists(path):
        return None
    return _copy_to_data(path, data_dir, slug, copied)


def _native_ref(layer, slug, data_dir, copied, warnings):
    """Canvas が直接参照できるソースなら参照辞書を返す。

    戻り値: ``{'type': <kasc行タイプ>, 'ref': <参照>, 'opts': {k: v}}``、
    または ``{'skip_reason': <理由>}``(表示不能と確定)、不可時は None
    (呼び出し側で GeoJSON 再エクスポートに回す)。

    - http(s) ソース: 拡張子に応じて URL をそのまま参照
    - ローカルファイル: DATA/<slug><ext> へコピーして相対参照
    - delimitedtext / .csv,.tsv → ``duckdb:``(lon=/lat=/geom= 付き)
    - subsetString → gpkg は ``where=``、parquet は ``duckdb:+format=parquet``
      へ切替、GeoJSON/FGB はフィルタ反映のため GeoJSON 変換へ回す
    地理座標系でない場合は None(GeoJSON 再エクスポートへ回す)。
    """
    src = layer.source() or ''
    subset = _subset_filter(layer)

    # delimitedtext プロバイダ(CSV/TSV等) → duckdb:
    if (layer.providerType() or '') == 'delimitedtext':
        path, params = _delimited_params(layer)
        geom = params.get('wktfield') or None
        lon = params.get('xfield') or None
        lat = params.get('yfield') or None
        if not geom and not (lon and lat):
            return {'skip_reason': 'ジオメトリ列なし(属性テーブル)'}
        if not _geo_equiv_crs(layer):
            return None  # 再投影が必要 → GeoJSON 変換
        ref = _duckdb_target_ref(path, slug, data_dir, copied)
        if not ref:
            return None
        opts = {'format': 'tsv' if path.lower().endswith('.tsv') else 'csv'}
        if geom:
            opts['geom'] = geom
        else:
            opts['lon'] = lon
            opts['lat'] = lat
        if subset:
            opts['where'] = subset
        return {'type': 'duckdb', 'ref': ref, 'opts': opts}

    # http(s)/vsicurl ソース → 拡張子で行タイプ決定
    if re.match(r'https?://', src) or src.startswith('/vsicurl/'):
        url = src.replace('/vsicurl/', '')
        low = url.split('?')[0].lower()
        kind, ext = None, None
        for e, k in (('.gpkg', 'gpkg'), ('.geojson', 'geojson'),
                     ('.json', 'geojson'), ('.parquet', 'geoparquet'),
                     ('.fgb', 'flatgeobuf'),
                     ('.csv', 'duckdb'), ('.tsv', 'duckdb')):
            if low.endswith(e):
                kind, ext = k, e
                break
        if not kind:
            return None
        opts = {}
        if kind == 'duckdb':
            opts['format'] = 'tsv' if ext == '.tsv' else 'csv'
        if subset:
            if kind in ('gpkg', 'duckdb'):
                opts['where'] = subset
            elif kind == 'geoparquet':
                kind = 'duckdb'
                opts['format'] = 'parquet'
                opts['where'] = subset
            else:
                # geojson:/flatgeobuf: に where= は無い → GeoJSON 変換で反映
                return None
        return {'type': kind, 'ref': url, 'opts': opts}

    # ローカルファイルソース
    src_path = _source_path(layer)
    if not src_path:
        return None
    ext = os.path.splitext(src_path)[1].lower()

    # ogr の区切りテキスト → duckdb:(ヘッダからジオメトリ/経緯度列を推定。
    # ogr CSV は CRS 情報を持たないため値はそのまま=再投影なし)
    if ext in _DUCKDB_TEXT_EXTS:
        geom, lon, lat = _csv_geom_hints(src_path)
        if not geom and not (lon and lat):
            return None
        opts = {'format': 'tsv' if ext == '.tsv' else 'csv'}
        if geom:
            opts['geom'] = geom
        else:
            opts['lon'] = lon
            opts['lat'] = lat
        if subset:
            opts['where'] = subset
        return {'type': 'duckdb',
                'ref': _copy_to_data(src_path, data_dir, slug, copied),
                'opts': opts}

    kinds = {'.gpkg': 'gpkg', '.geojson': 'geojson', '.json': 'geojson',
             '.parquet': 'geoparquet', '.fgb': 'flatgeobuf'}
    kind = kinds.get(ext)
    if not kind:
        return None
    # GeoJSON は仕様上 lon/lat のため CRS 不明でも同等扱いとする
    geojson_spec = ext in ('.geojson', '.json')
    if not geojson_spec and not _geo_equiv_crs(layer):
        return None
    if subset:
        if kind == 'geoparquet':
            kind = 'duckdb'
        elif kind != 'gpkg':
            # geojson/flatgeobuf は where= 非対応 → GeoJSON 変換で反映
            return None
    ref = _copy_to_data(src_path, data_dir, slug, copied)
    opts = {}
    if kind == 'duckdb':
        opts['format'] = 'parquet'
    if kind == 'gpkg':
        m = re.search(r'layername=([^|&]+)', src)
        if m:
            opts['table'] = urllib.parse.unquote(m.group(1))
    if subset:
        opts['where'] = subset
    return {'type': kind, 'ref': ref, 'opts': opts}


def _embed_gpkg_style(layer):
    """GPKG の layer_styles へ既定スタイルを保存する(QGIS 標準機能)。

    データ+スタイルを1ファイルで配布できる。元ファイルに書き込む点に注意。
    """
    try:
        res = layer.saveStyleToDatabase(
            'kasugai', 'KASUGAI Canvas 既定スタイル', True, '')
        if isinstance(res, tuple):
            return bool(res[1]) if len(res) > 1 else not res[0]
        return not res
    except Exception:
        return False


def _export_geojson(layer, path):
    """ベクターレイヤを EPSG:4326 の GeoJSON へ書き出す。"""
    from qgis.core import (QgsCoordinateReferenceSystem,
                           QgsCoordinateTransform, QgsProject,
                           QgsVectorFileWriter)
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = 'GeoJSON'
    options.fileEncoding = 'UTF-8'
    options.ct = QgsCoordinateTransform(
        layer.crs(), QgsCoordinateReferenceSystem('EPSG:4326'),
        QgsProject.instance())
    if hasattr(QgsVectorFileWriter, 'writeAsVectorFormatV3'):
        err, msg, _, _ = QgsVectorFileWriter.writeAsVectorFormatV3(
            layer, path, QgsProject.instance().transformContext(), options)
    else:
        err, msg = QgsVectorFileWriter.writeAsVectorFormatV2(
            layer, path, QgsProject.instance().transformContext(), options)
    if err != QgsVectorFileWriter.NoError:
        raise RuntimeError('GeoJSON export failed: {0} ({1})'.format(err, msg))
    return path


def _export_qml(layer, path):
    """レイヤの現在スタイルを .qml として保存する。"""
    msg, ok = layer.saveNamedStyle(path)
    if not ok:
        raise RuntimeError('qml save failed: {0}'.format(msg))
    return path


def _xyz_layer_info(layer):
    """XYZタイル系ラスタレイヤなら (url, zmin, zmax) を返す。

    source URI は ``key=value&key=value`` 形式で url 値は
    パーセントエンコード済み(&を含まない)。値だけをunquoteすることで
    url内の ``x={x}&y={y}&z={z}`` を保持する。
    """
    try:
        if layer.providerType() not in ('wms',):
            return None
        src = layer.source() or ''
        if 'type=xyz' not in src and 'type%3Dxyz' not in src.lower():
            return None
        params = {}
        for part in src.split('&'):
            if '=' not in part:
                continue
            key, val = part.split('=', 1)
            params[key.strip().lower()] = urllib.parse.unquote(val.strip())
        url = params.get('url')
        if not url:
            return None

        def _num(name):
            try:
                return int(params[name])
            except Exception:
                return None
        return url, _num('zmin'), _num('zmax')
    except Exception:
        return None


def _wms_layer_info(layer):
    """QGIS の WMS ラスタレイヤ(type=xyz 以外)なら
    (base_url, layers_csv, styles_csv, format) を返す。

    source URI は ``key=value&key=value`` 形式で、layers=/styles= は
    繰り返し出る(レイヤ順を保持)。値はパーセントエンコード済み。
    ``wms:`` 行は GetMap を 256px タイルへ分解して参照するため、
    エンドポイントURLは生で渡し、レイヤ指定はオプションとして出す。
    """
    try:
        if layer.providerType() not in ('wms',):
            return None
        src = layer.source() or ''
        if 'type=xyz' in src or 'type%3Dxyz' in src.lower():
            return None
        params = {}
        lists = {}
        for part in src.split('&'):
            if '=' not in part:
                continue
            key, val = part.split('=', 1)
            key = key.strip().lower()
            val = urllib.parse.unquote(val.strip())
            if key in ('layers', 'styles'):
                lists.setdefault(key, []).append(val)
            else:
                params[key] = val
        url = params.get('url')
        if not url or not re.match(r'https?://', url):
            return None
        return (url,
                ','.join(lists.get('layers', [])),
                ','.join(lists.get('styles', [])),
                params.get('format') or '')
    except Exception:
        return None


def _camera_line(iface, height_hint_scale=None):
    """現在キャンバスから cam: 行を作る。失敗時 None。"""
    try:
        from qgis.core import (QgsCoordinateReferenceSystem,
                               QgsCoordinateTransform, QgsPointXY,
                               QgsProject)
        canvas = iface.mapCanvas()
        ext = canvas.extent()
        crs = canvas.mapSettings().destinationCrs()
        tr = QgsCoordinateTransform(
            crs, QgsCoordinateReferenceSystem('EPSG:4326'),
            QgsProject.instance())
        c = tr.transform(QgsPointXY(ext.center().x(), ext.center().y()))
        scale = float(canvas.scale() or 10000)
        # 概算: 画面高~800px * 0.28mm/px * scale を地上高、
        # Cesium fov60° より h ≒ 地上高/1.15 → scale*0.2
        h = max(120.0, scale * 0.2)
        line = 'cam:QGIS|{0:.6f}|{1:.6f}|h={2:.0f}|p=-90'.format(
            c.y(), c.x(), h)
        try:
            rot = float(canvas.rotation())
            if abs(rot) > 0.01:
                line += '|d={0:.1f}'.format(rot % 360)
        except Exception:  # nosec B110  # 設計上の許容
            pass
        return line
    except Exception:
        return None


def _export_bookmarks_xml(path):
    """QGISブックマーク(プロジェクト+アプリケーション)を qgis_bookmarks
    形式の XML として path へ出力する。

    extent は全て EPSG:4326 へ正規化する(sr_id はQGIS内部srsidで
    EPSGと一致しないため、参照側が確実に度単位として読めるようにする)。
    戻り値は書き出した件数。失敗時・0件時は 0(ファイルは作らない)。
    """
    try:
        from qgis.core import (QgsApplication, QgsBookmark,
                               QgsBookmarkManager,
                               QgsCoordinateReferenceSystem,
                               QgsCoordinateTransform, QgsProject,
                               QgsReferencedRectangle)
        project = QgsProject.instance()
        dest = QgsCoordinateReferenceSystem('EPSG:4326')
        # 変換済みブックマークを集める一時マネージャ(initialize しないので
        # ファイルへは書き出さない)
        tmp = QgsBookmarkManager()
        count = 0
        for mgr in (project.bookmarkManager(),
                    QgsApplication.bookmarkManager()):
            if mgr is None:
                continue
            for bm in mgr.bookmarks() or []:
                try:
                    ext = bm.extent()
                    if ext is None or ext.isNull() or ext.isEmpty():
                        continue
                    src = ext.crs()
                    if src is None or not src.isValid():
                        src = project.crs()
                    rect = QgsCoordinateTransform(
                        src, dest, project).transformBoundingBox(ext)
                    nb = QgsBookmark()
                    nb.setName(bm.name())
                    nb.setGroup(bm.group())
                    nb.setRotation(bm.rotation())
                    nb.setExtent(QgsReferencedRectangle(rect, dest))
                    tmp.addBookmark(nb)
                    count += 1
                except Exception:  # nosec B112  # 設計上の許容
                    continue
        if not count:
            return 0
        return count if QgsBookmarkManager.exportToFile(path, [tmp]) else 0
    except Exception:
        return 0


def _attribution(layer):
    """レイヤの出典(attribution)文字列。失敗時は空文字。"""
    try:
        return (layer.attribution() or '').strip()
    except Exception:  # nosec B110  # 設計上の許容
        return ''


def _write_engine_launchers(out_dir, kasc_name):
    """.kasc と同じ場所に <engine>.html 起動ページ一式を出力する。

    生成物:
        cesium.html / maplibre.html / openlayers.html / leaflet.html —
            同名エンジンへ ``?kasc=<この .kasc の絶対URL>`` 付きで転送する
            自己完結ランチャー。エンジン本体(web/ の中身)は ./ ../ ../../ /
            の順に自動探索し、見つからなければHTML内の CANVAS_BASE を
            編集して使う
        index.html — 4エンジンへのリンク一覧(フォルダを直接開いた時の案内)

    出力フォルダとエンジンを同じ静的 Web サーバーへアップするだけで
    動く、サーバレス配布のための部品。
    """
    written = []
    for engine in _LAUNCHER_ENGINES:
        html = (_ENGINE_LAUNCHER_HTML
                .replace('__ENGINE__', engine)
                .replace('__KASC__', kasc_name))
        path = os.path.join(out_dir, '{0}.html'.format(engine))
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        written.append(path)
    idx_path = os.path.join(out_dir, 'index.html')
    with open(idx_path, 'w', encoding='utf-8') as f:
        f.write(_LAUNCHER_INDEX_HTML.replace('__KASC__', kasc_name))
    written.append(idx_path)
    return written


def export_kasugai_project(iface, out_dir=None, visible_only=True,
                           native_formats=True, hidden_as_off=False,
                           embed_gpkg_style=False, reearth_port=None,
                           emit_themes=True, emit_bookmarks=True,
                           emit_launchers=True):
    """レイヤツリーを KASUGAI Canvas プロジェクトとして出力する。

    引数:
        visible_only: True なら非表示レイヤは出力しない(既定)。
        native_formats: True なら GPKG/GeoJSON/GeoParquet/FlatGeobuf
            ソース(ローカルファイル・http URL)をそのまま参照し、
            CSV/TSV(delimitedtext 等)は ``duckdb:`` 行(lon=/lat=/geom=)、
            フィルタ付き GPKG は ``where=`` 付き ``gpkg:``、
            フィルタ付き Parquet は ``duckdb:+format=parquet+where=``、
            3D Tiles レイヤは ``3dtiles:``、ローカル XYZ テンプレートは
            タイルツリー複製の ``xyz:`` 行として出力する。
            それ以外のベクターのみ GeoJSON(EPSG:4326)へ出力する。
            False なら全ベクターを GeoJSON へ変換する(従来動作)。
        hidden_as_off: True なら非表示レイヤも ``| off`` 付きで出力する
            (visible_only より優先。プロジェクト構成の丸ごと引越し用)。
        embed_gpkg_style: True なら gpkg: 参照レイヤの現在スタイルを
            QGIS 標準の layer_styles(useAsDefault)へも保存する。
            **元の .gpkg ファイルへ書き込む**点に注意(opt-in)。
        emit_themes: True ならプロジェクトのマップテーマを ``theme:`` 行
            (Canvas の可視性プリセット)として出力する(既定)。
            テーマが存在する場合、非表示レイヤも ``| off`` で出力しないと
            テーマ側から表示へ戻せないため、hidden_as_off 同等に全レイヤを
            出力する。テーマが無ければ従来どおりの出力。
        emit_bookmarks: True ならプロジェクト+アプリケーションの
            ブックマークを ``bookmarks.xml``(qgis_bookmarks 形式・
            EPSG:4326 正規化)として出力し ``bookmark:`` 行を書く(既定)。
            Canvas 側ではカメラプリセットUIにそのまま並ぶ。
        emit_launchers: True なら .kasc と同じ場所に
            ``<engine>.html``(cesium/maplibre/openlayers/leaflet)と
            ``index.html`` のエンジン起動ページを出力する(既定)。
            各HTMLは ``?kasc=<この .kasc の絶対URL>`` 付きでエンジンへ
            転送し、エンジン本体(web/ の中身)を ./ ../ ../../ / の順に
            自動探索する。出力フォルダとエンジンを同じ静的サーバーへ
            アップするだけで動くサーバレス配布の部品。

    戻り値: {"dir","kasc","data_dir","layers":[{name,file,features}],
             "tiles":[...],"skipped":[...],"errors":[...],"warnings":[...],
             "launchers":[...]}。
    layers が1件も無くても .kasc は出力する。
    """
    from qgis.core import QgsVectorLayer, QgsProject
    out_dir = os.path.abspath(out_dir or get_output_dir())
    data_dir = os.path.join(out_dir, 'DATA')
    os.makedirs(data_dir, exist_ok=True)
    global _last_export_dir
    _last_export_dir = out_dir

    project = QgsProject.instance()
    project_title = os.path.splitext(
        os.path.basename(project.fileName() or ''))[0] or 'QGIS Export'

    used_names = set()
    copied = {}
    layers_out, tiles_out, skipped, errors, warnings = [], [], [], [], []
    kasc_lines = []
    detected_base = None  # 表示中の最下段 XYZ → base: 行

    tree = _tree_layers()

    # theme: 行(マップテーマ → Canvas 可視性プリセット)の素材。
    # テーマが存在する場合、非表示レイヤも | off で出さないとテーマ適用時に
    # 表示へ戻せないため、hidden_as_off 同等に全レイヤを出力対象にする
    theme_names = []
    if emit_themes:
        try:
            theme_names = sorted(
                project.mapThemeCollection().mapThemes() or [])
        except Exception:
            theme_names = []
    export_hidden_off = hidden_as_off or bool(theme_names)

    # base: 判定用に表示中の最下段 XYZ を先に特定する
    last_xyz_id = None
    for layer, _groups, vis in tree:
        if vis and _xyz_layer_info(layer):
            last_xyz_id = id(layer)

    for layer, groups, visible in tree:
        title = '/'.join(
            [_kasc_escape(g) for g in groups if g] +
            [_kasc_escape(layer.name())])
        if not visible:
            if export_hidden_off:
                vis_flag = 'off'
            elif not visible_only:
                vis_flag = 'on'
            else:
                continue
        else:
            vis_flag = 'on'

        if isinstance(layer, QgsVectorLayer):
            # ジオメトリを持たない属性テーブルは Canvas で描画できない
            try:
                from qgis.core import QgsWkbTypes
                if layer.wkbType() == QgsWkbTypes.NoGeometry:
                    skipped.append(
                        '{0} (属性テーブル)'.format(layer.name()))
                    continue
            except Exception:  # nosec B110  # 設計上の許容
                pass
            slug = _slugify(layer.name() or 'layer', used_names)
            qml_path = os.path.join(data_dir, slug + '.qml')
            style_opt = ''
            try:
                _export_qml(layer, qml_path)
                style_opt = ' | style=DATA/{0}.qml'.format(slug)
            except Exception as e:
                errors.append('{0}: qml {1}'.format(layer.name(), e))
            feat_count = -1
            try:
                feat_count = int(layer.featureCount())
            except Exception:  # nosec B110  # 設計上の許容
                pass

            if _has_unusable_subset(layer):
                warnings.append(
                    '{0}: フィルタに | を含むためGeoJSON変換'.format(
                        layer.name()))
                native = None
            else:
                native = _native_ref(layer, slug, data_dir, copied,
                                     warnings) if native_formats else None
            if isinstance(native, dict) and native.get('skip_reason'):
                skipped.append(
                    '{0} ({1})'.format(layer.name(), native['skip_reason']))
                continue
            if native:
                line_type, ref = native['type'], native['ref']
                if embed_gpkg_style and line_type == 'gpkg':
                    if _embed_gpkg_style(layer):
                        warnings.append(
                            '{0}: layer_styles に既定スタイルを保存'.format(
                                layer.name()))
                    else:
                        warnings.append(
                            '{0}: layer_styles への保存に失敗'.format(
                                layer.name()))
                line = '{0}: {1} | {2} | {3}'.format(
                    line_type, title, _kasc_escape(ref), vis_flag)
                for key, val in native.get('opts', {}).items():
                    line += ' | {0}={1}'.format(key, _kasc_escape(val))
                line += style_opt
                attr = _attribution(layer)
                if attr:
                    line += ' | attr={0}'.format(_kasc_escape(attr))
                layers_out.append({
                    'name': layer.name(), 'title': title, 'file': ref,
                    'qml': 'DATA/{0}.qml'.format(slug) if style_opt else None,
                    'features': feat_count, 'format': line_type,
                })
                kasc_lines.append(line)
                continue

            # ネイティブ参照できないベクター → GeoJSON(EPSG:4326)へ変換
            gj_path = os.path.join(data_dir, slug + '.geojson')
            try:
                _export_geojson(layer, gj_path)
            except Exception as e:
                errors.append('{0}: geojson {1}'.format(layer.name(), e))
                continue
            if not _geo_equiv_crs(layer):
                warnings.append(
                    '{0}: CRS {1} を EPSG:4326 へ再投影'.format(
                        layer.name(), layer.crs().authid() or ''))
            layers_out.append({
                'name': layer.name(), 'title': title,
                'file': 'DATA/{0}.geojson'.format(slug),
                'qml': 'DATA/{0}.qml'.format(slug) if style_opt else None,
                'features': feat_count, 'format': 'geojson',
            })
            attr = _attribution(layer)
            attr_opt = ' | attr={0}'.format(
                _kasc_escape(attr)) if attr else ''
            kasc_lines.append(
                'geojson: {0} | DATA/{1}.geojson | {2}{3}{4}'.format(
                    title, slug, vis_flag, style_opt, attr_opt))
        else:
            if _is_tiled_scene(layer):
                slug = _slugify(layer.name() or 'scene', used_names)
                ref = _tiledscene_ref(layer, slug, data_dir, copied,
                                      warnings)
                if ref:
                    line = '3dtiles: {0} | {1} | {2}'.format(
                        title, _kasc_escape(ref), vis_flag)
                    attr = _attribution(layer)
                    if attr:
                        line += ' | attr={0}'.format(_kasc_escape(attr))
                    kasc_lines.append(line)
                    tiles_out.append({'name': layer.name(), 'url': ref,
                                      'type': '3dtiles'})
                else:
                    skipped.append(
                        '{0} (3dtiles参照不可)'.format(layer.name()))
                continue
            xyz = _xyz_layer_info(layer)
            if xyz:
                url, zmin, zmax = xyz
                if not re.match(r'https?://', url):
                    # file:/// 等のローカルタイルテンプレートは DATA/ へ複製
                    slug = _slugify(layer.name() or 'tiles', used_names)
                    ref = _local_xyz_template(url, slug, data_dir, copied,
                                              warnings)
                    if ref:
                        url = ref
                    else:
                        skipped.append(
                            '{0} (ローカルタイル複製不可)'.format(
                                layer.name()))
                        continue
                opacity = _maplayer_opacity(layer)
                bbox = _layer_extent_bbox(layer)
                if visible and id(layer) == last_xyz_id:
                    # QGIS の最下段タイルはベースマップとして出力
                    line = 'base: {0} | {1}'.format(title, _kasc_escape(url))
                    attr = _attribution(layer)
                    if attr:
                        line += ' | {0}'.format(_kasc_escape(attr))
                    if zmax is not None:
                        line += ' | maxZoom={0}'.format(zmax)
                    if zmin is not None:
                        line += ' | minZoom={0}'.format(zmin)
                    if opacity is not None:
                        line += ' | opacity={0}'.format(opacity)
                    detected_base = line
                else:
                    line = 'xyz: {0} | {1} | {2}'.format(
                        title, _kasc_escape(url), vis_flag)
                    if zmax is not None:
                        line += ' | maxZoom={0}'.format(zmax)
                    if zmin is not None:
                        line += ' | minZoom={0}'.format(zmin)
                    if opacity is not None:
                        line += ' | opacity={0}'.format(opacity)
                    if bbox is not None:
                        line += ' | bbox={0}'.format(bbox)
                    attr = _attribution(layer)
                    if attr:
                        line += ' | attr={0}'.format(_kasc_escape(attr))
                    kasc_lines.append(line)
                tiles_out.append({'name': layer.name(), 'url': url,
                                  'type': 'xyz'})
            else:
                wms = _wms_layer_info(layer)
                if wms:
                    url, wms_layers, wms_styles, wms_fmt = wms
                    line = 'wms: {0} | {1} | {2}'.format(
                        title, _kasc_escape(url), vis_flag)
                    if wms_layers:
                        line += ' | layers={0}'.format(
                            _kasc_escape(wms_layers))
                    if wms_styles:
                        line += ' | styles={0}'.format(
                            _kasc_escape(wms_styles))
                    if wms_fmt:
                        line += ' | format={0}'.format(
                            _kasc_escape(wms_fmt))
                    opacity = _maplayer_opacity(layer)
                    bbox = _layer_extent_bbox(layer)
                    if opacity is not None:
                        line += ' | opacity={0}'.format(opacity)
                    if bbox is not None:
                        line += ' | bbox={0}'.format(bbox)
                    attr = _attribution(layer)
                    if attr:
                        line += ' | attr={0}'.format(_kasc_escape(attr))
                    kasc_lines.append(line)
                    tiles_out.append({'name': layer.name(), 'url': url,
                                      'type': 'wms'})
                else:
                    skipped.append(
                        '{0} ({1})'.format(layer.name(), _skip_reason(layer)))

    cam = _camera_line(iface)
    bookmark_count = 0
    if emit_bookmarks:
        bookmark_count = _export_bookmarks_xml(
            os.path.join(out_dir, 'bookmarks.xml'))
    if reearth_port:
        try:
            _write_reearth_txt(iface, out_dir, int(reearth_port), tree,
                               visible_only, hidden_as_off, native_formats,
                               data_dir, copied, used_names,
                               errors, warnings)
        except Exception as e:
            warnings.append('reearth.txt 生成失敗: {0}'.format(e))
    default_bases = [
        'base: 地理院タイル 標準地図 | '
        'https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png | '
        '出典：国土地理院 | maxZoom=18',
        'base: 地理院タイル 淡色地図 | '
        'https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png | '
        '出典：国土地理院 | maxZoom=18',
        'base: 地理院タイル 全国最新写真 | '
        'https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg | '
        '出典：国土地理院 | maxZoom=18',
        'base: OpenStreetMap | https://tile.openstreetmap.org/{z}/{x}/{y}.png | '
        '(c) OpenStreetMap contributors | maxZoom=19',
    ]
    # QGIS 側で表示中の XYZ があれば既定ベースマップとして先頭に置く
    bases = ([detected_base] if detected_base else []) + default_bases
    header = [
        '# Exported from QGIS geo_webview -> KASUGAI Canvas',
    ] + bases
    if cam:
        header.append(cam)
    # QGISブックマーク → bookmarks.xml + bookmark: 行。
    # Canvas 側が XML を読み込んでカメラプリセットへ展開する
    if bookmark_count:
        header.append('bookmark: bookmarks.xml')

    # theme: 行(QGIS マップテーマ → Canvas 可視性プリセット)。
    # 表示レイヤは .kasc のレイヤタイトル(groups/名 のパンくず)と一致させる
    if theme_names:
        try:
            collection = project.mapThemeCollection()
            title_by_id = {}
            for layer, groups, _vis in tree:
                title_by_id[layer.id()] = '/'.join(
                    [_kasc_escape(g) for g in groups if g] +
                    [_kasc_escape(layer.name())])
            for name in theme_names:
                try:
                    visible_ids = set(
                        collection.mapThemeVisibleLayerIds(name))
                    titles = [title_by_id[layer.id()]
                              for layer, _g, _v in tree
                              if layer.id() in visible_ids]
                    kasc_lines.append('theme: {0}{1}'.format(
                        _kasc_escape(name),
                        ''.join(' | ' + t for t in titles)))
                except Exception as e:
                    warnings.append('theme {0}: {1}'.format(name, e))
        except Exception as e:
            warnings.append('theme 行出力失敗: {0}'.format(e))

    kasc_path = os.path.join(out_dir, 'kasugai_canvas.kasc')
    with open(kasc_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(header + kasc_lines) + '\n')
    with open(os.path.join(out_dir, 'project.json'), 'w',
              encoding='utf-8') as f:
        json.dump({'title': project_title}, f, ensure_ascii=False)

    launchers = []
    if emit_launchers:
        try:
            launchers = _write_engine_launchers(
                out_dir, os.path.basename(kasc_path))
        except Exception as e:
            warnings.append('engine launcher html 生成失敗: {0}'.format(e))

    return {
        'dir': out_dir, 'kasc': kasc_path, 'data_dir': data_dir,
        'title': project_title, 'layers': layers_out,
        'tiles': tiles_out, 'skipped': skipped, 'errors': errors,
        'warnings': warnings, 'themes': theme_names,
        'bookmarks': bookmark_count, 'launchers': launchers,
    }


def _reearth_native(layer, slug, data_dir, copied, base_url):
    """geo_suite が解釈できるネイティブ参照を (line_type, url, opts) で返す。

    geo_suite inspector 行の対応タイプ: geojson:/parquet:/flatgeobuf:/
    duckdb:/csv:(gpkg:/sql: は非対応)。URL は http(s) 必須のため、
    ローカルファイルは DATA/ へ複製して /export-data/ の絶対URLにする。
    対象外は None(呼び出し側で GeoJSON 変換へ回す)。
    """
    subset = _subset_filter(layer)
    src = layer.source() or ''

    # delimitedtext → duckdb:
    if (layer.providerType() or '') == 'delimitedtext':
        path, params = _delimited_params(layer)
        geom = params.get('wktfield') or None
        lon = params.get('xfield') or None
        lat = params.get('yfield') or None
        if not geom and not (lon and lat):
            return None
        if not _geo_equiv_crs(layer):
            return None
        ref = _duckdb_target_ref(path, slug, data_dir, copied)
        if not ref:
            return None
        url = ref if re.match(r'https?://', ref) else base_url + '/export-data/' + urllib.parse.quote(ref)
        opts = {'format': 'tsv' if path.lower().endswith('.tsv') else 'csv'}
        if geom:
            opts['geom'] = geom
        else:
            opts['lon'] = lon
            opts['lat'] = lat
        if subset:
            opts['where'] = subset
        return 'duckdb', url, opts

    if re.match(r'https?://', src) or src.startswith('/vsicurl/'):
        url = src.replace('/vsicurl/', '')
        low = url.split('?')[0].lower()
        kind, ext = None, None
        for e, k in (('.geojson', 'geojson'), ('.json', 'geojson'),
                     ('.parquet', 'parquet'), ('.fgb', 'flatgeobuf'),
                     ('.csv', 'duckdb'), ('.tsv', 'duckdb')):
            if low.endswith(e):
                kind, ext = k, e
                break
        if not kind:
            return None
        opts = {}
        if kind == 'duckdb':
            opts['format'] = 'tsv' if ext == '.tsv' else 'csv'
        if subset and kind == 'duckdb':
            opts['where'] = subset
        return kind, url, opts

    src_path = _source_path(layer)
    if not src_path:
        return None
    ext = os.path.splitext(src_path)[1].lower()
    if ext in _DUCKDB_TEXT_EXTS:
        geom, lon, lat = _csv_geom_hints(src_path)
        if not geom and not (lon and lat):
            return None
        opts = {'format': 'tsv' if ext == '.tsv' else 'csv'}
        if geom:
            opts['geom'] = geom
        else:
            opts['lon'] = lon
            opts['lat'] = lat
        if subset:
            opts['where'] = subset
        ref = _copy_to_data(src_path, data_dir, slug, copied)
        return 'duckdb', base_url + '/export-data/' + urllib.parse.quote(ref), opts
    kind = {'.geojson': 'geojson', '.json': 'geojson',
            '.parquet': 'parquet', '.fgb': 'flatgeobuf'}.get(ext)
    if not kind:
        return None
    geojson_spec = ext in ('.geojson', '.json')
    if not geojson_spec and not _geo_equiv_crs(layer):
        return None
    ref = _copy_to_data(src_path, data_dir, slug, copied)
    return kind, base_url + '/export-data/' + urllib.parse.quote(ref), {}


def _write_reearth_txt(iface, out_dir, port, tree, visible_only,
                       hidden_as_off, native_formats, data_dir, copied,
                       used_names, errors, warnings):
    """Re:Earth geo_suite の inspector テキスト(reearth.txt)を生成する。

    - ベクター: ネイティブ参照可能なら geojson:/parquet:/flatgeobuf:/
      duckdb: 行、それ以外(gpkg含む)は GeoJSON 変換して geojson: 行。
      URL は http://localhost:<port>/export-data/<DATA相対> の絶対参照。
    - XYZ: xyz:/base: 行(.kasc と同じ構文を geo_suite が解釈)。
    - 3D Tiles: 3dtiles: 行(ローカルは DATA/ 複製 + /export-data URL)。
    - cam: 行(.kasc と同じ)。
    """
    from qgis.core import QgsVectorLayer
    base_url = 'http://localhost:{0}'.format(port)
    lines = ['# Exported from QGIS geo_webview -> Re:Earth geo_suite']
    cam = _camera_line(iface)

    last_xyz = None
    for layer, _g, vis in tree:
        if vis and _xyz_layer_info(layer):
            last_xyz = id(layer)
    # base: は geo_suite 側が先頭解釈のため後付けせず先に記録
    base_line = None
    body = []

    for layer, groups, visible in tree:
        title = '/'.join(
            [_kasc_escape(g) for g in groups if g] +
            [_kasc_escape(layer.name())])
        if not visible:
            if hidden_as_off:
                vis_flag = 'off'
            elif not visible_only:
                vis_flag = 'on'
            else:
                continue
        else:
            vis_flag = 'on'

        if isinstance(layer, QgsVectorLayer):
            try:
                from qgis.core import QgsWkbTypes
                if layer.wkbType() == QgsWkbTypes.NoGeometry:
                    continue
            except Exception:  # nosec B110  # 設計上の許容
                pass
            slug = _slugify(layer.name() or 'layer', used_names)
            style_opt = ''
            try:
                qml_path = os.path.join(data_dir, slug + '.qml')
                _export_qml(layer, qml_path)
                style_opt = ' | style={0}/export-data/{1}'.format(
                    base_url, urllib.parse.quote('DATA/{0}.qml'.format(slug)))
            except Exception as e:
                errors.append('{0}: reearth qml {1}'.format(layer.name(), e))

            native = None
            if native_formats and not _has_unusable_subset(layer):
                native = _reearth_native(layer, slug, data_dir, copied,
                                         base_url)
            if native:
                kind, url, opts = native
                line = '{0}: {1} | {2} | {3}'.format(
                    kind, title, _kasc_escape(url), vis_flag)
                for key, val in opts.items():
                    line += ' | {0}={1}'.format(key, _kasc_escape(val))
                line += style_opt
                attr = _attribution(layer)
                if attr:
                    line += ' | attr={0}'.format(_kasc_escape(attr))
                body.append(line)
                continue
            gj_path = os.path.join(data_dir, slug + '.geojson')
            try:
                _export_geojson(layer, gj_path)
            except Exception as e:
                errors.append('{0}: reearth geojson {1}'.format(
                    layer.name(), e))
                continue
            body.append('geojson: {0} | {1}/export-data/{2} | {3}{4}'.format(
                title, base_url,
                urllib.parse.quote('DATA/{0}.geojson'.format(slug)),
                vis_flag, style_opt))
        else:
            if _is_tiled_scene(layer):
                slug = _slugify(layer.name() or 'scene', used_names)
                ref = _tiledscene_ref(layer, slug, data_dir, copied,
                                      warnings)
                if ref:
                    url = (ref if re.match(r'https?://', ref)
                           else base_url + '/export-data/' +
                           urllib.parse.quote(ref))
                    body.append('3dtiles: {0} | {1} | {2}'.format(
                        title, _kasc_escape(url), vis_flag))
                continue
            xyz = _xyz_layer_info(layer)
            if xyz:
                url, zmin, zmax = xyz
                if not re.match(r'https?://', url):
                    slug = _slugify(layer.name() or 'tiles', used_names)
                    ref = _local_xyz_template(url, slug, data_dir, copied,
                                              warnings)
                    if not ref:
                        continue
                    url = base_url + '/export-data/' + urllib.parse.quote(
                        ref, safe='/{}')
                line = 'xyz: {0} | {1} | {2}'.format(
                    title, _kasc_escape(url), vis_flag)
                if zmax is not None:
                    line += ' | maxZoom={0}'.format(zmax)
                if zmin is not None:
                    line += ' | minZoom={0}'.format(zmin)
                if visible and id(layer) == last_xyz:
                    line = 'base' + line[len('xyz'):]
                    base_line = line
                else:
                    body.append(line)
            else:
                continue  # 対応外は inspector に出さない

    if base_line:
        lines.append(base_line)
    if cam:
        lines.append(cam)
    lines.extend(body)
    path = os.path.join(out_dir, 'reearth.txt')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    return path


def _http_json(url, payload=None, timeout=2.0, method=None):
    """小さなJSON HTTP呼び出し。payload無しはGET。"""
    if urllib.parse.urlparse(url).scheme not in ('http', 'https'):
        raise ValueError('unsupported URL scheme: {0}'.format(url))
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method=method)
    with urllib.request.urlopen(req, timeout=timeout) as res:  # nosec B310  # 直上でhttp/httpsスキームを検証済み
        body = res.read(65536)
    return json.loads(body.decode('utf-8'))


def detect_kasugai(port=None):
    """KASUGAIローカルサーバが稼働していればcapabilitiesを返す。"""
    port = int(port or get_kasugai_port())
    try:
        caps = _http_json(
            'http://localhost:{0}/api/capabilities'.format(port),
            timeout=1.5)
        if isinstance(caps, dict):
            caps['_port'] = port
            return caps
    except Exception:  # nosec B110  # 設計上の許容
        pass
    return None


def build_kasugai_url(project_id, engine=None, port=None):
    """KASUGAI Canvas のプロジェクトURLを構築する。

    engine 指定時は ``/<engine>/?project=<id>`` 形式
    (cesium/maplibre/openlayers/leaflet の実パスを直接指す。
    web/index.html の ?engine= リダイレクトに依存しないため、
    旧バージョンの Canvas でも確実にそのエンジンが開く)。
    engine=None/無効値は既定(cesium)の ``/?project=<id>``。
    """
    port = int(port or get_kasugai_port())
    base = 'http://localhost:{0}'.format(port)
    e = normalize_engine(engine)
    if e:
        base += '/{0}/'.format(e)
    return '{0}?project={1}'.format(
        base, urllib.parse.quote(str(project_id)))


def register_kasugai_project(kasc_path, port=None, engine=None):
    """POST /api/projects/register で.kascを外部プロジェクト登録する。

    戻り値: {"ok":True,"id":...,"url":...} または {"ok":False,"error":...}
    engine 指定時は url が /<engine>/?project=<id> 形式になる。
    """
    port = int(port or get_kasugai_port())
    try:
        res = _http_json(
            'http://localhost:{0}/api/projects/register'.format(port),
            payload={'path': os.path.abspath(kasc_path)}, timeout=4.0)
        pid = res.get('id')
        if res.get('ok') and pid:
            return {'ok': True, 'id': pid,
                    'url': build_kasugai_url(pid, engine, port)}
        return {'ok': False, 'error': str(res)}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def kasugai_command(name, args=None, port=None):
    """POST /api/command でチャットツールをキューイング(ベストエフォート)。"""
    port = int(port or get_kasugai_port())
    try:
        res = _http_json(
            'http://localhost:{0}/api/command'.format(port),
            payload={'name': name, 'args': args or {}}, timeout=4.0)
        return {'ok': bool(res.get('ok')), 'response': res}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def find_kasugai_exe():
    """起動可能な kasugai_canvas.exe のパスを返す（見つからなければ None）。

    detect_kasugai_install_dir()（設定→レジストリ）で特定した
    インストール先の ``<dir>/`` と ``<dir>/server/`` を見る。
    """
    install = detect_kasugai_install_dir()
    if not install:
        return None
    for cand in (os.path.join(install, KASUGAI_EXE_NAME),
                 os.path.join(install, 'server', KASUGAI_EXE_NAME)):
        if os.path.isfile(cand):
            return cand
    return None


def launch_kasugai(kasc_path=None, open_browser=False):
    """kasugai_canvas.exe を起動する。起動要求に成功すれば True。

    open_browser=False(既定)では ``--no-browser`` でサーバーのみ起動し、
    ブラウザは呼び出し側がエンジン付きURLで開く。open_browser=True または
    .kasc パス指定でのみ exe 既定挙動(ブラウザ自動起動)を利用する。
    """
    exe = find_kasugai_exe()
    if not exe:
        return False
    args = [exe]
    if not open_browser:
        args.append('--no-browser')
    if kasc_path:
        args.append(os.path.abspath(kasc_path))
    try:
        subprocess.Popen(  # nosec B603  # 固定exe・シェル非経由
            args, cwd=os.path.dirname(exe))
        return True
    except Exception as e:
        print(f'⚠️ KASUGAI launch failed: {e}')
        return False


def wait_for_kasugai(timeout=12.0, interval=0.3, pump_events=True):
    """起動直後のローカルサーバ応答を待つ。応答があれば capabilities。

    pump_events=True のとき待機中に Qt イベントを回して UI を固めない
    （GUI スレッドからの呼び出し用）。HTTP ハンドラ等の別スレッドでは
    False を指定すること。
    """
    deadline = time.time() + timeout
    while True:
        caps = detect_kasugai()
        if caps or time.time() >= deadline:
            return caps
        if pump_events:
            try:
                from qgis.PyQt.QtWidgets import QApplication
                app = QApplication.instance()
                if app is not None:
                    app.processEvents()
            except Exception:  # nosec B110  # 設計上の許容
                pass
        time.sleep(interval)


def open_kasc_with_association(kasc_path):
    """.kasc ファイル関連付け経由で Canvas 起動を要求する（Windows）。

    インストーラが ``.kasc → kasugai_canvas.exe --open-browser %1`` を
    登録済みなら起動できる。この経路は既定エンジンでブラウザが開く。
    起動要求ができれば True（起動完了は保証しない）。
    """
    if not kasc_path or not hasattr(os, 'startfile'):
        return False
    try:
        os.startfile(os.path.abspath(kasc_path))  # nosec B606
        return True
    except OSError:
        return False


def ensure_kasugai_running(kasc_path=None, timeout=12.0,
                           pump_events=True):
    """KASUGAI Canvas ローカルサーバを使える状態にして capabilities を返す。

    1. 既に稼働中 → そのまま返す
    2. インストール済み exe を発見 → ``--no-browser`` で起動して待機
       （ブラウザは呼び出し側がエンジン付きURLで開く）
    3. exe 不明・未インストール → kasc_path をファイル関連付けで開いて待機
       （この経路は既定エンジンのブラウザが exe 側で開かれる）

    戻り値は ``(capabilities or None, opened_default_browser)``。
    第2戻り値が True のとき、関連付け起動により既定エンジンのタブが
    既に開かれている可能性が高い（二重オープン防止に利用）。
    """
    caps = detect_kasugai()
    if caps:
        return caps, False
    if launch_kasugai():
        caps = wait_for_kasugai(
            timeout=timeout, pump_events=pump_events)
        if caps:
            return caps, False
    if open_kasc_with_association(kasc_path):
        caps = wait_for_kasugai(
            timeout=timeout, pump_events=pump_events)
        return caps, True
    return None, False


# ---- 自動インストール（配布ZIPのダウンロード・展開） ----

# 公開チャンネル(main)の配布物を参照する
KASUGAI_LATEST_JSON_URL = (
    'https://raw.githubusercontent.com/yamamoto-ryuzo/kasugai_canvas'
    '/main/download/latest.json')
KASUGAI_ZIP_FALLBACK_URL = (
    'https://raw.githubusercontent.com/yamamoto-ryuzo/kasugai_canvas'
    '/main/download/kasugai_canvas.zip')


def kasugai_download_url():
    """latest.json から配布ZIPのURLを返す（取得失敗時は既定URL）。"""
    try:
        meta = _http_json(KASUGAI_LATEST_JSON_URL, timeout=5.0)
        url = ((meta.get('platforms') or {})
               .get('windows-x86_64') or {}).get('url')
        if url and str(url).startswith(('https://', 'http://')):
            return url
    except Exception:  # nosec B110  # 設計上の許容
        pass
    return KASUGAI_ZIP_FALLBACK_URL


def default_install_dir():
    r"""既定インストール先。インストーラ既定の C:\kasugai\kasugai_canvas
    を優先し、作成できなければ %LOCALAPPDATA%\kasugai_canvas。"""
    if os.name == 'nt':
        cand = r'C:\kasugai\kasugai_canvas'
        try:
            os.makedirs(cand, exist_ok=True)
            return cand
        except OSError:
            pass
    import tempfile
    base = os.environ.get('LOCALAPPDATA') or tempfile.gettempdir()
    return os.path.join(base, 'kasugai_canvas')


def _safe_extractall(zf, dest_dir):
    """zip-slip 対策付き extractall。"""
    dest = os.path.abspath(dest_dir)
    for member in zf.namelist():
        target = os.path.abspath(os.path.join(dest, member))
        if not (target == dest or target.startswith(dest + os.sep)):
            raise RuntimeError('unsafe path in archive: {0}'.format(member))
    zf.extractall(dest)


def install_kasugai(dest_dir=None):
    """KASUGAI Canvas の配布ZIPをダウンロード・展開してインストール先を返す。

    dest_dir 既定は default_install_dir()。成功時は
    ``kasugai_install_path`` 設定へ自動登録する。
    失敗時は例外を送出（呼び出し側でキャッチして通知する）。
    ブロッキングするため GUI スレッドではタスク経由で呼ぶこと。
    """
    import tempfile
    import zipfile
    dest_dir = os.path.abspath(dest_dir or default_install_dir())
    url = kasugai_download_url()
    fd, tmp = tempfile.mkstemp(suffix='.zip', prefix='kasugai_canvas_')
    os.close(fd)
    try:
        req = urllib.request.Request(
            url, headers={'User-Agent': 'geo_webview'})
        with urllib.request.urlopen(req, timeout=300) as res, \
                open(tmp, 'wb') as out:  # nosec B310  # https固定URL
            shutil.copyfileobj(res, out)
        os.makedirs(dest_dir, exist_ok=True)
        with zipfile.ZipFile(tmp) as zf:
            _safe_extractall(zf, dest_dir)
    finally:
        try:
            os.remove(tmp)
        except OSError:  # nosec B110  # 設計上の許容
            pass
    exe = os.path.join(dest_dir, KASUGAI_EXE_NAME)
    if not os.path.isfile(exe):
        raise RuntimeError(
            'kasugai_canvas.exe not found in downloaded archive')
    try:
        _qsettings().setValue('kasugai_install_path', dest_dir)
    except Exception:  # nosec B110  # 設計上の許容
        pass
    return dest_dir
