"""開発用ホットリロード(手動)。

メニュー「プラグイン > QGIS Live Driver > ホットリロード」から、
開発対象のプラグインを手動で sys.modules 掃除+reloadPlugin
(+open_dialog再表示)する。QGIS再起動・deployは不要。

候補のプラグインidは、junction配置時は自プラグインのrealpath
(<repo>/qgis-plugin/<id>)からrepoを辿って plugin.config.json の
id 順に取る。見つからない場合(-Copy配置や通常利用)はロード中の
全プラグインを候補にするため、サードパーティプラグインの手動
リロードとしても使える。
"""

import json
import os

CTRL_ID = "qgis_live_driver"


def dev_plugin_ids(own_file):
    """ホットリロード候補のプラグインid一覧を返す。

    plugin.config.json が発見できればそのid順(deploy済みのもののみ)、
    無ければロード中プラグインのid順。
    """
    deployed_dir = os.path.dirname(os.path.abspath(own_file))
    plugins_root = os.path.dirname(deployed_dir)
    try:
        # junction配置: realpathが <repo>/qgis-plugin/<id> を指す
        repo = os.path.dirname(os.path.dirname(
            os.path.realpath(deployed_dir)))
        with open(os.path.join(repo, "plugin.config.json"),
                  encoding="utf-8") as f:
            cfg = json.load(f)
        ids = cfg["id"] if isinstance(cfg["id"], list) else [cfg["id"]]
        ok = [i for i in ids
              if os.path.isdir(os.path.join(plugins_root, i))]
        if ok:
            return ok
    except Exception:
        pass
    try:
        import qgis.utils
        return sorted(qgis.utils.plugins.keys())
    except Exception:
        return []


def reload_plugins(ids, notify=None):
    """プラグインid群を順にリロードする。

    制御面の qgis_live_driver は最後(送信経路を先に殺さないため)。
    自プラグイン自身のリロードも可能(呼出中フレームは有効なまま)。
    notify は (level, msg) を受けるコールバック(level="info"/"warn")。
    """
    notify = notify or (lambda level, msg: None)
    for pid in sorted(ids, key=lambda p: (p == CTRL_ID, p)):
        try:
            from .live_driver import reload_plugin_now
            res = reload_plugin_now(pid)
            notify("info", f"ホットリロード: {pid}"
                   + (" (ダイアログ再表示)" if res.get("opened") else ""))
        except Exception:
            notify("warn", f"ホットリロード失敗: {pid}")
