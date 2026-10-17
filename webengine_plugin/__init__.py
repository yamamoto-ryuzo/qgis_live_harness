import os
import traceback


def _log(msg):
    # 配置形態(junction/copy)に依存しないよう、環境変数で出力先を指定可能にする。
    # 未指定時はテンポラリディレクトリに書く。
    log = os.environ.get(
        "WEBENGINE_LOG_PATH",
        os.path.join(os.environ.get("TEMP", "/tmp"), "webengine_plugin_load.log"),
    )
    try:
        os.makedirs(os.path.dirname(log), exist_ok=True)
        with open(log, "a", encoding="utf-8") as f:
            f.write(str(msg) + "\n")
    except Exception:
        pass


def classFactory(iface):
    try:
        from .main_plugin import WebEnginePlugin
    except Exception:
        _log("import main_plugin failed:\n" + traceback.format_exc())
        raise
    _log("classFactory ok")
    return WebEnginePlugin(iface)
