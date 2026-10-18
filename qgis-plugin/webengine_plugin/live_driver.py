"""ファイル経由のライブドライバ。

QtWebEngineのCDP実装(Runtimeドメイン)がこの環境では応答しないため、
プラグイン側でQTimerポーリングし commands.jsonl に書き込まれたJSを
view.page().runJavaScript() で実行する。結果はJS側が console.log("__live ...")
で報告し、_LiveConsolePage.javaScriptConsoleMessage が受けて results.jsonl に返す。

重要: WebChannelの transport.send は返信をネストして同期的に待つため、
send中にrunJavaScriptを実行すると返信が喪失しチャネルがwedgeする(実測確認)。
そのため (a) eval結果のポーリング読み取りはしない、(b) evalの投入は
pendingが空の時だけに直列化する、(c) 結果報告はWebChannelを経由しない
一方向のconsole通知にする、という3点で回避している。

環境変数 WEBENGINE_LIVE_DIR が設定されている場合のみ有効化される。

コマンド形式(1行1JSON):
  {"id": 1, "type": "eval", "expression": "document.title"}
  {"id": 2, "type": "screenshot", "path": "C:/.../shot.png"}
  {"id": 3, "type": "pyeval", "code": "iface.activeLayer().name()"}
  {"id": 4, "type": "devreload"}
  {"id": 5, "type": "status"}
  {"id": 6, "type": "open_plugin", "plugin_id": "<id>"}
  {"id": 7, "type": "reload_plugin", "plugin_id": "<id>"}
  {"id": 8, "type": "bridge_call", "plugin_id": "<id>", "method": "...", "args": []}
結果形式:
  {"id": 1, "result": <JSON化可能な値>}  or  {"id": 1, "error": "..."}

plugin_id を「ルーティング」として使うコマンド(eval/pyeval/screenshot/
devreload)は、plugin_id が他プラグインを指す場合そのプラグインの
LiveDriverに転送され、結果は呼び出し元の results.jsonl に返る。
_handle(cmd, reply) の reply引数で結果の送り先を差し替えられるため、
qgis_live_driver等からの転送もこのlive dirに結果を残さず返せる。

pyeval はQGISプロセス内のPythonを同期実行する。式ならeval、文ならexecで実行し
(execの場合 `result` 変数への代入が返却値になる)。名前空間には iface/view/driver が
ありセッション中持続する。任意コード実行なので検証モード(WEBENGINE_LIVE_DIR
設定時)のみ有効。

devreload は WEBENGINE_DEV_SRC 指定時のみ有効。リポジトリ内のbridge等を
再importしてWebChannelのbridgeオブジェクトを差し替え、ページを再読み込みする。
deploy/reloadPluginなしでコード変更を反映できる(プラグイン本体側の
main_plugin/live_driver 等の変更は対象外。それらはlive:reloadを使う)。
"""

import hmac
import inspect
import itertools
import json
import os
import secrets
import time
import traceback

from qgis.PyQt.QtCore import QTimer

EVAL_TIMEOUT_MS = 120000
POLL_MS = 200
# キューでこれだけ滞留したevalは、クライアント側が既にタイムアウトして
# 新idでリトライ済みとみなし、実行せず破棄する(遅延clickの多重実行防止)
QUEUE_STALE_MS = 30000

