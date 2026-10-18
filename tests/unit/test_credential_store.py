"""credential_store.py のテスト。stdlibのみで動くため実QGIS不要。

QGIS_LIVE_REGISTRY をtmpに向けて実バックエンド(WindowsならDPAPI)の
往復を検証する。ファイルバックエンドは直接関数を叩く。
"""

import sys

import pytest

from qgis_live_driver import credential_store as cs


@pytest.fixture
def store_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("QGIS_LIVE_REGISTRY", str(tmp_path))
    return tmp_path


def test_roundtrip(store_dir):
    assert cs.set_secret("ai_test_api_key", "sk-secret-123")
    assert cs.get_secret("ai_test_api_key") == "sk-secret-123"
    # 日本語・空でない長い文字列も通る
    assert cs.set_secret("ai_test2", "鍵-あいうえお-✓" * 10)
    assert cs.get_secret("ai_test2") == "鍵-あいうえお-✓" * 10


def test_delete_and_empty(store_dir):
    cs.set_secret("k", "v")
    assert cs.delete_secret("k")
    assert cs.get_secret("k") is None
    # 空文字列をsetすると削除と同じ
    cs.set_secret("k2", "v2")
    assert cs.set_secret("k2", "")
    assert cs.get_secret("k2") is None


def test_missing_returns_none(store_dir):
    assert cs.get_secret("no-such-key") is None


def test_delete_nonexistent_is_ok(store_dir):
    # 存在しないキーの削除は冪等に成功(空欄保存で誤エラーにしない)
    assert cs.delete_secret("never-existed")


def test_set_failure_returns_false(store_dir, monkeypatch):
    """書込み不能な場所では set_secret が False を返す
    (パネル側はこれを受けてエラー表示し平文保存しない)。"""
    if sys.platform == "win32":
        # DPAPI暗号化自体は成功するため保存先ファイルを壊す
        def boom(_data):
            raise OSError("read-only")
        monkeypatch.setattr(cs, "_save_file", boom)
    else:
        monkeypatch.setattr(cs, "backend", lambda: "file")
        monkeypatch.setattr(cs, "_secrets_path",
                            lambda: "/nonexistent-dir/x/secrets.json")
    assert cs.set_secret("k", "v") is False


@pytest.mark.skipif(sys.platform != "win32", reason="DPAPIはWindows限定")
def test_dpapi_blob_is_encrypted(store_dir):
    """DPAPI: ファイル上の値が暗号化され平文を含まないことを確認。"""
    cs.set_secret("ai_dpapi", "PLAINTEXT-SECRET")
    import json
    raw = json.loads((store_dir / "ai-secrets.json").read_text())
    ent = raw["ai_dpapi"]
    assert ent["v"] == "dpapi"
    assert "PLAINTEXT-SECRET" not in ent["data"]
    # 別の場所(=別レジストリdir)からは同じユーザなら復号できる
    # (DPAPIはマシン+ユーザ紐付け。保存先ファイル位置には依存しない)
    assert cs.get_secret("ai_dpapi") == "PLAINTEXT-SECRET"


def test_file_backend(store_dir):
    assert cs._file_set("k", "secret")
    assert cs._file_get("k") == "secret"
    import json
    raw = json.loads((store_dir / "ai-secrets.json").read_text())
    assert raw["k"]["v"] == "plain"


def test_backend_label(store_dir):
    assert cs.backend() in ("dpapi", "keychain", "secret-tool", "file")
    assert cs.backend_label()
