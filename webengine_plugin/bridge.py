import json

from qgis.PyQt.QtCore import QObject, pyqtSignal, pyqtSlot

from .logic import summarize_layers


class PluginBridge(QObject):
    """QWebChannel経由でJSに公開するAPI。

    QGIS APIへの依存はこのクラス(とiface)に閉じ込め、
    純粋ロジックは logic.py 側に置いてpytestで検証可能にする。
    JSからは `bridge.<method>(args..., callback)` 形式で呼ばれる。
    """

    # Python -> JS の一方向通知用。UI側で bridge.layerAdded.connect(...) できる。
    layerAdded = pyqtSignal(str)

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self._iface = iface

    @pyqtSlot(result=str)
    def pluginInfo(self):
        return json.dumps({
            "name": "WebEngine Plugin",
            "version": "0.1.0",
            "qgis": self._qgis_version(),
        }, ensure_ascii=False)

    @pyqtSlot(result=str)
    def listLayers(self):
        from qgis.core import QgsProject
        layers = list(QgsProject.instance().mapLayers().values())
        return json.dumps(summarize_layers(layers), ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def setActiveLayer(self, layer_id):
        from qgis.core import QgsProject
        from qgis.PyQt.QtCore import QTimer
        layer = QgsProject.instance().mapLayer(layer_id)
        if layer is None:
            return json.dumps({"ok": False, "error": f"layer not found: {layer_id}"})
        # 重いQGIS操作は即時実行するとWebChannelの同期呼び出しがJSスレッドを
        # ブロックし、後続のrunJavaScriptまで飢餓するためイベントループに譲る
        QTimer.singleShot(0, lambda l=layer: self._iface.setActiveLayer(l))
        return json.dumps({"ok": True, "active": layer.name()})

    @pyqtSlot(result=str)
    def zoomToActiveLayer(self):
        from qgis.PyQt.QtCore import QTimer
        layer = self._iface.activeLayer()
        if layer is None:
            return json.dumps({"ok": False, "error": "no active layer"})
        canvas = self._iface.mapCanvas()
        QTimer.singleShot(0, lambda c=canvas, e=layer.extent(): (c.setExtent(e), c.refresh()))
        return json.dumps({"ok": True})

    def _qgis_version(self):
        try:
            from qgis.core import Qgis
            return Qgis.QGIS_VERSION
        except Exception:
            return "unknown"