# id無しコマンド(HTTPの/api/*等)用の自動採番。evalではcidがJS報告との
# 照合キーになるため、Noneのままでは結果報告が全て破棄されてハングする
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
    def __init__(self, view, live_dir, iface=None, dev_reload=None):
        self.view = view
        self.iface = iface
        self.dir = live_dir
        self.cmd_path = os.path.join(live_dir, "commands.jsonl")
        self.res_path = os.path.join(live_dir, "results.jsonl")
        # プラグインreload等でドライバが作り直されても、過去のコマンドを
        # 再実行しないよう既存ファイルは末尾までスキップする
        self.offset = os.path.getsize(self.cmd_path) if os.path.exists(self.cmd_path) else 0
        self.pending = {}  # cid -> {"remaining": ms, "reply": callable}
        self._queue = []  # (cid, expr, enqueued, reply) eval送信キュー。sendが飛んでいる間は投入しない
        self._runjs_mode = None  # "qt6" | "qt5"
        self._ns = {"iface": iface, "view": view, "driver": self}
        self._dev_reload = dev_reload  # callable -> 新しいbridgeオブジェクト or None
        # ファイル経由コマンドの認証トークン(qgis_live_driverと同仕様)。
        # クライアントは live_dir/token から読んでコマンドに付ける
        self.token = secrets.token_hex(24)
        os.makedirs(live_dir, exist_ok=True)
        try:
            with open(os.path.join(live_dir, "token"), "w",
                      encoding="ascii") as f:
                f.write(self.token)
        except Exception:
            pass

        # eval結果は console.log("__live ...") → _LiveConsolePage.
        # javaScriptConsoleMessage 経由でプッシュ受信する。
        # WebChannelのsendは返信待ち中のrunJavaScript割り込みでwedgeするため、
        # 一方向のconsole通知を使う(返信経路が存在しない=壊れようがない)。
        self._reports = {}  # cid -> {"n": total, "parts": {i: chunk}}
        self._attach_report_handler()

        self.timer = QTimer(view)
        self.timer.timeout.connect(self._poll)
        self.timer.start(POLL_MS)

    def stop(self):
        self.timer.stop()
        # timer.timeout.connect(bound method) がselfへの参照を保持し、
        # リロードごとにドライバ+QTimerが滞留するためC++側も解放する
        self.timer.deleteLater()

    def _poll(self):
        if os.path.exists(self.cmd_path):
            # ファイルが作り直されるとoffsetが実サイズを超えて読み飛ばすため補正
            if os.path.getsize(self.cmd_path) < self.offset:
                self.offset = 0
            with open(self.cmd_path, "r", encoding="utf-8") as f:
                f.seek(self.offset)
                data = f.read()
            # クライアントが書き込み中の部分行を処理するとJSONDecodeErrorで
            # コマンド喪失するため、改行で終端された行だけ処理し、
            # 未完の末尾はoffsetを進めず次ポーリングに残す。
            # 新規データ無し(空)でも後段のタイムアウト管理とキューdispatchを
            # 回す必要があるため、ここでは早期returnしない
            end = data.rfind("\n")
            if end >= 0:
                self.offset += end + 1
            for line in data[: max(end, 0)].split("\n"):
                line = line.strip()
                if not line:
                    continue
                try:
                    cmd = json.loads(line)
                except Exception as e:
                    self._reply({"id": None, "error": repr(e)})
                    continue
                if not hmac.compare_digest(str(cmd.get("token") or ""),
                                           self.token):
                    self._reply({"id": cmd.get("id"),
                                 "error": "unauthorized"})
                    continue
                try:
                    self._handle(cmd)
                except Exception as e:
                    self._reply({"id": None, "error": repr(e)})

        # evalのタイムアウト管理のみ(runJavaScriptプローブはwedgeを起こすため廃止)
        for cid in list(self.pending):
            self.pending[cid]["remaining"] -= POLL_MS
            if self.pending[cid]["remaining"] <= 0:
                ent = self.pending.pop(cid)
                ent["reply"]({"id": cid, "error": "eval timeout"})

        # 直列送信: pendingのevalが無い時だけ次を投入する。
        # sendが飛んでいる最中にrunJavaScriptを実行するとそのsendの返信が
        # 喪失する(Qt6.8のWebChannel transport制約)ため、evalは1件ずつ処理する
        if not self.pending and self._queue:
            cid, expr, enq, reply = self._queue.pop(0)
            if (time.monotonic() - enq) * 1000 > QUEUE_STALE_MS:
                reply({"id": cid, "error": "eval dropped: queue stale"})
            else:
                self._submit_eval(cid, expr, reply)

    def _handle(self, cmd, reply=None):
        """コマンドを処理する。

        @returns "async" の場合、replyが非同期的に後で呼ばれる(evalの
        キューイング/転送)。呼び出し元(submit等)は完了をreply待ちにできる。
        """
        reply = reply or self._reply
        cid = cmd.get("id") or f"auto-{next(_AUTO_IDS)}"
        ctype = cmd.get("type", "eval")
        pid = cmd.get("plugin_id")
        # plugin_id が他プラグインを指すコマンドはそのドライバへ転送。
        # 結果は注入したreply経由でこのlive dirのresults.jsonlに返る。
        if pid and pid != __package__ and ctype not in _LOCAL_TYPES:
            return self._forward(cid, pid, cmd, reply)
        if ctype == "screenshot":
            self._screenshot(cid, cmd, reply)
            return
        if ctype == "eval":
            self._queue.append(
                (cid, cmd.get("expression", ""), time.monotonic(), reply))
            return "async"
        if ctype == "pyeval":
            self._pyeval(cid, cmd.get("code", ""), reply)
            return
        if ctype == "devreload":
            self._devreload(cid, reply)
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
        reply({"id": cid, "error": f"unknown type: {ctype}"})

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
        """sys.modulesキャッシュを掃除してreloadPluginし、ダイアログを開き直す。"""
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
        """view(既定)/window/canvas/mainwindow をPNG保存する。"""
        path = cmd.get("path") or os.path.join(self.dir, f"shot-{cid}.png")
        target = cmd.get("target", "view")
        try:
            if target == "view":
                self.view.grab().save(path)
            elif target == "window":
                self.view.window().grab().save(path)
            elif target == "canvas":
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
                       "(view|window|canvas|mainwindow)"})
                return
            reply({"id": cid, "result": path})
        except Exception:
            reply({"id": cid, "error": traceback.format_exc()})

    def _devreload(self, cid, reply):
        """開発ソースのbridgeを再importして差し替え、ページを再読み込みする。"""
        if self._dev_reload is None:
            reply({"id": cid, "error": "devreload未設定(WEBENGINE_DEV_SRCなし)"})
            return
        try:
            bridge = self._dev_reload()
            channel = self.view.page().webChannel()
            if channel is not None:
                channel.registerObject("bridge", bridge)
            self._attach_report_handler()
            self.view.reload()
            reply({"id": cid, "result": True})
        except Exception:
            reply({"id": cid, "error": traceback.format_exc()})

    def _pyeval(self, cid, code, reply):
        """QGISプロセス内でPythonを実行する。

        式としてコンパイルできればeval、その結果を返す。文の場合はexecで実行し、
        名前空間の `result` 変数の値を返す(未設定ならNone)。
        同期的に実行するため長いコードはイベントループをブロックする点に注意。
        """
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

    def _js(self, script, callback=None):
        """runJavaScriptのQt5/6シグネチャ差を吸収する。

        Qt6: runJavaScript(script, worldId, callback)
        Qt5: runJavaScript(script, callback)
        """
        cb = callback or (lambda *_: None)
        if self._runjs_mode != "qt5":
            try:
                self.view.page().runJavaScript(script, 0, cb)
                self._runjs_mode = "qt6"
                return
            except TypeError:
                self._runjs_mode = "qt5"
        self.view.page().runJavaScript(script, cb)

    def _attach_report_handler(self):
        """console報告の受け口をページに接続する(devreload後も再呼び出し)。"""
        try:
            self.view.page().report = self._on_report
        except Exception:
            pass

    def _submit_eval(self, cid, expr, reply):
        """evalをJS側に投入。結果は console.log('__live ...') でプッシュされる。

        transport.send が飛行中に発行された console.log は喪失する(実測:
        .click() が起こした send 完了まで数十秒掛かり、その間の報告が全て
        届かなかった)。ただし喪失してもsendの返信自体は殺さないため、
        ドライバ側タイムアウトの直前まで定期的に再送すれば、send完了後の
        再送分が必ず届く(受信側はcid単位で冪等)。
        大きな結果は分割送信する(Chromiumのconsoleメッセージ長制限対策)。
        """
        key = json.dumps(str(cid))
        wrapper = (
            "(async()=>{let __o;try{__o={ok:true,v:await(" + expr + ")}"
            "}catch(e){__o={ok:false,e:String(e&&e.stack||e)}}"
            "let __s='';try{__s=JSON.stringify(__o)}catch(e){__s='{\"ok\":false,\"e\":\"unserializable\"}'}"
            "const __f=()=>{const __n=Math.max(1,Math.ceil(__s.length/4000));"
            "for(let __i=0;__i<__n;__i++)"
            "console.log('__live '+" + key + "+' '+__n+' '+__i+' '+__s.substr(__i*4000,4000));};"
            "__f();const __iv=setInterval(__f,3000);"
            "setTimeout(()=>clearInterval(__iv)," + str(EVAL_TIMEOUT_MS - 5000) + ");})()"
        )
        self.pending[cid] = {"remaining": EVAL_TIMEOUT_MS, "reply": reply}
        self._js(wrapper)

    def _on_report(self, msg):
        """'__live <cid> <n> <i> <chunk>' を受けて再構成しresults.jsonlに流す。"""
        try:
            cid, n_s, i_s, chunk = msg.split(" ", 3)
            n, i = int(n_s), int(i_s)
        except ValueError:
            return
        if cid not in self.pending:
            return
        ent = self._reports.setdefault(cid, {"n": n, "parts": {}})
        ent["parts"][i] = chunk
        if len(ent["parts"]) < ent["n"]:
            return
        self._reports.pop(cid, None)
        pent = self.pending.pop(cid)
        try:
            res = json.loads("".join(ent["parts"][k] for k in range(ent["n"])))
        except Exception:
            res = {"ok": False, "e": "bad report payload"}
        if res.get("ok"):
            pent["reply"]({"id": cid, "result": res.get("v")})
        else:
            pent["reply"]({"id": cid, "error": res.get("e")})

    def _reply(self, obj):
        os.makedirs(os.path.dirname(self.res_path), exist_ok=True)
        with open(self.res_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
