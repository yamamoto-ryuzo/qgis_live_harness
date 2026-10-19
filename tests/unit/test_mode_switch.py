"""mode_switch.py の deploy_state 優先度テスト。stdlibのみで実QGIS不要。

モード判定は配置実態(junction/dir)優先で、宣言markerは未配置時の
補完と乖離検出(diverged)にのみ使われることを検証する。
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

from qgis_live_driver import mode_switch

REPO = Path(__file__).resolve().parents[2]
CTRL = mode_switch.CTRL_ID


def _profile(tmp_path):
    p = tmp_path / "profile"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _own_file(profile):
    """deploy_state が要求する own_file を返す(存在不要。パス計算のみ)。"""
    return str(profile / "python" / "plugins" / CTRL / "x.py")


def _write_marker(profile, mode=None):
    """宣言markerを書く。repo=実repoで管理対象idを plugin.config.json から
    解決させる(mode省略時は宣言無しのmarker)。"""
    m = {"profile": "test", "repo": str(REPO)}
    if mode:
        m["mode"] = mode
    (profile / "qgis_live_mode.json").write_text(
        json.dumps(m), encoding="utf-8")


def _mk_dir(profile, plugin_id):
    (profile / "python" / "plugins" / plugin_id).mkdir(parents=True)


def _mk_junction(profile, plugin_id):
    link = profile / "python" / "plugins" / plugin_id
    link.parent.mkdir(parents=True, exist_ok=True)
    target = REPO / "qgis-plugin" / plugin_id
    try:
        os.symlink(str(target), str(link), target_is_directory=True)
        return
    except OSError:
        pass
    r = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True)
    if r.returncode != 0:
        pytest.skip("junction/symlink creation not permitted")


def test_actual_dir_beats_stale_dev_marker(tmp_path):
    """宣言=devだが実体dir配置 → 実態useが勝ち diverged。"""
    profile = _profile(tmp_path)
    _mk_dir(profile, "geo_search")
    _write_marker(profile, "dev")
    st = mode_switch.deploy_state(_own_file(profile))
    assert st["actual"] == "use"
    assert st["mode"] == "use"
    assert st["declared"] == "dev"
    assert st["diverged"] is True


def test_junction_beats_stale_use_marker(tmp_path):
    """宣言=useだがjunction配置 → 実態devが勝ち diverged。"""
    profile = _profile(tmp_path)
    _mk_junction(profile, "geo_search")
    _write_marker(profile, "use")
    st = mode_switch.deploy_state(_own_file(profile))
    assert st["actual"] == "dev"
    assert st["mode"] == "dev"
    assert st["declared"] == "use"
    assert st["diverged"] is True


def test_mixed_junction_and_dir(tmp_path):
    """junctionと実体dirの混在 → mixed。"""
    profile = _profile(tmp_path)
    _mk_junction(profile, "geo_search")
    _mk_dir(profile, "geo_webview")
    _write_marker(profile, "dev")
    st = mode_switch.deploy_state(_own_file(profile))
    assert st["actual"] == "mixed"
    assert st["mode"] == "mixed"
    assert st["diverged"] is True


def test_declared_fills_undeployed(tmp_path):
    """未配置時のみ宣言で補う(use宣言=自動deploy抑制の意図)。"""
    profile = _profile(tmp_path)
    _write_marker(profile, "use")
    st = mode_switch.deploy_state(_own_file(profile))
    assert st["actual"] == "none"
    assert st["mode"] == "use"
    assert st["diverged"] is False


def test_markerless_repo_real_dirs(tmp_path):
    """mode無しmarker(repoのみ) + 実体dir → use。宣言無しでdivergedはFalse。"""
    profile = _profile(tmp_path)
    _mk_dir(profile, "geo_search")
    _write_marker(profile)
    st = mode_switch.deploy_state(_own_file(profile))
    assert st["mode"] == "use"
    assert st["declared"] is None
    assert st["diverged"] is False


def test_no_marker_nothing_deployed(tmp_path):
    """何も無い → none。"""
    profile = _profile(tmp_path)
    st = mode_switch.deploy_state(_own_file(profile))
    assert st["mode"] == "none"
    assert st["diverged"] is False
