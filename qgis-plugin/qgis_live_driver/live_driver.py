"""QGISプロセスをファイル経由で外部制御するドライバ(スタンドアロン版)。

WebEngineを持たない任意のプラグイン/QGIS環境で使える制御面だけの実装。
webengine_plugin版との違い: viewを持たないため eval/devreload は未対応。
代わりに screenshot は iface.mapCanvas() の地図キャンバスをPNG化する。

環境変数 WEBENGINE_LIVE_DIR 設定時のみ有効。
live dir は WEBENGINE_LIVE_DIR/qgis-<pid>/<plugin_id>/。

コマンド形式(1行1JSON):
  {"id": 1, "type": "pyeval", "code": "iface.activeLayer().name()"}
  {"id": 2, "type": "screenshot", "path": "C:/.../shot.png"}  ← 地図キャンバス
  {"id": 3, "type": "status"}
  {"id": 4, "type": "open_plugin", "plugin_id": "webengine_plugin"}
  {"id": 5, "type": "reload_plugin", "plugin_id": "webengine_plugin"}
  {"id": 6, "type": "bridge_call", "plugin_id": "webengine_plugin",
   "method": "pluginInfo", "args": []}

plugin_id を「ルーティング」として使うコマンド(eval/pyeval/screenshot/
devreload)は、plugin_id が他プラグインを指す場合そのプラグインの
LiveDriverに転送され、結果は呼び出し元の results.jsonl に返る
(このドライバが全プラグインの統一制御点になる)。
"""

import inspect
import itertools
import json
import os
import queue
import threading
import traceback

from qgis.PyQt.QtCore import QTimer

POLL_MS = 200

# id無しコマンド(HTTPの/api/*等)用の自動採番。転送先のevalではcidが
# JS報告との照合キーになるため、Noneのままでは結果報告が全て破棄される
_AUTO_IDS = itertools.count(1)

# plugin_id をルーティングではなくコマンド自身の引数として使う種別。
# これらは常にこのドライバ自身が処理する。
_LOCAL_TYPES = {"status", "open_plugin", "reload_plugin", "bridge_call"}


