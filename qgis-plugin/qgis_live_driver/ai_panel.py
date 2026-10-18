"""AIアシスタントドック — LLM APIを接続してQGISを対話操作するUI。

`プラグイン > QGIS Live Driver > AI アシスタント` で開く。
プロバイダ(OpenAI互換 / Gemini)・エンドポイント・APIキー・モデルを
設定すると、チャット経由でこのドライバのツール群(qgis_pyeval/
qgis_screenshot/...)をfunction callingでループ実行する。

構成:
  - 通信・スキーマ変換は ai_client.py(stdlibのみ・pytest対象)
  - ツール実行は LiveDriver.submit() → GUIスレッドのdispatch。
    リモート制御トグルOFFでも __init__ 側が用意する内部ドライバで動く
  - ネットワーク/ツール実行はワーカースレッド、UI更新はシグナル経由
  - APIキーはOSの資格情報ストアに保存される(credential_store.py)。
    ストア書込みに失敗した場合は平文保存せずエラーにする。
    エンドポイント/モデルはQSettingsにプロバイダごと別キーで保持する
"""

import html
import json
import re
import threading

from qgis.PyQt.QtCore import Qt, QSettings, pyqtSignal
from qgis.PyQt.QtGui import QStandardItem, QStandardItemModel
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDockWidget,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
    QLabel,
)

from . import ai_client, credential_store

_SETTING = "qgis_live_driver/ai_{}"
_PROVIDER_IDS = list(ai_client.PROVIDERS.keys())
_MODEL_HINT = ("「取得」でエンドポイントのモデル一覧を表示。"
               "括弧内は価格(入力/出力, $/1Mトークン, 参考値)。")


def _esc(t):
    return html.escape(t or "").replace("\n", "<br>")


