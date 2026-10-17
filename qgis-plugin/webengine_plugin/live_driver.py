"""ファイル経由のライブドライバ。

QtWebEngineのCDP実装(Runtimeドメイン)がこの環境では応答しないため、
プラグイン側でQTimerポーリングし commands.jsonl に書き込まれたJSを
view.page().runJavaScript() で実行して results.jsonl に結果を返す。

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
import traceback

from qgis.PyQt.QtCore import QTimer

EVAL_TIMEOUT_MS = 120000
POLL_MS = 200


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
        self._runjs_mode = None  # "qt6" | "qt5"
        self._ns = {"iface": iface, "view": view, "driver": self}
        self._dev_reload = dev_reload  # callable -> 新しいbridgeオブジェクト or None
        os.makedirs(live_dir, exist_ok=True)

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

        # evalコマンドの結果をグローバル辞書経由で回収
        for cid in list(self.pending):
            probe = f"window.__live_res&&window.__live_res[{json.dumps(str(cid))}]"
            self._js(probe, lambda res, cid=cid: self._collect(cid, res))
            if self.pending[cid] <= 0:
                self._reply({"id": cid, "error": "eval timeout"})
                self.pending.pop(cid, None)
            else:
                self.pending[cid] -= POLL_MS

    def _handle(self, cmd):
        cid = cmd.get("id")
        ctype = cmd.get("type", "eval")
        if ctype == "screenshot":
            path = cmd.get("path") or os.path.join(self.dir, f"shot-{cid}.png")
            self.view.grab().save(path)
            self._reply({"id": cid, "result": path})
            return
        if ctype == "eval":
            expr = cmd.get("expression", "")
            # Promiseも結果として受け取れるようasyncで包み、グローバル辞書に退避。
            # cidはクライアント生成の任意文字列(ハイフン等を含みうる)なので
            # 変数名ではなく辞書キーとして扱う
            key = json.dumps(str(cid))
            wrapper = (
                "(async()=>{try{const __r=await(" + expr + ");"
                "(window.__live_res=window.__live_res||{})[" + key + "]={ok:true,v:__r};"
                "}catch(e){"
                "(window.__live_res=window.__live_res||{})[" + key + "]={ok:false,e:String(e&&e.stack||e)}"
                "}})()"
            )
            self.pending[cid] = EVAL_TIMEOUT_MS
            self._js(wrapper)
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

    def _collect(self, cid, res):
        if cid not in self.pending or res is None:
            return
        self.pending.pop(cid, None)
        if res.get("ok"):
            self._reply({"id": cid, "result": res.get("v")})
        else:
            self._reply({"id": cid, "error": res.get("e")})

    def _reply(self, obj):
        os.makedirs(os.path.dirname(self.res_path), exist_ok=True)
        with open(self.res_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
