# QGISプロファイルの startup.py から import して実行する想定。
# (プロファイル)/python/startup.py がQGIS起動時に必ず実行される。
# プラグイン読み込み完了を待つため QTimer で遅延実行する。
# 結果は <repo>/test-results/open_plugin_dialog.log に記録される。

import json
import os
import traceback

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# QGIS上のプラグインID(deploy先ディレクトリ名)はplugin.config.jsonで管理
try:
    with open(os.path.join(_REPO, "plugin.config.json"), encoding="utf-8") as f:
        _ids = json.load(f)["id"]
        PLUGIN_ID = _ids[0] if isinstance(_ids, list) else _ids
except Exception:
    PLUGIN_ID = "geo_search"

LOG = os.path.join(_REPO, "test-results", "open_plugin_dialog.log")


def _w(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(str(msg) + "\n")
    print(f"[{PLUGIN_ID} autostart]", msg)


def open_dialog():
    from qgis.utils import loadPlugin, plugins, startPlugin

    _w("loaded plugins: " + ", ".join(sorted(plugins.keys())))

    plugin = plugins.get(PLUGIN_ID)
    if plugin is None:
        _w(f"{PLUGIN_ID} not loaded; trying loadPlugin/startPlugin")
        try:
            _w(f"loadPlugin -> {loadPlugin(PLUGIN_ID)}")
            startPlugin(PLUGIN_ID)
        except Exception:
            _w("loadPlugin error:\n" + traceback.format_exc())
        plugin = plugins.get(PLUGIN_ID)

    if plugin is None:
        _w("FAILED: plugin still not loaded")
        return
    try:
        plugin.open_dialog()
        _w("dialog opened")
    except Exception:
        _w("open_dialog error:\n" + traceback.format_exc())


def schedule(delay_ms=3000):
    from qgis.PyQt.QtCore import QTimer

    QTimer.singleShot(delay_ms, open_dialog)
    _w(f"scheduled open_dialog in {delay_ms}ms")


# runpy/qgis --code どちらで実行されても動くようモジュール直下で呼ぶ
schedule()