class _Input(QPlainTextEdit):
    """Ctrl+Enterで送信する入力欄。"""
    sig_submit = pyqtSignal()

    def keyPressEvent(self, e):
        if (e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
                and e.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.sig_submit.emit()
            return
        super().keyPressEvent(e)


class AiPanel(QDockWidget):
    sig_append = pyqtSignal(str, str)    # (kind, text) 表示はGUIスレッドで整形
    sig_status = pyqtSignal(str)
    sig_busy = pyqtSignal(bool)
    sig_models = pyqtSignal(list, str)   # (models, error) モデル一覧取得結果

    def __init__(self, iface, get_driver, parent=None):
        super().__init__("AI アシスタント", parent or iface.mainWindow())
        self.setObjectName("QgisLiveAiPanel")
        self.iface = iface
        self._get_driver = get_driver
        self._history = []      # [{"role": "user"|"assistant", "content": str}]
        self._model_infos = {}  # {id: ai_client.model_info()}
        self._busy = False
        self._alive = True
        self.destroyed.connect(self._on_destroyed)

        root = QWidget(self)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(6, 6, 6, 6)

        # ---- API設定 ----
        box = QGroupBox("API設定", root)
        form = QFormLayout(box)
        self.cmb_provider = QComboBox(box)
        for pid in _PROVIDER_IDS:
            self.cmb_provider.addItem(ai_client.PROVIDERS[pid]["label"], pid)
        self.ed_endpoint = QLineEdit(box)
        self.ed_key = QLineEdit(box)
        self.ed_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.lbl_keystore = QLabel(credential_store.backend_label(), box)
        self.lbl_keystore.setStyleSheet("color:#666; font-size:11px")
        self.lbl_keystore.setWordWrap(True)
        self.cmb_model = QComboBox(box)
        self.cmb_model.setEditable(True)
        self.cmb_model.setToolTip(
            "使用するモデル。「取得」でエンドポイントの一覧を表示。\n"
            "括弧内は1Mトークンあたりの価格(入力/出力, $)。\n"
            "「画像入力可」グループのモデルはスクリーンショット送信に対応。")
        model_row = QWidget(box)
        mr = QHBoxLayout(model_row)
        mr.setContentsMargins(0, 0, 0, 0)
        self.btn_models = QPushButton("取得", model_row)
        self.btn_models.setToolTip(
            "エンドポイントからモデル一覧を取得 (GET {base}/models)")
        mr.addWidget(self.cmb_model, 1)
        mr.addWidget(self.btn_models)
        self.lbl_model_info = QLabel(_MODEL_HINT, box)
        self.lbl_model_info.setStyleSheet("color:#666; font-size:11px")
        self.lbl_model_info.setWordWrap(True)
        self.chk_vision = QCheckBox(
            "スクリーンショットを画像として送信 (vision対応モデル)", box)
        self.chk_vision.setChecked(True)
        form.addRow("プロバイダ", self.cmb_provider)
        form.addRow("エンドポイント", self.ed_endpoint)
        form.addRow("APIキー", self.ed_key)
        form.addRow("キー保存先", self.lbl_keystore)
        form.addRow("モデル", model_row)
        form.addRow("", self.lbl_model_info)
        form.addRow("", self.chk_vision)
        lay.addWidget(box)

        # ---- チャット表示 ----
        self.view = QTextBrowser(root)
        self.view.setOpenExternalLinks(True)
        lay.addWidget(self.view, 1)

        # ---- 入力行 ----
        self.input = _Input(root)
        self.input.setPlaceholderText(
            "指示を入力 (Ctrl+Enterで送信)。例: 現在のレイヤー一覧を教えて")
        self.input.setMaximumHeight(64)
        lay.addWidget(self.input)

        row = QHBoxLayout()
        self.btn_send = QPushButton("送信", root)
        self.btn_clear = QPushButton("履歴クリア", root)
        self.lbl_status = QLabel("", root)
        row.addWidget(self.btn_send)
        row.addWidget(self.btn_clear)
        row.addWidget(self.lbl_status, 1)
        lay.addLayout(row)

        self.setWidget(root)
        self._load_settings()
        self._snapshot_fields()

        self.cmb_provider.currentIndexChanged.connect(
            self._on_provider_changed)
        self.cmb_model.activated.connect(self._on_model_activated)
        self.cmb_model.currentTextChanged.connect(
            self._on_model_text_changed)
        self.btn_models.clicked.connect(self._fetch_models)
        self.btn_send.clicked.connect(self._send)
        self.btn_clear.clicked.connect(self._clear)
        self.input.sig_submit.connect(self._send)
        self.sig_append.connect(self._append)
        self.sig_status.connect(self.lbl_status.setText)
        self.sig_busy.connect(self._set_busy)
        self.sig_models.connect(self._on_models)

    # ---- 設定の永続化 ----

    def _provider(self):
        return self.cmb_provider.currentData() or "openai"

    def _load_settings(self):
        s = QSettings()
        pid = s.value(_SETTING.format("provider"), "openai")
        idx = (_PROVIDER_IDS.index(pid) if pid in _PROVIDER_IDS else 0)
        self.cmb_provider.setCurrentIndex(idx)
        self._load_provider_fields()
        self.chk_vision.setChecked(
            str(s.value(_SETTING.format("vision"), "true")).lower()
            in ("1", "true"))

    def _load_provider_fields(self):
        """現在のプロバイダの保存値(無ければ既定)を入力欄へ反映する。"""
        s = QSettings()
        pid = self._provider()
        d = ai_client.PROVIDERS[pid]
        # 旧キー(プロバイダ無し)からの移行: 新キーが無ければ読む
        legacy = lambda k, dv: (  # noqa: E731
            s.value(_SETTING.format(f"{pid}_{k}"), None)
            if s.value(_SETTING.format(f"{pid}_{k}"), None) is not None
            else s.value(_SETTING.format(k), dv))
        ep = legacy("endpoint", d["base"]) if pid == "openai" \
            else s.value(_SETTING.format(f"{pid}_endpoint"), d["base"])
        # APIキーはOS資格情報ストアを優先し、
        # 無ければ従来のQSettings平文値(移行元)を読む
        key = credential_store.get_secret(f"ai_{pid}_api_key")
        if key is None:
            key = (legacy("api_key", "") if pid == "openai"
                   else s.value(_SETTING.format(f"{pid}_api_key"), ""))
        model = legacy("model", d["model"]) if pid == "openai" \
            else s.value(_SETTING.format(f"{pid}_model"), d["model"])
        self.ed_endpoint.setText(ep)
        self.ed_endpoint.setPlaceholderText(d["endpoint_hint"])
        self.ed_key.setText(key)
        self.ed_key.setPlaceholderText(d["key_hint"])
        self.cmb_model.clear()
        # 既定エンドポイント利用時は推奨モデル(種別・参考価格付き)を
        # 予めコンボへ載せる。カスタムエンドポイント(Ollama等)では
        # 一覧が異なるため載せず「取得」で実一覧を取る運用にする。
        if ep == d["base"]:
            infos = [ai_client.model_info({"id": m})
                     for m in ai_client.SUGGESTED_MODELS.get(pid, ())]
            self._set_model_items(infos, keep_text=model)
        else:
            self._model_infos = {}
        self.cmb_model.setEditText(model)
        self.cmb_model.lineEdit().setPlaceholderText(d["model"])
        self._update_model_info()

    def _save_settings(self):
        s = QSettings()
        pid = self._provider()
        s.setValue(_SETTING.format("provider"), pid)
        s.setValue(_SETTING.format(f"{pid}_endpoint"),
                   self.ed_endpoint.text())
        self._save_provider_key(pid, self.ed_key.text())
        s.setValue(_SETTING.format(f"{pid}_model"),
                   self._current_model())
        s.setValue(_SETTING.format("vision"), self.chk_vision.isChecked())

    def _save_provider_key(self, pid, key):
        """APIキーをOS資格情報ストアへ保存する。

        QSettingsにはいかなる場合も平文を残さない。ストア書込みに
        失敗した場合はエラー表示する(平文フォールバックはしない)。
        その場合でも入力欄の値は残るため今回のセッション内では
        送信できるが、次回起動時は再入力が必要になる。
        """
        s = QSettings()
        name = f"ai_{pid}_api_key"
        if key:
            ok = credential_store.set_secret(name, key)
        else:
            ok = credential_store.delete_secret(name)
        s.remove(_SETTING.format(f"{pid}_api_key"))
        if ok:
            s.setValue(_SETTING.format(f"{pid}_key_store"),
                       credential_store.backend())
        else:
            s.remove(_SETTING.format(f"{pid}_key_store"))
            self._append(
                "error",
                f"APIキーをOS資格情報ストアに保存できませんでした"
                f" (backend={credential_store.backend()})。"
                "平文での保存はしません。このセッション内では"
                "入力中のキーを使えますが、次回起動時は再入力が必要です。")
        return ok

    def _on_provider_changed(self, _idx):
        """切替前のプロバイダの入力値を保存し、新プロバイダの値を読み込む。

        currentIndexChanged 時点で combo は既に新プロバイダを指すため、
        直前のプロバイダを保持しておく必要がある。
        """
        prev = getattr(self, "_prev_provider", None)
        if prev is not None and prev != self._provider():
            s = QSettings()
            s.setValue(_SETTING.format(f"{prev}_endpoint"),
                       self._prev_endpoint)
            self._save_provider_key(prev, self._prev_key)
            s.setValue(_SETTING.format(f"{prev}_model"),
                       self._prev_model)
        self._load_provider_fields()
        self._snapshot_fields()

    def _snapshot_fields(self):
        self._prev_provider = self._provider()
        self._prev_endpoint = self.ed_endpoint.text()
        self._prev_key = self.ed_key.text()
        self._prev_model = self._current_model()

    # ---- モデル選択 ----

    def _current_model(self):
        """選択中のモデルID。装飾付き表示("id   $x/$y")や
        グループ見出しが入っていてもIDだけを返す。"""
        data = self.cmb_model.currentData()
        if data:
            return str(data)
        t = self.cmb_model.currentText().strip()
        if not t or t.startswith("──"):
            return ""
        # モデルIDは空白を含まないため、表示装飾(空白2つ以上+価格)は剥がす
        return re.split(r"\s{2,}", t, maxsplit=1)[0].strip()

    def _set_model_items(self, infos, keep_text=None):
        """モデルコンボを種別グループ付きで再構築する。

        @returns 設定したモデル数
        """
        cur = (keep_text if keep_text is not None
               else self._current_model())
        self._model_infos = {i["id"]: i for i in infos}
        mdl = QStandardItemModel(self.cmb_model)
        n = 0
        for kind, label in ai_client.MODEL_KINDS:
            entries = [i for i in infos if i["kind"] == kind]
            if not entries:
                continue
            hdr = QStandardItem(f"── {label} ──")
            hdr.setEnabled(False)          # 選択不可の見出し行
            f = hdr.font()
            f.setBold(True)
            hdr.setFont(f)
            mdl.appendRow(hdr)
            for i in entries:
                it = QStandardItem(ai_client.model_label(i))
                it.setData(i["id"], Qt.ItemDataRole.UserRole)
                it.setToolTip(ai_client.model_tooltip(i))
                mdl.appendRow(it)
                n += 1
        self.cmb_model.setModel(mdl)
        idx = self.cmb_model.findData(cur) if cur else -1
        if cur and idx >= 0:
            self.cmb_model.setCurrentIndex(idx)
            self.cmb_model.setEditText(cur)  # IDだけをline editに表示
        elif cur:
            self.cmb_model.setEditText(cur)
        self._update_model_info()
        return n

    def _on_model_activated(self, idx):
        """項目選択時、line editには装飾無しのIDだけを残す。"""
        data = self.cmb_model.itemData(idx)
        if data:
            self.cmb_model.setEditText(str(data))

    def _on_model_text_changed(self, _text):
        self._update_model_info()

    def _update_model_info(self):
        """モデル欄の下に選択中モデルの種別・価格等を表示する。"""
        info = self._model_infos.get(self._current_model())
        if not info:
            self.lbl_model_info.setText(_MODEL_HINT)
            return
        parts = [ai_client.MODEL_KIND_LABELS.get(
            info["kind"], info["kind"])]
        if info.get("price_desc"):
            src = "API" if info["price_src"] == "api" else "参考"
            parts.append(f"{info['price_desc']} ({src})")
        ctx = ai_client.fmt_tokens(info.get("context"))
        if ctx:
            parts.append(f"コンテキスト {ctx}")
        if info["kind"] == "chat":
            parts.append("画像入力非対応の可能性(スクショ送信には"
                         "「画像入力可」モデルを選択)")
        elif info["kind"] != "chat_vision":
            parts.append("チャット用途には使えません")
        self.lbl_model_info.setText(" / ".join(parts))

    # ---- 表示 ----

    _STYLE = {
        "user": "#0759c7",
        "assistant": "#222222",
        "tool": "#666666",
        "error": "#b00020",
    }

    def _append(self, kind, text):
        color = self._STYLE.get(kind, "#222")
        label = {"user": "あなた", "assistant": "AI",
                 "tool": "tool", "error": "error"}.get(kind, kind)
        if kind == "tool":
            body = f"<pre style='margin:2px 0'>{_esc(text)}</pre>"
        else:
            body = _esc(text)
        self.view.append(
            f"<div style='margin:6px 0'>"
            f"<b style='color:{color}'>[{label}]</b> "
            f"<span style='color:{color}'>{body}</span></div>")

    def _set_busy(self, busy):
        self._busy = busy
        self.btn_send.setEnabled(not busy)
        self.input.setEnabled(not busy)
        if busy:
            self.lbl_status.setText("実行中…")

    def _clear(self):
        self._history.clear()
        self.view.clear()

    def _on_destroyed(self):
        self._alive = False

    def _emit(self, sig, *args):
        """ワーカースレッドからのemit。パネル消去後は無視。"""
        if not self._alive:
            return
        try:
            sig.emit(*args)
        except RuntimeError:
            self._alive = False

    def hideEvent(self, e):
        self._save_settings()
        super().hideEvent(e)

    # ---- モデル一覧取得 ----

    def _fetch_models(self):
        """「取得」ボタン: {base}/models から一覧を取り込む。"""
        pid = self._provider()
        base = (self.ed_endpoint.text().strip()
                or ai_client.PROVIDERS[pid]["base"])
        key = self.ed_key.text().strip()
        self.btn_models.setEnabled(False)
        self.lbl_status.setText("モデル一覧取得中…")
        threading.Thread(
            target=self._models_run, args=(pid, base, key),
            daemon=True, name="qgis-ai-models").start()

    def _models_run(self, pid, base, key):
        try:
            infos = ai_client.list_model_infos(pid, base, key)
            self._emit(self.sig_models, infos, "")
        except Exception as e:
            self._emit(self.sig_models, [], str(e))

    def _on_models(self, infos, error):
        self.btn_models.setEnabled(True)
        self.lbl_status.setText("")
        if error:
            self._append("error", f"モデル一覧の取得に失敗: {error}")
            return
        n = self._set_model_items(infos)
        self._append("tool", f"モデル一覧を{n}件取得しました")

    # ---- 送信/エージェントループ ----

    def _send(self):
        text = self.input.toPlainText().strip()
        if not text or self._busy:
            return
        driver = self._get_driver()  # 生成を伴うため必ずGUIスレッドで取得
        if driver is None:
            self._append("error", "live driverを用意できませんでした")
            return
        plugins = []
        try:
            import qgis.utils
            plugins = sorted(qgis.utils.plugins.keys())
        except Exception:
            pass
        pid = self._provider()
        cfg = {
            "provider": pid,
            "base": (self.ed_endpoint.text().strip()
                     or ai_client.PROVIDERS[pid]["base"]),
            "key": self.ed_key.text().strip(),
            "model": (self._current_model()
                      or ai_client.PROVIDERS[pid]["model"]),
            "vision": self.chk_vision.isChecked(),
        }
        self._save_settings()
        self.input.clear()
        self._append("user", text)
        self.sig_busy.emit(True)
        threading.Thread(
            target=self._agent_run,
            args=(driver, cfg, plugins, text),
            daemon=True, name="qgis-ai-agent").start()

    def _agent_run(self, driver, cfg, plugins, user_text):
        """ワーカースレッド: API呼出 + ツール実行のループ。"""
        try:
            prov = ai_client.get_provider(cfg["provider"])
        except ai_client.ApiError as e:
            self._emit(self.sig_append, "error", str(e))
            self._emit(self.sig_status, "")
            self._emit(self.sig_busy, False)
            return
        system = ai_client.system_prompt(plugins)
        msgs = prov.build_messages(system, self._history, user_text)
        final_text = ""
        try:
            for _ in range(ai_client.MAX_TOOL_ROUNDS):
                self._emit(self.sig_status, "API応答待ち…")
                data = prov.send(cfg["base"], cfg["key"], cfg["model"],
                                 system, msgs)
                turn = prov.parse(data)
                if turn["text"]:
                    self._emit(self.sig_append, "assistant", turn["text"])
                if not turn["calls"]:
                    final_text = turn["text"]
                    break
                results = [self._run_tool(driver, cfg, c["name"], c["args"])
                           for c in turn["calls"]]
                prov.append_exchange(msgs, turn, results)
            else:
                final_text = "(ツール往復の上限に達しました)"
                self._emit(self.sig_append, "error", final_text)
            # 会話履歴はテキスト対のみ保持(ツール詳細は畳む)
            self._history.append({"role": "user", "content": user_text})
            if final_text:
                self._history.append(
                    {"role": "assistant", "content": final_text})
        except ai_client.ApiError as e:
            self._emit(self.sig_append, "error", str(e))
        except Exception:
            import traceback
            self._emit(self.sig_append, "error", traceback.format_exc())
        finally:
            self._emit(self.sig_status, "")
            self._emit(self.sig_busy, False)

    def _run_tool(self, driver, cfg, name, args):
        """ツール呼び出しをドライバにdispatchして正規化結果を返す。

        @returns {"text": str, "image": path|None}
        """
        try:
            cmd = ai_client.tool_to_command(name, args)
        except ai_client.ApiError as e:
            self._emit(self.sig_append, "error", str(e))
            return {"text": f"ERROR: {e}", "image": None}
        disp = {k: v for k, v in cmd.items() if k != "type"}
        self._emit(self.sig_append, "tool",
                   f"{name} {json.dumps(disp, ensure_ascii=False)}")
        if cmd["type"] == "screenshot" and not cmd.get("path"):
            cmd["path"] = ai_client.screenshot_temp_path()
        self._emit(self.sig_status, f"{name} 実行中…")
        rep = driver.submit(cmd)
        text = ai_client.reply_to_text(rep)
        self._emit(self.sig_append, "tool",
                   f"→ {text[:2000]}"
                   + ("…" if len(text) > 2000 else ""))
        # vision有効時はスクリーンショットを画像として返す
        image = None
        if (cmd["type"] == "screenshot" and "error" not in rep
                and cfg["vision"]):
            image = rep.get("result")
        return {"text": text, "image": image}


def show_panel(iface, get_driver, panel):
    """ドックを(必要なら生成して)表示し、インスタンスを返す。"""
    if panel is None:
        panel = AiPanel(iface, get_driver)
        iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, panel)
    panel.show()
    panel.raise_()
    return panel
