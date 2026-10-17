import json
import os
import time
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


def _registry_dir():
    # spawnされる側(MCPクライアントのshim等)が環境変数を持たないため、
    # 検出情報は固定パス ~/.qgis-live/ に書き出す
    return os.environ.get(
        "QGIS_LIVE_REGISTRY",
        os.path.join(os.path.expanduser("~"), ".qgis-live"),
    )


class QgisLivePlugin:
    """UIを持たない制御専用プラグイン。

    WEBENGINE_LIVE_DIR 設定時のみLiveDriverを起動し、
    pyeval/キャンバススクショを公開する。
    未設定なら何もしない(通常プラグインとして無害)。

    公開面:
      - ファイルJSONL (commands.jsonl/results.jsonl) — 言語非依存の基底
      - HTTP 127.0.0.1:<auto port> (/mcp = MCP Streamable HTTP, /api/* = REST)
      - ~/.qgis-live/<pid>-qgis_live_driver.json — 上記への接続情報(自動検出用)
    """

    def __init__(self, iface):
        self.iface = iface
        self.driver = None
        self._http = None
        self._reg_path = None

    def initGui(self):
        live_base = os.environ.get("WEBENGINE_LIVE_DIR")
        _log(f"qgis_live_driver initGui: live_base={live_base!r}")
        if not live_base:
            return
        live_dir = os.path.join(live_base, f"qgis-{os.getpid()}", __package__)
        try:
            from .live_driver import LiveDriver
            self.driver = LiveDriver(live_dir, iface=self.iface)
            _log(f"qgis_live_driver LiveDriver active: {live_dir}")
        except Exception:
            _log("qgis_live_driver LiveDriver failed:\n" + traceback.format_exc())
            return

        try:
            from .mcp_http import start_http
            self._http, port = start_http(self.driver)
            self.driver.http_port = port
            _log(f"qgis_live_driver HTTP API: http://127.0.0.1:{port}/")
        except Exception:
            _log("qgis_live_driver HTTP failed:\n" + traceback.format_exc())
            port = None

        try:
            reg_dir = _registry_dir()
            os.makedirs(reg_dir, exist_ok=True)
            self._reg_path = os.path.join(
                reg_dir, f"{os.getpid()}-{__package__}.json")
            with open(self._reg_path, "w", encoding="utf-8") as f:
                json.dump({
                    "pid": os.getpid(),
                    "plugin_id": __package__,
                    "live_dir": live_dir,
                    "http_port": port,
                    "started": time.time(),
                }, f)
        except Exception:
            _log("qgis_live_driver registry write failed:\n" + traceback.format_exc())

    def unload(self):
        if self._http is not None:
            try:
                self._http.shutdown()
            except Exception:
                pass
            self._http = None
        if self.driver is not None:
            self.driver.stop()
            self.driver = None
        if self._reg_path is not None:
            try:
                os.remove(self._reg_path)
            except Exception:
                pass
            self._reg_path = None


def classFactory(iface):
    return QgisLivePlugin(iface)
