# -*- coding: utf-8 -*-
"""geo_excel プラグイン本体。

upstream(QGIS-exportExcel)のスクリプトは「レイヤアクション」として実行される
前提で書かれており、QGISアクションの置換変数([% @layer_id %] / [% $id %])を
含む。本プラグインはプラグインメニューからの実行時に、これらをアクティブ
レイヤ/選択地物の値で置き換えて exec することで、スクリプトを無改変で
再利用する。

またスクリプト内の `from PyQt5.…` 固定importは、exec直前にソース文字列を
`from qgis.PyQt.…` へ書き換えて吸収する(QGISのQt6ビルドでは PyQt5 のimportが
qgis.utils._import フックで禁止されるため、sys.modules shim では不可)。
ファイル自体は upstream のまま維持する。

実行には win32com(pywin32) と Excel が必要。
"""

import os
import re

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.core import QgsProject, QgsVectorLayer

from . import settings
from .bridge import GeoExcelBridge
from .i18n_json import install_translator

PLUGIN_DIR = os.path.dirname(__file__)

# PyQt5 固定importを qgis.PyQt(Qt5/Qt6 自動切替)へ書き換える
_PYQT5_RE = re.compile(r"PyQt5(?=[\.\s])")


def _rewrite_source(src):
    """アクション置換変数と Qt5 固有記法を実行用に書き換える。

    - `PyQt5.` / `from PyQt5 import` → `qgis.PyQt`
    - `Qt.WaitCursor` → `Qt.CursorShape.WaitCursor`
      (Qt6で非スコープenumは廃止。Qt5でもスコープ記法は有効)
    """
    src = _PYQT5_RE.sub("qgis.PyQt", src)
    return src.replace("Qt.WaitCursor", "Qt.CursorShape.WaitCursor")


def _active_vector_layer(iface):
    layer = iface.activeLayer()
    if not isinstance(layer, QgsVectorLayer):
        iface.messageBar().pushCritical(
            "geo_excel",
            QCoreApplication.translate(
                "geo_excel", "Please activate a vector layer."),
        )
        return None
    return layer


class plugin(object):
    def __init__(self, iface):
        self.iface = iface
        self.actions = []
        self.menu_name = "&geo_excel"
        self._init_language()
        # qgis_live_driver の bridge_call / describe_plugins 経由で
        # AI・外部制御から使われるAPI (plugins['geo_excel'].bridge)
        self.bridge = GeoExcelBridge(self)
        self._settings_dialog = None

    @staticmethod
    def tr(message):
        return QCoreApplication.translate("geo_excel", message)

    def _init_language(self):
        """QGISの言語設定に合わせて i18n/<lang>.json を載せる。

        ソース文字列は英語。en または未対応言語では翻訳を載せない。
        """
        self.translator = install_translator(PLUGIN_DIR)

    # ---- GUI --------------------------------------------------------------
    def initGui(self):
        entries = (
            (self.tr("Export list report (active layer)"),
             "exportList.py", False),
            (self.tr("Export single form (selected feature)"),
             "exportSingle.py", True),
            (self.tr("Bulk export single forms (selected or all features)"),
             "exportSingleBulk.py", False),
        )
        for title, script, needs_fid in entries:
            action = QAction(title, self.iface.mainWindow())
            action.triggered.connect(
                lambda checked=False, s=script, f=needs_fid: self._run(s, f)
            )
            self.iface.addPluginToMenu(self.menu_name, action)
            self.actions.append(action)

        settings_action = QAction(
            self.tr("Settings..."), self.iface.mainWindow())
        settings_action.triggered.connect(self.open_settings)
        self.iface.addPluginToMenu(self.menu_name, settings_action)
        self.actions.append(settings_action)

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(self.menu_name, action)
        self.actions = []
        if self._settings_dialog is not None:
            self._settings_dialog.close()
            self._settings_dialog = None

    def open_settings(self):
        """設定ダイアログを開く(既にあれば前面に出す)。"""
        from .settings_dialog import GeoExcelSettingsDialog

        if self._settings_dialog is None:
            self._settings_dialog = GeoExcelSettingsDialog(
                self, self.iface.mainWindow())
        else:
            self._settings_dialog.refresh()
        self._settings_dialog.show()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()
        return self._settings_dialog

    # ---- script runner ----------------------------------------------------
    def _run(self, script_name, needs_fid):
        layer = _active_vector_layer(self.iface)
        if layer is None:
            return

        if needs_fid:
            fids = layer.selectedFeatureIds()
            if not fids:
                self.iface.messageBar().pushCritical(
                    "geo_excel", self.tr("Please select one or more features.")
                )
                return
            for fid in fids:
                self._exec_script(script_name, layer.id(), fid)
        else:
            self._exec_script(script_name, layer.id(), None)

    def _exec_script(self, script_name, layer_id, fid):
        """スクリプトをexecして結果を返す。

        戻り値: {"ok": bool, "error": str|None, "ns": dict}。
        ns にはスクリプトのグローバルが残るため、bridgeは
        excel_result/output_path 等の終了状態をここから取得する。
        """
        # 不足しているレイヤ変数(xlsout_*)へ既定値を自動適用する。
        # 既定の出力先は <ドキュメント>/geo_excel、テンプレートは
        # 未指定時にレイヤのフィールドから自動生成される(設定で無効化可)。
        if settings.auto_apply_enabled():
            layer = QgsProject.instance().mapLayer(layer_id)
            if isinstance(layer, QgsVectorLayer):
                rep = settings.ensure_layer_variables(layer, script_name)
                if rep["applied"]:
                    self.iface.messageBar().pushInfo(
                        "geo_excel",
                        self.tr("Applied default layer variables: {0}").format(
                            ", ".join(sorted(rep["applied"]))))
                for err in rep["errors"]:
                    self.iface.messageBar().pushCritical(
                        "geo_excel",
                        self.tr("Could not apply default for {0}").format(err))

        path = os.path.join(PLUGIN_DIR, script_name)
        with open(path, encoding="utf-8") as f:
            src = f.read()

        # QGISアクションの置換変数を実値で置き換える
        src = src.replace("[% @layer_id %]", layer_id)
        if fid is not None:
            src = src.replace("[% $id %]", str(fid))
        src = _rewrite_source(src)

        ns = {"__name__": f"geo_excel.{script_name}", "__file__": path}
        try:
            code = compile(src, path, "exec")
            exec(code, ns)
        except Exception as e:  # noqa: BLE001 - スクリプト側の失敗をQGISを落とさず通知する
            QMessageBox.critical(
                self.iface.mainWindow(),
                "geo_excel",
                self.tr("Failed to run {0}:\n{1}").format(script_name, e),
            )
            return {"ok": False, "error": str(e), "ns": ns}
        return {"ok": True, "ns": ns}
