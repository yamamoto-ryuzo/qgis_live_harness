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
結果形式:
  {"id": 1, "result": <JSON化可能な値>}  or  {"id": 1, "error": "..."}

pyeval はQGISプロセス内のPythonを同期実行する。式ならeval、文ならexecで実行し
(execの場合 `result` 変数への代入が返却値になる)。名前空間には iface/view/driver が
ありセッション中持続する。任意コード実行なので検証モード(WEBENGINE_LIVE_DIR
設定時)のみ有効。

devreload は WEBENGINE_DEV_SRC 指定時のみ有効。リポジトリ内のbridge等を
再importしてWebChannelのbridgeオブジェクトを差し替え、ページを再読み込みする。
deploy/reloadPluginなしでコード変更を反映できる(プラグイン本体側の
main_plugin/live_driver 等の変更は対象外。それらはlive:reloadを使う)。
"""

import json
import os
import time
import traceback

from qgis.PyQt.QtCore import QTimer

EVAL_TIMEOUT_MS = 120000
POLL_MS = 200
# キューでこれだけ滞留したevalは、クライアント側が既にタイムアウトして
# 新idでリトライ済みとみなし、実行せず破棄する(遅延clickの多重実行防止)
QUEUE_STALE_MS = 30000


def _to_jsonable(v):
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, dict):
        return {str(k): _to_jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [_to_jsonable(x) for x in v]
    return repr(v)


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
        self.pending = {}  # cid -> remaining ms
        self._queue = []  # (cid, expr) eval送信キュー。sendが飛んでいる間は投入しない
        self._runjs_mode = None  # "qt6" | "qt5"
        self._ns = {"iface": iface, "view": view, "driver": self}
        self._dev_reload = dev_reload  # callable -> 新しいbridgeオブジェクト or None
        os.makedirs(live_dir, exist_ok=True)

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
                    self._handle(json.loads(line))
                except Exception as e:
                    self._reply({"id": None, "error": repr(e)})

        # evalのタイムアウト管理のみ(runJavaScriptプローブはwedgeを起こすため廃止)
        for cid in list(self.pending):
            self.pending[cid] -= POLL_MS
            if self.pending[cid] <= 0:
                self._reply({"id": cid, "error": "eval timeout"})
                self.pending.pop(cid, None)

        # 直列送信: pendingのevalが無い時だけ次を投入する。
        # sendが飛んでいる最中にrunJavaScriptを実行するとそのsendの返信が
        # 喪失する(Qt6.8のWebChannel transport制約)ため、evalは1件ずつ処理する
        if not self.pending and self._queue:
            cid, expr, enq = self._queue.pop(0)
            if (time.monotonic() - enq) * 1000 > QUEUE_STALE_MS:
                self._reply({"id": cid, "error": "eval dropped: queue stale"})
            else:
                self._submit_eval(cid, expr)

    def _handle(self, cmd):
        cid = cmd.get("id")
        ctype = cmd.get("type", "eval")
        if ctype == "screenshot":
            path = cmd.get("path") or os.path.join(self.dir, f"shot-{cid}.png")
            self.view.grab().save(path)
            self._reply({"id": cid, "result": path})
            return
        if ctype == "eval":
            self._queue.append(
                (cmd.get("id"), cmd.get("expression", ""), time.monotonic()))
            return
        if ctype == "pyeval":
            self._pyeval(cid, cmd.get("code", ""))
            return
        if ctype == "devreload":
            self._devreload(cid)
            return
        self._reply({"id": cid, "error": f"unknown type: {ctype}"})

    def _devreload(self, cid):
        """開発ソースのbridgeを再importして差し替え、ページを再読み込みする。"""
        if self._dev_reload is None:
            self._reply({"id": cid, "error": "devreload未設定(WEBENGINE_DEV_SRCなし)"})
            return
        try:
            bridge = self._dev_reload()
            channel = self.view.page().webChannel()
            if channel is not None:
                channel.registerObject("bridge", bridge)
            self._attach_report_handler()
            self.view.reload()
            self._reply({"id": cid, "result": True})
        except Exception:
            self._reply({"id": cid, "error": traceback.format_exc()})

    def _pyeval(self, cid, code):
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
            self._reply({"id": cid, "result": _to_jsonable(res)})
        except Exception:
            self._reply({"id": cid, "error": traceback.format_exc()})

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

    def _submit_eval(self, cid, expr):
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
        self.pending[cid] = EVAL_TIMEOUT_MS
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
        self.pending.pop(cid, None)
        try:
            res = json.loads("".join(ent["parts"][k] for k in range(ent["n"])))
        except Exception:
            res = {"ok": False, "e": "bad report payload"}
        if res.get("ok"):
            self._reply({"id": cid, "result": res.get("v")})
        else:
            self._reply({"id": cid, "error": res.get("e")})

    def _reply(self, obj):
        os.makedirs(os.path.dirname(self.res_path), exist_ok=True)
        with open(self.res_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
