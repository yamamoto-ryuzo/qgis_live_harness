"""kasc_import.py のテスト。

parse_kasc/inspect_kasc は stdlib のみで動くため実QGIS不要。
QGIS依存の import_kasc(レイヤ構築)は対象外。
"""

import os

from geo_webview import kasc_import as ki


SAMPLE = """\
# comment
base: GSI/std | https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png | 出典：国土地理院 | maxZoom=18 | minZoom=2
base: none | transparent
xyz: tiles/foo | https://example.com/{z}/{x}/{y}.png | on | maxZoom=17 | opacity=0.7 | bbox=130,30,140,40 | attr=xyz出典
geojson: grp/sub/道路 | DATA/road.geojson | on | style=DATA/road.qml | minScale=25000 | maxScale=2500
gpkg: grp/筆 | DATA/fude.gpkg | on | table=parcel | where="city"='X' | attr=筆出典
geoparquet: 全件 | DATA/all.parquet | on
duckdb: 地点 | DATA/pt.csv | on | format=csv | lon=lon | lat=lat
wms: オルソ | https://example.com/wms | on | layers=ortho | styles= | format=image/jpeg
3dtiles: 建物 | https://example.com/tiles/tileset.json | on | minScale=5000
fly_geojson: Atlas: A | DATA/atlas_a.geojson | speed=10
theme: 概況図 | 道路 | 筆
group: grp/sub | collapsed
group: grp | expanded
bookmark: bookmarks.xml
cam:QGIS|35.685278|139.778045|h=3010|p=-90
title: サンプルプロジェクト
live: http://localhost:8089 | follow
terrain: 地形 | exaggeration=1.5
scene3d: 3D | skybox=on | shadows=on
light: 光 | az=180 | el=45
sql: SELECT * FROM t | foo
unknown_type: x | y
"""


def test_parse_layers_and_types():
    doc = ki.parse_kasc(SAMPLE)
    types = [it["type"] for it in doc["layers"]]
    assert types == ["xyz", "geojson", "gpkg", "geoparquet",
                     "duckdb", "wms", "3dtiles", "fly_geojson", "sql"]
    # レイヤ行でも base/theme/group/cam/title 等でもない未知行は unsupported
    unsupported_types = [it["type"] for it in doc["unsupported"]]
    assert "unknown_type" in unsupported_types
    assert "sql" in types  # sql: は layers へ入り呼出側で skipped 扱い
    # 順序保持
    idxs = [it["_idx"] for it in doc["layers"]]
    assert idxs == sorted(idxs)


def test_parse_opts_and_flags():
    doc = ki.parse_kasc(SAMPLE)
    xyz = doc["layers"][0]
    assert xyz["opts"]["maxzoom"] == "17"
    assert xyz["opts"]["opacity"] == "0.7"
    assert xyz["opts"]["bbox"] == "130,30,140,40"
    assert xyz["opts"]["attr"] == "xyz出典"  # attr= は opts へ(裸トークンは .attr)
    gj = doc["layers"][1]
    assert gj["opts"]["style"] == "DATA/road.qml"
    assert gj["opts"]["minscale"] == "25000"
    assert gj["opts"]["maxscale"] == "2500"
    gk = doc["layers"][2]
    assert gk["opts"]["table"] == "parcel"
    assert gk["opts"]["where"].startswith('"city"')
    db = doc["layers"][4]
    assert db["opts"]["lon"] == "lon" and db["opts"]["lat"] == "lat"
    wms = doc["layers"][5]
    assert wms["opts"]["layers"] == "ortho"
    assert wms["opts"]["format"] == "image/jpeg"


def test_parse_bases_modes():
    doc = ki.parse_kasc(SAMPLE)
    assert len(doc["bases"]) == 2
    assert doc["bases"][0]["opts"]["maxzoom"] == "18"
    assert doc["bases"][0]["attr"] == "出典：国土地理院"
    assert doc["bases"][1].get("mode") == "transparent"


def test_parse_meta_lines():
    doc = ki.parse_kasc(SAMPLE)
    assert doc["cams"][0]["latitude"] == 35.685278
    assert doc["cams"][0]["height"] == 3010.0
    assert doc["title"] == "サンプルプロジェクト"
    assert doc["live"]["url"] == "http://localhost:8089"
    assert doc["live"]["follow"] is True
    assert doc["terrain"]["opts"]["exaggeration"] == "1.5"
    assert doc["scene3d"]["opts"]["skybox"] == "on"
    assert doc["lights"][0]["opts"]["az"] == "180"
    assert doc["bookmarks"] == [
        {"title": None, "url": "bookmarks.xml"}]
    collapsed = {g["path"]: g["collapsed"] for g in doc["groups"]}
    assert collapsed["grp/sub"] is True
    assert collapsed["grp"] is False
    themes = doc["themes"]
    assert themes[0]["name"] == "概況図"
    assert "道路" in themes[0]["layers"]


def test_resolve_ref(tmp_path):
    assert ki.resolve_ref("DATA/x.gpkg", "/out") == \
        os.path.normpath("/out/DATA/x.gpkg")
    assert ki.resolve_ref("DATA/x.gpkg", "https://h/p/") == \
        "https://h/p/DATA/x.gpkg"
    assert ki.resolve_ref("https://a/b.geojson", "/out") == \
        "https://a/b.geojson"
    assert ki.resolve_ref("file:///c:/d/x.geojson", "/out") == \
        "c:/d/x.geojson"


def test_inspect_kasc_local(tmp_path):
    d = tmp_path / "proj"
    (d / "DATA").mkdir(parents=True)
    (d / "DATA" / "a.geojson").write_text("{}", encoding="utf-8")
    (d / "p.kasc").write_text(
        "geojson: A | DATA/a.geojson | on\n"
        "cam:QGIS|35.0|139.0|h=1000\n", encoding="utf-8")
    rep = ki.inspect_kasc(str(d / "p.kasc"))
    assert rep["ok"] is True
    assert rep["counts"]["geojson"] == 1
    assert rep["layers"][0]["ref"].endswith("a.geojson")
    assert rep["cams"][0]["height"] == 1000.0


def test_title_helpers():
    assert ki._title_leaf("a/b/c") == "c"
    assert ki._title_leaf("a//b/c") == "c"
    assert ki._title_groups("a/b/c") == ["a", "b"]
    assert ki._exclusive_groups("a/b//c") == ["b"]
    assert ki._exclusive_groups("a/b/c") == []


def test_norm_title():
    # NFKC正規化: 全角→半角・連続空白の畳込み・前後空白除去
    assert ki._norm_title("  国土数値情報  ") == "国土数値情報"
    assert ki._norm_title("ＡＢＣ　１２３") == "ABC 123"
    assert ki._norm_title("a  b") == "a b"
    assert ki._norm_title("") == ""


def test_source_key(tmp_path):
    p = tmp_path / "x.kasc"
    p.write_text("", encoding="utf-8")
    # ローカルは normcase+abspath で同一ファイルを一意に
    assert ki._source_key(str(p)) == ki._source_key(
        os.path.join(str(tmp_path), ".", "x.kasc"))
    # URL はそのまま
    assert ki._source_key("https://h/p.kasc") == "https://h/p.kasc"
