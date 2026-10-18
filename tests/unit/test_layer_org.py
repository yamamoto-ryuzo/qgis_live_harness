"""layer_org.py のテスト。stdlibのみで動くため実QGIS不要。

プロファイル解決・ルールマッチ・テンプレート置換・dry実行を検証する
(QGIS依存のツリー操作はdry=Trueで回避)。
"""

import json
import os

import pytest

from qgis_live_driver import layer_org


class _FakeLayer:
    """layer_attrs() が要求する最小限のQGISレイヤもどき。"""

    def __init__(self, name, ltype=1, provider="gdal", source=""):
        self._name = name
        self._ltype = ltype
        self._provider = provider
        self._source = source

    def name(self):
        return self._name

    def providerType(self):
        return self._provider

    def type(self):
        return self._ltype

    def source(self):
        return self._source


# ---- プロファイル解決 ----

def test_bundled_default_profile():
    ids = [p["id"] for p in layer_org.list_profiles()]
    assert "default" in ids
    prof, path = layer_org.load_profile("default")
    assert prof is not None
    assert prof["id"] == "default"
    assert isinstance(prof.get("rules"), list)
    assert os.path.isfile(path)


def test_user_profile_overrides(tmp_path, monkeypatch):
    """QGIS_LIVE_REGISTRY配下の同名ユーザファイルが同梱を上書きする。"""
    reg = tmp_path / "reg"
    udir = reg / "layer_org"
    udir.mkdir(parents=True)
    (udir / "default.json").write_text(
        json.dumps({"name": "user-default", "root": "R",
                    "rules": [{"match": {"layer_type": "raster"},
                               "group": "G"}]}),
        encoding="utf-8")
    monkeypatch.setenv("QGIS_LIVE_REGISTRY", str(reg))
    prof, path = layer_org.load_profile("default")
    assert prof["name"] == "user-default"
    assert prof["root"] == "R"
    assert str(path).startswith(str(reg))


def test_missing_profile():
    prof, path = layer_org.load_profile("no-such-profile-xyz")
    assert (prof, path) == (None, None)


# ---- レイヤ属性抽出 ----

def test_layer_attrs_from_source_ext():
    lyr = _FakeLayer("dem", source="C:/data/foo.tif?x=1")
    a = layer_org.layer_attrs(lyr, {"format": "GTiff"})
    assert a["ext"] == "tif"
    assert a["format"] == "gtiff"
    assert a["layer_type"] == "raster"
    assert a["geom"] == "none"


def test_layer_attrs_uri_has_no_ext():
    lyr = _FakeLayer("wms", provider="wms",
                     source="crs=EPSG:4326&url=http://x/wms")
    a = layer_org.layer_attrs(lyr, {"format": "WMS"})
    assert a["ext"] == ""
    assert a["format"] == "wms"
    assert a["provider"] == "wms"


# ---- ルールマッチ ----

_RULES = [
    {"match": {"format": ["wms", "xyz"]}, "group": "Services"},
    {"match": {"layer_type": "vector", "geom": "point"},
     "group": "Vector/Points"},
    {"match": {"ext": ["tif"]}, "group": "Raster"},
]


def _attrs(**kw):
    base = {"ctx": {}, "name": "n", "provider": "", "layer_type": "raster",
            "geom": "none", "source": "", "ext": "", "format": "",
            "url": ""}
    base.update(kw)
    return base


def test_match_first_hit_wins():
    idx, rule = layer_org.match_rule(_RULES, _attrs(format="wms"))
    assert idx == 0
    idx, rule = layer_org.match_rule(
        _RULES, _attrs(format="tif", ext="tif"))
    assert idx == 2  # format=tifでもext=tifで3番目にヒット


def test_match_and_conditions():
    attrs = _attrs(layer_type="vector", geom="point")
    idx, rule = layer_org.match_rule(_RULES, attrs)
    assert idx == 1
    # geomが違えばそのルールは外れる
    idx, rule = layer_org.match_rule(
        _RULES, _attrs(layer_type="vector", geom="polygon"))
    assert idx is None


def test_match_name_dataset_url_regex():
    rules = [
        {"match": {"name_re": "人口"}, "group": "Stats"},
        {"match": {"dataset_re": "土地"}, "group": "Land"},
        {"match": {"url_re": r"\.zip$"}, "group": "Zip"},
    ]
    idx, _ = layer_org.match_rule(rules, _attrs(name="人口メッシュ"))
    assert idx == 0
    idx, _ = layer_org.match_rule(
        rules, _attrs(ctx={"resource": "人口データ"}))
    assert idx == 0  # resource名もname_re対象
    idx, _ = layer_org.match_rule(
        rules, _attrs(ctx={"dataset": "土地基本図"}))
    assert idx == 1
    idx, _ = layer_org.match_rule(rules, _attrs(url="http://x/a.zip"))
    assert idx == 2
    idx, _ = layer_org.match_rule(rules, _attrs())
    assert idx is None


def test_match_plugin_and_tags():
    rules = [{"match": {"plugin": "geo_import", "tags": "stats"},
              "group": "G"}]
    idx, _ = layer_org.match_rule(
        rules, _attrs(ctx={"plugin_id": "geo_import", "tags": ["Stats"]}))
    assert idx == 0
    idx, _ = layer_org.match_rule(rules, _attrs(ctx={"plugin_id": "other"}))
    assert idx is None


def test_unknown_match_key_fails():
    rules = [{"match": {"nonsense": "x"}, "group": "G"}]
    idx, _ = layer_org.match_rule(rules, _attrs())
    assert idx is None


# ---- テンプレート ----

def test_render_template():
    attrs = _attrs(name="L", ext="shp", format="shp",
                   ctx={"dataset": "D", "resource": "R",
                        "plugin_id": "geo_import"})
    out = layer_org.render_template(
        "{dataset} - {resource} ({format})", attrs)
    assert out == "D - R (shp)"
    # 未定義トークンはそのまま残す
    assert "{zzz}" in layer_org.render_template("{zzz}", attrs)


# ---- dry実行(QGIS不要なパス) ----

def test_place_dry_reports_group(tmp_path, monkeypatch):
    reg = tmp_path / "reg"
    udir = reg / "layer_org"
    udir.mkdir(parents=True)
    (udir / "prof.json").write_text(
        json.dumps({"root": "Imported",
                    "rules": [{"match": {"layer_type": "raster"},
                               "group": "Raster",
                               "rename": "{name}-r"}],
                    "fallback": "Misc"}),
        encoding="utf-8")
    monkeypatch.setenv("QGIS_LIVE_REGISTRY", str(reg))
    prof, _ = layer_org.load_profile("prof")
    org = layer_org.LayerOrganizer()

    entry = org.place(_FakeLayer("dem", source="a.tif"), {}, prof, dry=True)
    assert entry["action"] == "dry"
    assert entry["group"] == "Imported/Raster"
    assert entry["renamed"] == "dem-r"

    # ルール不一致→fallback
    entry = org.place(_FakeLayer("v", ltype=0, provider="ogr"), {},
                      prof, dry=True)
    assert entry["group"] == "Imported/Misc"
    assert entry["rule"] == "fallback"


def test_place_disabled_noop():
    org = layer_org.LayerOrganizer()
    entry = org.place(_FakeLayer("x"), {}, prof=None, dry=True)
    assert entry["action"] == "disabled"
