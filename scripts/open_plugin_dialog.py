# QGISプロファイルの startup.py から import して実行する想定。
# (プロファイル)/python/startup.py がQGIS起動時に必ず実行される。
# プラグイン読み込み完了を待つため QTimer で遅延実行する。
# 結果は <repo>/test-results/open_plugin_dialog.log に記録される。

import os
import traceback

LOG = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "test-results",
    "open_plugin_dialog.log",
)


def _w(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(str(msg) + "\n")
    print("[webengine_plugin autostart]", msg)


def open_dialog():
    from qgis.utils import loadPlugin, plugins, startPlugin

    _w("loaded plugins: " + ", ".join(sorted(plugins.keys())))

    plugin = plugins.get("webengine_plugin")
    if plugin is None:
        _w("webengine_plugin not loaded; trying loadPlugin/startPlugin")
        try:
            _w(f"loadPlugin -> {loadPlugin('webengine_plugin')}")
            startPlugin("webengine_plugin")
        except Exception:
            _w("loadPlugin error:\n" + traceback.format_exc())
        plugin = plugins.get("webengine_plugin")

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
