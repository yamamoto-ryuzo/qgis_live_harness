"""ファイル経由のライブドライバ。

QtWebEngineのCDP実装(Runtimeドメイン)がこの環境では応答しないため、
プラグイン側でQTimerポーリングし commands.jsonl に書き込まれたJSを
view.page().runJavaScript() で実行して results.jsonl に結果を返す。

環境変数 WEBENGINE_LIVE_DIR が設定されている場合のみ有効化される。

コマンド形式(1行1JSON):
  {"id": 1, "type": "eval", "expression": "document.title"}
  {"id": 2, "type": "screenshot", "path": "C:/.../shot.png"}
結果形式:
  {"id": 1, "result": <JSON化可能な値>}  or  {"id": 1, "error": "..."}
"""

import json
import os

from qgis.PyQt.QtCore import QTimer

EVAL_TIMEOUT_MS = 120000
POLL_MS = 200


class LiveDriver:
    def __init__(self, view, live_dir):
        self.view = view
        self.dir = live_dir
        self.cmd_path = os.path.join(live_dir, "commands.jsonl")
        self.res_path = os.path.join(live_dir, "results.jsonl")
        self.offset = 0
        self.pending = {}  # cid -> remaining ms
        self._runjs_mode = None  # "qt6" | "qt5"
        os.makedirs(live_dir, exist_ok=True)

        self.timer = QTimer(view)
        self.timer.timeout.connect(self._poll)
        self.timer.start(POLL_MS)

    def _poll(self):
        if os.path.exists(self.cmd_path):
            # ファイルが作り直されるとoffsetが実サイズを超えて読み飛ばすため補正
            if os.path.getsize(self.cmd_path) < self.offset:
                self.offset = 0
            with open(self.cmd_path, "r", encoding="utf-8") as f:
                f.seek(self.offset)
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        self._handle(json.loads(line))
                    except Exception as e:
                        self._reply({"id": None, "error": repr(e)})
                self.offset = f.tell()

        # evalコマンドの結果をグローバル変数経由で回収
        for cid in list(self.pending):
            probe = f"window.__live_res_{cid}"
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
            # Promiseも結果として受け取れるようasyncで包み、グローバルに退避
            wrapper = (
                "(async()=>{try{const __r=await(" + expr + ");"
                f"window.__live_res_{cid}={{ok:true,v:__r}};"
                "}catch(e){"
                f"window.__live_res_{cid}={{ok:false,e:String(e&&e.stack||e)}}"
                "}})()"
            )
            self.pending[cid] = EVAL_TIMEOUT_MS
            self._js(wrapper)
            return
        self._reply({"id": cid, "error": f"unknown type: {ctype}"})

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
