import os

from qgis.PyQt.QtCore import QUrl, QTimer
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QDialog, QVBoxLayout

try:
    from qgis.PyQt.QtWebChannel import QWebChannel
    from qgis.PyQt.QtWebEngineWidgets import QWebEngineView
except ImportError:  # qgis.PyQt shim がQtWebEngine系を仲介しないQGISバージョン向け
    from PyQt6.QtWebChannel import QWebChannel
    from PyQt6.QtWebEngineWidgets import QWebEngineView

from . import _log
from .bridge import PluginBridge

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_NAME = "WebEngine Plugin"

# 設定時はロジック層(bridge.py等)とui/をdeploy済みパッケージではなく
# リポジトリ側から読む。devreloadコマンドでdeploy無しに再importできる。
DEV_SRC = os.environ.get("WEBENGINE_DEV_SRC")


def resolve_ui_dir():
    """ui/ は DEV_SRCリポジトリ > プラグイン同梱 の順で探す。"""
    candidates = []
    if DEV_SRC:
        candidates.append(
            os.path.join(DEV_SRC, "qgis-plugin", __package__, "ui"))
    candidates.append(os.path.join(PLUGIN_DIR, "ui"))
    for d in candidates:
        if os.path.isfile(os.path.join(d, "index.html")):
            return d
    raise FileNotFoundError("ui/index.html not found in: " + ", ".join(candidates))


def load_dev_bridge_class():
    """DEV_SRC内の qgis-plugin/<id>/ パッケージを別名で読み込みPluginBridgeを返す。

    deploy済みのプラグインパッケージと衝突しないよう <id>_devsrc
    としてimportする。毎回モジュールキャッシュを掃除するため、呼ぶたびに
    最新のファイル内容が反映される(bridge.py -> logic.py の相対importも追従)。
    __package__ はdeploy先ディレクトリ名(=プラグインID)と一致する。
    """
    import importlib.util
    import sys

    pkg_name = __package__ + "_devsrc"
    pkg_dir = os.path.join(DEV_SRC, "qgis-plugin", __package__)
    for k in [k for k in list(sys.modules)
              if k == pkg_name or k.startswith(pkg_name + ".")]:
        sys.modules.pop(k, None)
    spec = importlib.util.spec_from_file_location(
        pkg_name, os.path.join(pkg_dir, "__init__.py"),
        submodule_search_locations=[pkg_dir])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[pkg_name] = mod
    spec.loader.exec_module(mod)
    return importlib.import_module(pkg_name + ".bridge").PluginBridge


class WebEnginePlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None
        self.bridge = None

    def initGui(self):
        self.action = QAction(QIcon(), PLUGIN_NAME, self.iface.mainWindow())
        self.action.triggered.connect(self.open_dialog)
        self.iface.addPluginToMenu(f"&{PLUGIN_NAME}", self.action)
        self.iface.addToolBarIcon(self.action)
        _log("initGui done; WEBENGINE env=" + str(
            {k: v for k, v in os.environ.items() if k.startswith("WEBENGINE")}))
        if os.environ.get("WEBENGINE_AUTOOPEN"):
            delay = int(os.environ.get("WEBENGINE_AUTOOPEN_DELAY", "3000"))
            QTimer.singleShot(delay, self.open_dialog)
            _log(f"autoopen scheduled in {delay}ms")

    def unload(self):
        if self.action is not None:
            self.iface.removePluginMenu(f"&{PLUGIN_NAME}", self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None
        live = getattr(self, "_live", None)
        if live is not None:
            try:
                live.stop()
            except Exception:
                pass
            self._live = None
        if self.dialog is not None:
            self.dialog.deleteLater()
            self.dialog = None

    def _make_bridge(self, view):
        """DEV_SRC設定時はリポジトリ側のbridgeを読み、失敗時は同梱版にフォールバック。"""
        if DEV_SRC:
            try:
                return load_dev_bridge_class()(self.iface, parent=view)
            except Exception:
                import traceback
                _log("dev bridge load failed, fallback to bundled:\n"
                     + traceback.format_exc())
        return PluginBridge(self.iface, parent=view)

    def _dev_reload(self):
        """devreloadコマンド用: リポジトリ側bridgeを再importして返す。"""
        self.bridge = load_dev_bridge_class()(self.iface, parent=self.dialog)
        return self.bridge

    def open_dialog(self):
        if self.dialog is None:
            self.dialog = QDialog(self.iface.mainWindow())
            self.dialog.setWindowTitle(PLUGIN_NAME)
            self.dialog.resize(900, 640)
            layout = QVBoxLayout(self.dialog)
            layout.setContentsMargins(0, 0, 0, 0)

            view = QWebEngineView(self.dialog)
            self.bridge = self._make_bridge(view)
            channel = QWebChannel(view.page())
            channel.registerObject("bridge", self.bridge)
            view.page().setWebChannel(channel)

            layout.addWidget(view)
            index_html = os.path.join(resolve_ui_dir(), "index.html")
            view.setUrl(QUrl.fromLocalFile(index_html))

            live_dir = os.environ.get("WEBENGINE_LIVE_DIR")
            _log(f"open_dialog: live_dir={live_dir!r} dev_src={DEV_SRC!r}")
            if live_dir:
                # qgis-<pid>/<plugin_id> で分離。複数インスタンス・
                # 複数プラグインが共存しても衝突しない
                live_dir = os.path.join(
                    live_dir, f"qgis-{os.getpid()}", __package__)
                try:
                    from .live_driver import LiveDriver
                    self._live = LiveDriver(
                        view, live_dir, iface=self.iface,
                        dev_reload=self._dev_reload if DEV_SRC else None,
                    )
                    _log(f"LiveDriver active: {live_dir}")
                except Exception:
                    import traceback
                    _log("LiveDriver failed:\n" + traceback.format_exc())

        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
