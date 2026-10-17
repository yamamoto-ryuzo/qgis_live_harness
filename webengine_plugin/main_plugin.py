import os

from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QDialog, QVBoxLayout
from qgis.PyQt.QtWebChannel import QWebChannel
from qgis.PyQt.QtWebEngineWidgets import QWebEngineView

from .bridge import PluginBridge

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_NAME = "WebEngine Plugin"


def resolve_ui_dir():
    """ui/ はリポジトリ直下(開発時)とプラグイン内(配布時)の両方を許容する。"""
    candidates = [
        os.path.join(PLUGIN_DIR, "ui"),
        os.path.join(os.path.dirname(PLUGIN_DIR), "ui"),
    ]
    for d in candidates:
        if os.path.isfile(os.path.join(d, "index.html")):
            return d
    raise FileNotFoundError("ui/index.html not found in: " + ", ".join(candidates))


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

    def unload(self):
        if self.action is not None:
            self.iface.removePluginMenu(f"&{PLUGIN_NAME}", self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None
        if self.dialog is not None:
            self.dialog.deleteLater()
            self.dialog = None

    def open_dialog(self):
        if self.dialog is None:
            self.dialog = QDialog(self.iface.mainWindow())
            self.dialog.setWindowTitle(PLUGIN_NAME)
            self.dialog.resize(900, 640)
            layout = QVBoxLayout(self.dialog)
            layout.setContentsMargins(0, 0, 0, 0)

            view = QWebEngineView(self.dialog)
            self.bridge = PluginBridge(self.iface, parent=view)
            channel = QWebChannel(view.page())
            channel.registerObject("bridge", self.bridge)
            view.page().setWebChannel(channel)

            layout.addWidget(view)
            index_html = os.path.join(resolve_ui_dir(), "index.html")
            view.setUrl(QUrl.fromLocalFile(index_html))

        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
