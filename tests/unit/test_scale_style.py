"""scale_style.py のテスト。stdlibのみで動くため実QGIS不要。

プロファイル解決・縮尺帯ルックアップ・カテゴリマッチ・
mm↔m 変換を検証する(QGIS依存のレンダラ操作は対象外)。
"""

import json

from geo_driver import scale_style
from geo_driver.layer_org import layer_attrs


class _FakeLayer:
    """layer_attrs() が要求する最小限のQGISレイヤもどき。"""

    def __init__(self, name, ltype=0, provider="ogr", source=""):
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
    ids = [p["id"] for p in scale_style.list_profiles()]
    assert "default" in ids
    prof, path = scale_style.load_profile("default")
    assert prof is not None
    assert prof["id"] == "default"
    assert isinstance(prof.get("scale_bands"), list)
    assert isinstance(prof.get("categories"), list)


def test_user_profile_overrides(tmp_path, monkeypatch):
    """QGIS_LIVE_REGISTRY配下の同名ユーザファイルが同梱を上書きする。"""
    reg = tmp_path / "reg"
    udir = reg / "scale_style"
    udir.mkdir(parents=True)
    (udir / "default.json").write_text(
        json.dumps({"name": "user-default",
                    "scale_bands": [{"max": None, "factor": 2.0}],
                    "categories": [{"key": "default", "match": {},
                                    "base_mm": 9.9}]}),
        encoding="utf-8")
    monkeypatch.setenv("QGIS_LIVE_REGISTRY", str(reg))
    prof, path = scale_style.load_profile("default")
    assert prof["name"] == "user-default"
    assert prof["categories"][0]["base_mm"] == 9.9
    assert str(path).startswith(str(reg))


def test_missing_profile():
    prof, path = scale_style.load_profile("no-such-profile-xyz")
    assert (prof, path) == (None, None)


# ---- 縮尺帯ルックアップ ----

def _default():
    prof, _ = scale_style.load_profile("default")
    return prof


def test_band_for_scale_bands():
    prof = _default()
    assert scale_style.band_for_scale(prof, 1000)["max"] == 2500
    assert scale_style.band_for_scale(prof, 2499.9)["max"] == 2500
    # 上限は排他: 2500ちょうどは次の帯
    assert scale_style.band_for_scale(prof, 2500)["max"] == 5000
    assert scale_style.band_for_scale(prof, 20000)["max"] == 25000
    # 最大帯を超えると末尾(max=None)
    last = scale_style.band_for_scale(prof, 99999999)
    assert last["max"] is None
    # scale不明 → factor=1.0 の基準帯
    assert scale_style.band_for_scale(prof, None)["factor"] == 1.0


# ---- カテゴリマッチ ----

def test_match_category_by_name():
    prof = _default()
    lyr = _FakeLayer("国道17号線")
    a = layer_attrs(lyr)
    cat = scale_style.match_category(prof, a)
    assert cat is not None
    assert cat["key"] == "road_major"


def test_match_category_geom_fallback():
    prof = _default()
    lyr = _FakeLayer("なにかの線")
    # geom は FakeLayer では wkbType が無いので "none" →
    # line/polygon カテゴリにはマッチせず default へ
    cat = scale_style.match_category(prof, layer_attrs(lyr))
    assert cat["key"] == "default"


def test_match_category_river():
    prof = _default()
    lyr = _FakeLayer("河川中心線_水系")
    cat = scale_style.match_category(prof, layer_attrs(lyr))
    assert cat["key"] == "river"


# ---- 推奨幅 ----

def test_suggested_mm_scales_with_factor():
    prof = _default()
    cat = {"key": "road", "base_mm": 0.4}
    w_detail, band_d = scale_style.suggested_mm(prof, cat, 2000)
    w_ref, band_r = scale_style.suggested_mm(prof, cat, 20000)
    w_small, band_s = scale_style.suggested_mm(prof, cat, 300000)
    # 詳細側は太く、広域側は細く
    assert w_detail > w_ref > w_small
    assert w_ref == 0.4  # factor=1.0 の基準帯
    assert band_d["factor"] == 1.5
    assert band_s["factor"] == 0.4


def test_suggested_mm_clamps():
    prof = {"scale_bands": [{"max": None, "factor": 100.0}]}
    w, _ = scale_style.suggested_mm(prof, {"base_mm": 1.0}, 500)
    assert w == 10.0  # 上限clamp


def test_mm_to_meters():
    assert scale_style.mm_to_meters(0.5, 2500) == 1.25
    assert scale_style.mm_to_meters(0.3, 25000) == 7.5
    assert scale_style.mm_to_meters(0.3, None) is None
