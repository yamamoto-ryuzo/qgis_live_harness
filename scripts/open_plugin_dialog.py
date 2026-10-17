# qgis --code で起動時に実行され、プラグインダイアログを自動で開くスクリプト。
# QGISのPython環境で実行されるため import はそのまま使える。

from qgis.utils import plugins

plugin = plugins.get("webengine_plugin")
if plugin is None:
    print("[open_plugin_dialog] webengine_plugin not loaded (プラグイン有効化を確認)")
else:
    plugin.open_dialog()
    print("[open_plugin_dialog] dialog opened")