def _to_jsonable(v):
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, dict):
        return {str(k): _to_jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [_to_jsonable(x) for x in v]
    return repr(v)


def _loaded_plugins():
    import qgis.utils
    return qgis.utils.plugins


def _find_plugin_driver(plugin_id):
    """他プラグインのLiveDriverを返す(無ければNone)。"""
    p = _loaded_plugins().get(plugin_id)
    if p is None:
        return None
    for attr in ("driver", "_live", "live"):
        d = getattr(p, attr, None)
        if d is not None and hasattr(d, "_handle"):
            return d
    return None


class LiveDriver:
    def __init__(self, live_dir, iface):
        self.iface = iface
        self.view = None  # WebEngineなし。ns経由でクライアントがUI有無を判定できる
        self.dir = live_dir
        self.cmd_path = os.path.join(live_dir, "commands.jsonl")
        self.res_path = os.path.join(live_dir, "results.jsonl")
        self.http_port = None  # __init__.py が start_http 後に設定する
        # ドライバ再生成時に過去のコマンドを再実行しないよう末尾までスキップ
        self.offset = os.path.getsize(self.cmd_path) if os.path.exists(self.cmd_path) else 0
        self._ns = {"iface": iface, "view": None, "driver": self}
        # pyeval内で頻出のQGIS APIを事前importしておく(利便性のため)
        try:
            from qgis.core import QgsProject, QgsApplication
            self._ns.update({"QgsProject": QgsProject,
                             "QgsApplication": QgsApplication})
        except Exception:
            pass
        # ファイル以外の命令入力(HTTPサーバ等の別スレッドからの投入)。
        # GUIスレッド以外から iface/QgsProject に触れないため、
        # 実行は必ずこのドライバの_poll(GUIスレッド)内で行う
        self._queue = queue.Queue()
        os.makedirs(live_dir, exist_ok=True)

        self.timer = QTimer()
        self.timer.timeout.connect(self._poll)
        self.timer.start(POLL_MS)

    def submit(self, cmd, timeout=180.0):
        """別スレッドからコマンドを投入し、GUIスレッドでの実行結果を待って返す。

        @returns {"id":..., "result": v} or {"id":..., "error": e}
        """
        if cmd.get("id") is None:
            cmd["id"] = f"submit-{next(_AUTO_IDS)}"
        box = {}
        done = threading.Event()
        self._queue.put((cmd, box, done))
        if not done.wait(timeout):
            return {"id": cmd.get("id"), "error": f"submit timeout ({timeout}s)"}
        return box.get("reply", {"id": cmd.get("id"), "error": "no reply"})

    def stop(self):
        self.timer.stop()
        # timer.timeout.connect(bound method) がselfへの参照を保持し、
        # リロードごとにドライバ+QTimerが滞留するためC++側も解放する
        self.timer.deleteLater()

    def _poll(self):
        # メモリキュー(HTTP等)の命令を先に処理
        while True:
            try:
                cmd, box, done = self._queue.get_nowait()
            except queue.Empty:
                break
            # replyが呼ばれた時点で完了。_handleが"async"を返した(eval転送等)は
            # replyが非同期的に後で呼ばれるため、ここでdone.set()しない
            def _reply_once(obj, _box=box, _done=done):
                _box["reply"] = obj
                _done.set()
            try:
                async_pending = self._handle(cmd, reply=_reply_once) == "async"
            except Exception:
                async_pending = False
                box["reply"] = {"id": cmd.get("id"),
                                "error": traceback.format_exc()}
            if not async_pending and not done.is_set():
                done.set()

        if not os.path.exists(self.cmd_path):
            return
        # ファイルが作り直されるとoffsetが実サイズを超えて読み飛ばすため補正
        if os.path.getsize(self.cmd_path) < self.offset:
            self.offset = 0
        with open(self.cmd_path, "r", encoding="utf-8") as f:
            f.seek(self.offset)
            data = f.read()
        # クライアントが書き込み中の部分行を処理するとJSONDecodeErrorで
        # コマンド喪失するため、改行で終端された行だけ処理し、
        # 未完の末尾はoffsetを進めず次ポーリングに残す
        end = data.rfind("\n")
        if end < 0:
            return
        self.offset += end + 1
        for line in data[:end].split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                self._handle(json.loads(line))
            except Exception as e:
                self._reply({"id": None, "error": repr(e)})

    def _handle(self, cmd, reply=None):
        reply = reply or self._reply
        cid = cmd.get("id") or f"auto-{next(_AUTO_IDS)}"
        ctype = cmd.get("type", "eval")
        pid = cmd.get("plugin_id")
        # plugin_id が他プラグインを指すコマンドはそのドライバへ転送。
        # 結果は注入したreply経由でこのlive dirのresults.jsonlに返る。
        if pid and pid != __package__ and ctype not in _LOCAL_TYPES:
            return self._forward(cid, pid, cmd, reply)
        if ctype == "pyeval":
            self._pyeval(cid, cmd.get("code", ""), reply)
            return
        if ctype == "screenshot":
            self._screenshot(cid, cmd, reply)
            return
        if ctype == "status":
            reply({"id": cid, "result": self._status()})
            return
        if ctype == "open_plugin":
            self._open_plugin(cid, pid, reply)
            return
        if ctype == "reload_plugin":
            self._reload_plugin(cid, pid, reply)
            return
        if ctype == "bridge_call":
            self._bridge_call(cid, cmd, reply)
            return
        reply({
            "id": cid,
            "error": f"type={ctype} unsupported: qgis_live_driver has no WebEngine view. "
                     "pass plugin_id of a WebEngine plugin to route "
                     "(eval/devreload/screenshot), or use "
                     "pyeval/status/open_plugin/reload_plugin/bridge_call",
        })

    def _forward(self, cid, pid, cmd, reply):
        """他プラグインのドライバへコマンドを転送し、結果を呼び出し元へ返す。"""
        drv = _find_plugin_driver(pid)
        if drv is None:
            reply({"id": cid, "error":
                   f"plugin '{pid}' has no live driver "
                   f"(loaded: {sorted(_loaded_plugins().keys())})"})
            return
        if "reply" not in inspect.signature(drv._handle).parameters:
            reply({"id": cid, "error":
                   f"plugin '{pid}' driver does not support reply routing; "
                   "redeploy+reload it to update live_driver.py"})
            return
        fwd = {k: v for k, v in cmd.items() if k != "plugin_id"}
        try:
            return drv._handle(fwd, reply=reply)
        except Exception:
            reply({"id": cid, "error": traceback.format_exc()})

    def _status(self):
        """ドライバ自身と全プラグインの状態を返す(生存確認・一覧用)。"""
        plugs = {}
        try:
            for pid, p in _loaded_plugins().items():
                drv = None
                for a in ("driver", "_live", "live"):
                    d = getattr(p, a, None)
                    if d is not None and hasattr(d, "_handle"):
                        drv = d
                        break
                plugs[pid] = {
                    "driver": drv is not None,
                    "view": bool(drv is not None
                                 and getattr(drv, "view", None) is not None),
                }
        except Exception:
            pass
        return {
            "pid": os.getpid(),
            "plugin": __package__,
            "live_dir": self.dir,
            "http_port": self.http_port,
            "view": self.view is not None,
            "plugins": plugs,
        }

    def _open_plugin(self, cid, pid, reply):
        """プラグインをload/startし、open_dialogがあれば開く。"""
        if not pid:
            reply({"id": cid, "error": "plugin_id required"})
            return
        try:
            import qgis.utils
            if pid not in qgis.utils.plugins:
                qgis.utils.loadPlugin(pid)
                qgis.utils.startPlugin(pid)
            p = qgis.utils.plugins.get(pid)
            opened = False
            if p is not None and hasattr(p, "open_dialog"):
                p.open_dialog()
                opened = True
            reply({"id": cid, "result": {
                "loaded": pid in qgis.utils.plugins,
                "opened": opened,
                "plugins": sorted(qgis.utils.plugins.keys()),
            }})
        except Exception:
            reply({"id": cid, "error": traceback.format_exc()})

    def _reload_plugin(self, cid, pid, reply):
        """sys.modulesキャッシュを掃除してreloadPluginし、ダイアログを開き直す。

        自分自身(qgis_live_driver)のreloadも可能: 実行中はこのドライバが
        unload→再生成されるが、呼び出し中のコードフレームは有効なままなので
        reload完了後に結果をresults.jsonlへ書き込める。
        """
        if not pid:
            reply({"id": cid, "error": "plugin_id required"})
            return
        try:
            import sys
            import qgis.utils
            for k in [k for k in list(sys.modules)
                      if k == pid or k.startswith(pid + ".")]:
                sys.modules.pop(k, None)
            if pid in qgis.utils.plugins:
                qgis.utils.reloadPlugin(pid)
            else:
                qgis.utils.loadPlugin(pid)
                qgis.utils.startPlugin(pid)
            p = qgis.utils.plugins.get(pid)
            opened = False
            if p is not None and hasattr(p, "open_dialog"):
                p.open_dialog()
                opened = True
            reply({"id": cid, "result": {
                "loaded": pid in qgis.utils.plugins,
                "opened": opened,
                "plugins": sorted(qgis.utils.plugins.keys()),
            }})
        except Exception:
            reply({"id": cid, "error": traceback.format_exc()})

    def _bridge_call(self, cid, cmd, reply):
        """プラグインのbridgeオブジェクトのメソッドをプロセス内で直接呼ぶ。

        JSのBridgeClient.callJsonと違いWebChannelを経由しないため、
        レンダラー飢餓中でもbridgeメソッドを検証できる。
        bridgeメソッドがJSON文字列を返す慣例に合わせ、パース可能なら
        構造化して返す。plugin_id省略時はbridgeを持つ最初のプラグイン。
        """
        pid = cmd.get("plugin_id")
        method = cmd.get("method")
        args = cmd.get("args") or []
        try:
            plugins = _loaded_plugins()
            target = plugins.get(pid) if pid else None
            if target is None:
                target = next(
                    (p for p in plugins.values()
                     if getattr(p, "bridge", None) is not None), None)
            if target is None:
                reply({"id": cid, "error":
                       f"plugin '{pid}' not loaded or has no bridge "
                       f"(loaded: {sorted(plugins.keys())})"})
                return
            bridge = getattr(target, "bridge", None)
            fn = getattr(bridge, method, None) if bridge is not None else None
            if not callable(fn):
                reply({"id": cid, "error":
                       f"no bridge method '{method}'. methods: "
                       f"{[m for m in dir(bridge) if not m.startswith('_')] if bridge else 'no bridge'}"})
                return
            res = fn(*args)
            if isinstance(res, str):
                try:
                    res = json.loads(res)
                except Exception:
                    pass
            reply({"id": cid, "result": _to_jsonable(res)})
        except Exception:
            reply({"id": cid, "error": traceback.format_exc()})

    def _screenshot(self, cid, cmd, reply):
        """地図キャンバス(既定)またはメインウィンドウをPNG保存する。"""
        path = cmd.get("path") or os.path.join(self.dir, f"shot-{cid}.png")
        target = cmd.get("target", "canvas")
        try:
            if target == "canvas":
                canvas = self.iface.mapCanvas() if self.iface is not None else None
                if canvas is None:
                    reply({"id": cid, "error": "no map canvas"})
                    return
                canvas.saveAsImage(path)
            elif target in ("mainwindow", "main"):
                if self.iface is None:
                    reply({"id": cid, "error": "no iface"})
                    return
                self.iface.mainWindow().grab().save(path)
            else:
                reply({"id": cid, "error":
                       f"unknown screenshot target: {target} "
                       "(canvas|mainwindow)"})
                return
            reply({"id": cid, "result": path})
        except Exception:
            reply({"id": cid, "error": traceback.format_exc()})

    def _pyeval(self, cid, code, reply=None):
        """QGISプロセス内でPythonを実行する。

        式としてコンパイルできればeval、その結果を返す。文の場合はexecで実行し、
        名前空間の `result` 変数の値を返す(未設定ならNone)。
        同期的に実行するため長いコードはイベントループをブロックする点に注意。
        plugin_id付きで転送された場合、そのプラグインのドライバの
        名前空間(view等)で実行される。
        """
        reply = reply or self._reply
        self._ns.pop("result", None)
        try:
            try:
                code_obj = compile(code, "<pyeval>", "eval")
            except SyntaxError:
                code_obj = compile(code, "<pyeval>", "exec")
            res = eval(code_obj, self._ns)
            if res is None:
                res = self._ns.pop("result", None)
            reply({"id": cid, "result": _to_jsonable(res)})
        except Exception:
            reply({"id": cid, "error": traceback.format_exc()})

    def _reply(self, obj):
        os.makedirs(os.path.dirname(self.res_path), exist_ok=True)
        with open(self.res_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
