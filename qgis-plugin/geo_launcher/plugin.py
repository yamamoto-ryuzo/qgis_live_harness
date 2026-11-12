# -*- coding: utf-8 -*-
"""geo_launcher プラグイン本体。

kasugai_qgis (Rust製 QGIS/QField ランチャー) の機能を QGIS プラグインへ
移植したもの。ランチャーインストールフォルダの qgis_settings.json を読み、
プロファイル/プロジェクト/バージョン選択・ロール制御・開発モード
(WEBENGINE_*)・ドライブ割当・local_sync・プロファイルシード・
NSIS自動更新を QGIS 内から実行できる。

- launcher_core.py: Rust版の機能移植(QGIS非依存)
- launcher_dialog.py: 管理ダイアログ(Qt)
- bridge.py: GeoLauncherBridge (bridge_call / describe_plugins 経由)
"""

import os

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QToolBar
from qgis.core import QgsMessageLog, Qgis

from .bridge import GeoLauncherBridge
from .i18n_json import install_translator
from .launcher_core import PLUGIN_ID

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_TAG = PLUGIN_ID


def _log(msg, level=Qgis.MessageLevel.Warning):
    QgsMessageLog.logMessage(str(msg), LOG_TAG, level)


class plugin(object):
    def __init__(self, iface):
        self.iface = iface
        self.actions = []
        self.menu_name = "&" + PLUGIN_ID
        self._init_language()
        # qgis_live_driver の bridge_call / describe_plugins 経由で
        # AI・外部制御から使われるAPI (plugins['geo_launcher'].bridge)
        self.bridge = GeoLauncherBridge(self)
        self._dialog = None

    @staticmethod
    def tr(message):
        return QCoreApplication.translate(PLUGIN_ID, message)

    def _init_language(self):
        """QGISの言語設定に合わせて i18n/<lang>.json を載せる。"""
        self.translator = install_translator(PLUGIN_DIR)

    # ---- GeoSuite共有ツールバー ------------------------------------------
    def _geo_toolbar(self, ensure_visible=True):
        """GeoSuite共有ツールバーをfind-or-createで返す。"""
        tb = self.iface.mainWindow().findChild(QToolBar, "GeoSuite")
        if tb is None:
            tb = self.iface.addToolBar("GeoSuite")
            tb.setObjectName("GeoSuite")
        if ensure_visible:
            tb.setVisible(True)
        return tb

    # ---- GUI --------------------------------------------------------------
    def initGui(self):
        action = QAction(
            QIcon(os.path.join(PLUGIN_DIR, "icon.png")),
            self.tr("QGIS/QField launcher..."), self.iface.mainWindow())
        action.triggered.connect(self.open_dialog)
        self.iface.addPluginToMenu(self.menu_name, action)
        self._geo_toolbar().addAction(action)
        self.actions.append(action)

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(self.menu_name, action)
            self._geo_toolbar(ensure_visible=False).removeAction(action)
        self.actions = []
        self.close_dialog()

    # ---- ダイアログ --------------------------------------------------------
    def open_dialog(self):
        from .launcher_dialog import LauncherDialog
        if self._dialog is None:
            self._dialog = LauncherDialog(self)
        else:
            try:
                self._dialog.reload_all()
            except Exception as e:  # noqa: BLE001
                _log("dialog reload failed: {0}".format(e))
        self._dialog.show()
        self._dialog.raise_()
        self._dialog.activateWindow()
        return self._dialog

    def close_dialog(self):
        if self._dialog is not None:
            try:
                self._dialog.close()
            except Exception:  # noqa: BLE001
                pass
            self._dialog = None
