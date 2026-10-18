"""qgis_live_driver 自身のAI向けブリッジ。

ドライバ自身の機能は LiveDriver のコマンド面(pyeval/status/bridge_call等)
として全経路から既に呼べるため、ここでは describe_plugins カタログ用の
自己記述と稼働状態の報告だけを提供する。
"""

import json
import os

_PLUGIN_ID = "qgis_live_driver"

_COMMANDS = [
    {"name": "pyeval", "signature": "pyeval(code)",
     "description": "QGISプロセス内で任意Pythonを実行(iface/QgsProject等にアクセス可)"},
    {"name": "eval", "signature": "eval(code)",
     "description": "WebEngineプラグインのページ内でJS実行(view必須)"},
    {"name": "status", "signature": "status()",
     "description": "ドライバ・ロード中プラグイン・bridge有無の一覧"},
    {"name": "describe_plugins", "signature": "describe_plugins()",
     "description": "全プラグインのAI利用可能機能カタログ(pluginInfo集約)"},
    {"name": "bridge_call", "signature": "bridge_call(plugin_id, method, args)",
     "description": "プラグインのbridgeメソッドを直接呼ぶ"
                    "(bridge未搭載プラグインは汎用アダプタが応答)"},
    {"name": "open_plugin", "signature": "open_plugin(plugin_id)",
     "description": "プラグインをロード+run()で開く"},
    {"name": "reload_plugin", "signature": "reload_plugin(plugin_id)",
     "description": "プラグインを再読み込み(junction配置ならコード即反映)"},
    {"name": "screenshot", "signature": "screenshot(target, path)",
     "description": "地図キャンバス/mainwindow/dockのPNG撮影"},
]


class QgisLiveBridge:
    """QGIS Live Driver の自己記述ブリッジ。

    メソッドはJSON文字列を返す(他プラグインのbridgeと同じ契約)。
    """

    def __init__(self, plugin):
        self._plugin = plugin

    @staticmethod
    def _ok(payload=None):
        obj = {"ok": True}
        if payload:
            obj.update(payload)
        return json.dumps(obj, ensure_ascii=False)

    def pluginInfo(self):
        """describe_plugins カタログ用の標準自己記述。"""
        return self._ok({
            "id": _PLUGIN_ID,
            "name": "QGIS Live Driver",
            "summary": "QGISプロセス内の遠隔制御ハブ。pyeval/status/"
                       "bridge_call/describe_plugins等をファイルJSONL・"
                       "REST・MCPの全経路で提供する",
            "when_to_use": [
                "QGIS内部(iface/QgsProject/地物/レイヤ)を直接操作・検査したい",
                "他プラグインの機能をbridge_callで呼び出したい",
                "地図キャンバスやウィンドウのスクリーンショットが欲しい",
                "プラグインのロード・再読み込みを行いたい",
            ],
            "invoke": {"type": "command",
                       "note": "bridge_callではなくドライバのコマンド面"
                               "(qgis_pyeval等のMCPツール)を使う",
                       "commands": _COMMANDS},
            "methods": [
                {"name": "pluginInfo", "signature": "pluginInfo()",
                 "description": "この自己記述を返す"},
                {"name": "status", "signature": "status()",
                 "description": "ドライバ稼働状態(live_dir/http_port/pid)"},
            ],
        })

    def status(self):
        """ドライバの稼働状態を返す。"""
        d = self._plugin.driver
        return self._ok({
            "id": _PLUGIN_ID,
            "pid": os.getpid(),
            "remote_enabled": d is not None,
            "live_dir": getattr(d, "dir", None),
            "http_port": getattr(d, "http_port", None),
            "commands": [c["name"] for c in _COMMANDS],
        })
