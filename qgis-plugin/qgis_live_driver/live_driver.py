"""QGISプロセスをファイル経由で外部制御するドライバ(スタンドアロン版)。

WebEngineを持たない任意のプラグイン/QGIS環境で使える制御面だけの実装。
webengine_plugin版との違い: viewを持たないため eval/devreload は未対応。
代わりに screenshot は iface.mapCanvas() の地図キャンバスをPNG化する。

環境変数 WEBENGINE_LIVE_DIR 設定時のみ有効。
live dir は WEBENGINE_LIVE_DIR/qgis-<pid>/<plugin_id>/。

コマンド形式(1行1JSON):
  {"id": 1, "type": "pyeval", "code": "iface.activeLayer().name()"}
  {"id": 2, "type": "screenshot", "path": "C:/.../shot.png"}  ← 地図キャンバス
"""

import json
import os
import queue
import threading
import traceback

from qgis.PyQt.QtCore import QTimer

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
    def __init__(self, live_dir, iface):
        self.iface = iface
        self.view = None  # WebEngineなし。ns経由でクライアントがUI有無を判定できる
        self.dir = live_dir
        self.cmd_path = os.path.join(live_dir, "commands.jsonl")
        self.res_path = os.path.join(live_dir, "results.jsonl")
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

    def submit(self, cmd, timeout=120.0):
        """別スレッドからコマンドを投入し、GUIスレッドでの実行結果を待って返す。

        @returns {"id":..., "result": v} or {"id":..., "error": e}
        """
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
            try:
                self._handle(cmd, reply=lambda obj: box.__setitem__("reply", obj))
            finally:
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
        cid = cmd.get("id")
        ctype = cmd.get("type", "eval")
        if ctype == "pyeval":
            self._pyeval(cid, cmd.get("code", ""), reply)
            return
        if ctype == "screenshot":
            path = cmd.get("path") or os.path.join(self.dir, f"shot-{cid}.png")
            # viewが無いので地図キャンバスを撮る(QgsMapCanvas.saveAsImage)
            canvas = self.iface.mapCanvas() if self.iface is not None else None
            if canvas is None:
                reply({"id": cid, "error": "no map canvas"})
                return
            canvas.saveAsImage(path)
            reply({"id": cid, "result": path})
            return
        reply({
            "id": cid,
            "error": f"type={ctype} unsupported: qgis_live_driver has no WebEngine view "
                     "(pyeval/screenshot only)",
        })

    def _pyeval(self, cid, code, reply=None):
        """QGISプロセス内でPythonを実行する。

        式としてコンパイルできればeval、その結果を返す。文の場合はexecで実行し、
        名前空間の `result` 変数の値を返す(未設定ならNone)。
        同期的に実行するため長いコードはイベントループをブロックする点に注意。
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
