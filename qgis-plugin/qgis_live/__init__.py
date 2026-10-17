import os
import traceback


def _log(msg):
    log = os.environ.get(
        "WEBENGINE_LOG_PATH",
        os.path.join(os.environ.get("TEMP", "/tmp"), "plugin_load.log"),
    )
    try:
        os.makedirs(os.path.dirname(log), exist_ok=True)
        with open(log, "a", encoding="utf-8") as f:
            f.write(str(msg) + "\n")
    except Exception:
        pass


class QgisLivePlugin:
    """UIを持たない制御専用プラグイン。

    WEBENGINE_LIVE_DIR 設定時のみLiveDriverを起動し、
    pyeval/キャンバススクショをファイルプロトコルで公開する。
    未設定なら何もしない(通常プラグインとして無害)。
    """

    def __init__(self, iface):
        self.iface = iface
        self.driver = None

    def initGui(self):
        live_base = os.environ.get("WEBENGINE_LIVE_DIR")
        _log(f"qgis_live initGui: live_base={live_base!r}")
        if not live_base:
            return
        live_dir = os.path.join(live_base, f"qgis-{os.getpid()}", __package__)
        try:
            from .live_driver import LiveDriver
            self.driver = LiveDriver(live_dir, iface=self.iface)
            _log(f"qgis_live LiveDriver active: {live_dir}")
        except Exception:
            _log("qgis_live LiveDriver failed:\n" + traceback.format_exc())

    def unload(self):
        if self.driver is not None:
            self.driver.stop()
            self.driver = None


def classFactory(iface):
    return QgisLivePlugin(iface)
