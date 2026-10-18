"""AIアシスタントドック — LLM APIを接続してQGISを対話操作するUI。

`プラグイン > QGIS Live Driver > AI アシスタント` で開く。
プロバイダ(OpenAI互換 / Gemini / GitHub Copilot)・エンドポイント・
APIキー・モデルを設定すると、チャット経由でこのドライバのツール群
(qgis_pyeval/qgis_screenshot/...)をfunction callingでループ実行する。
GitHub Copilot選択時は「GitHubでサインイン」ボタンでOAuthデバイス
フローによるトークン取得ができる。

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
import os
import re
import threading
import time

from qgis.PyQt.QtCore import Qt, QSettings, QUrl, pyqtSignal
from qgis.PyQt.QtGui import (
    QDesktopServices,
    QStandardItem,
    QStandardItemModel,
    QTextDocument,
)
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
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


def _md(t):
    """Markdown → 本文用HTML(QTextDocument.toHtml()のbody中身)。"""
    doc = QTextDocument()
    doc.setMarkdown(t or "")
    h = doc.toHtml()
    m = re.search(r"<body[^>]*>(.*)</body>", h, re.S)
    return m.group(1) if m else h


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
    sig_instructions = pyqtSignal()      # ai_*ツールが指示書を更新した
    sig_agent_changed = pyqtSignal(str)  # ai_select_agentで選択切替(id)
    sig_confirm = pyqtSignal(str, str)   # ツール確認要求(name, args表示)
    sig_status = pyqtSignal(str)
    sig_busy = pyqtSignal(bool)
    sig_models = pyqtSignal(list, str)   # (models, error) モデル一覧取得結果
    sig_signin = pyqtSignal(str, str)    # (pid, token) デバイスフロー完了
    sig_open_url = pyqtSignal(str)       # ブラウザで開くURL(GUIスレッドで実行)

    def __init__(self, iface, get_driver, parent=None):
        super().__init__("AI アシスタント", parent or iface.mainWindow())
        self.setObjectName("QgisLiveAiPanel")
        self.iface = iface
        self._get_driver = get_driver
        self._history = []      # [{"role": "user"|"assistant", "content": str}]
        # チャットセッション。先頭は常に「現在のチャット」(コンボindexと一致)。
        # 過去チャットは {"title","history","html"} として後ろに積む
        self._sessions = [{"title": "現在のチャット",
                           "history": self._history, "html": "",
                           "agent": None}]
        self._open_chat = 0     # 表示中のセッションindex
        self._model_infos = {}  # {id: ai_client.model_info()}
        self._busy = False
        self._abort = False         # 中断ボタンで立つ。ループ境界で観測
        self._alive = True
        self._signin_abort = False
        self._confirm_event = threading.Event()
        self._confirm_result = False
        self._mcp_done = False       # 外部MCPの発見を済ませたか
        self._mcp_sessions = {}      # {name: McpSession} 切断用に保持
        self._plugins = []           # 直近送信時のプラグイン一覧(ctx推定用)
        self._usage = {"in": 0, "out": 0, "last": 0}  # API応答usage累計
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
        self.chk_confirm = QCheckBox(
            "ツール実行の前に確認する", box)
        self.chk_confirm.setToolTip(
            "ONにするとツール呼び出しごとに実行可否を確認する。\n"
            "任意コード実行(pyeval)を自動で回したくない場合に。")
        # エージェント(常時注入する指示書 ~/.qgis-live/agents/*.md)
        agent_row = QWidget(box)
        ar = QHBoxLayout(agent_row)
        ar.setContentsMargins(0, 0, 0, 0)
        self.cmb_agent = QComboBox(box)
        self.cmb_agent.setToolTip(
            "常時注入する指示書(エージェント)。\n"
            "~/.qgis-live/agents/*.md を列挙。「編集」で作成・修正")
        self.btn_agent_edit = QPushButton("編集", agent_row)
        self.btn_agent_edit.setToolTip(
            "エージェント指示書(.md)の作成・編集・削除")
        ar.addWidget(self.cmb_agent, 1)
        ar.addWidget(self.btn_agent_edit)
        form.addRow("エージェント", agent_row)
        # スキル(オンデマンド手順書 ~/.qgis-live/skills/*.md。
        # 全件がプロンプトの一覧に載るため選択ではなく一覧表示)
        skill_row = QWidget(box)
        sk = QHBoxLayout(skill_row)
        sk.setContentsMargins(0, 0, 0, 0)
        self.cmb_skill = QComboBox(box)
        self.cmb_skill.setToolTip(
            "オンデマンドの手順書。全件がプロンプトの一覧に載り、\n"
            "モデルが必要時に qgis_pyeval の open() で本文を読む。\n"
            "~/.qgis-live/skills/*.md を列挙。「編集」で作成・修正")
        self.btn_skill_edit = QPushButton("編集", skill_row)
        self.btn_skill_edit.setToolTip(
            "スキル指示書(.md)の作成・編集・削除")
        sk.addWidget(self.cmb_skill, 1)
        sk.addWidget(self.btn_skill_edit)
        form.addRow("スキル", skill_row)
        # 外部MCPサーバ(~/.qgis-live/mcp_servers.json)
        mcp_row = QWidget(box)
        mk = QHBoxLayout(mcp_row)
        mk.setContentsMargins(0, 0, 0, 0)
        self.lbl_mcp = QLabel("未設定", mcp_row)
        self.lbl_mcp.setStyleSheet("color:#666")
        self.btn_mcp = QPushButton("設定", mcp_row)
        self.btn_mcp.setToolTip(
            "外部MCPサーバの設定(mcp_servers.json)を編集。\n"
            "command=stdio起動 / url=Streamable HTTP。\n"
            "発見したツールは mcp_<サーバ>__<ツール> として使える")
        mk.addWidget(self.lbl_mcp, 1)
        mk.addWidget(self.btn_mcp)
        form.addRow("MCP", mcp_row)
        # Copilot選択時のみ見せるOAuthデバイスフロー行
        self.w_signin = QWidget(box)
        sr = QHBoxLayout(self.w_signin)
        sr.setContentsMargins(0, 0, 0, 0)
        self.btn_signin = QPushButton("GitHubでサインイン", self.w_signin)
        self.btn_signin.setToolTip(
            "OAuthデバイスフローでGitHubトークンを取得しAPIキー欄に設定。\n"
            "表示されるコードをブラウザ(github.com/login/device)で入力。\n"
            "GitHub Copilotの契約があるアカウントが必要。")
        sr.addWidget(self.btn_signin)
        lbl = QLabel("Copilot契約のGitHubアカウント", self.w_signin)
        lbl.setStyleSheet("color:#666; font-size:11px")
        sr.addWidget(lbl, 1)
        self.w_signin.setVisible(False)
        form.addRow("プロバイダ", self.cmb_provider)
        form.addRow("エンドポイント", self.ed_endpoint)
        form.addRow("APIキー", self.ed_key)
        form.addRow("", self.w_signin)
        form.addRow("キー保存先", self.lbl_keystore)
        form.addRow("モデル", model_row)
        form.addRow("", self.lbl_model_info)
        form.addRow("", self.chk_vision)
        form.addRow("", self.chk_confirm)
        lay.addWidget(box)
        self.box_api = box

        # ---- チャット履歴 ----
        crow = QHBoxLayout()
        self.btn_settings = QPushButton("⚙", root)
        self.btn_settings.setCheckable(True)
        self.btn_settings.setFixedWidth(32)
        self.btn_settings.setToolTip(
            "API設定の表示/非表示を切り替える")
        crow.addWidget(self.btn_settings)
        self.btn_newchat = QPushButton("新しいチャット", root)
        self.btn_newchat.setToolTip(
            "現在のチャットを履歴へ保存し、新規チャットを開始。\n"
            "コンテキスト(会話履歴)もリセットされる。")
        self.cmb_chats = QComboBox(root)
        self.cmb_chats.setToolTip(
            "過去のチャット。選択で再表示・会話の継続ができる")
        self.cmb_chats.addItem("現在のチャット")
        crow.addWidget(self.btn_newchat)
        crow.addWidget(self.cmb_chats, 1)
        self.btn_chat_export = QPushButton("↓", root)
        self.btn_chat_export.setFixedWidth(26)
        self.btn_chat_export.setToolTip(
            "表示中のチャットをMarkdownファイルに保存")
        self.btn_chat_del = QPushButton("✕", root)
        self.btn_chat_del.setFixedWidth(26)
        self.btn_chat_del.setEnabled(False)
        self.btn_chat_del.setToolTip(
            "表示中の履歴チャットを削除(現在のチャットは対象外)")
        crow.addWidget(self.btn_chat_export)
        crow.addWidget(self.btn_chat_del)
        lay.addLayout(crow)

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
        self.btn_send.setToolTip(
            "送信中は「中断」に変わり、実行中の往復を止める\n"
            "(進行中のAPI応答/ツール実行の完了待ちは中断できない)")
        self.btn_retry = QPushButton("再送", root)
        self.btn_retry.setEnabled(False)
        self.btn_retry.setToolTip(
            "最後の質問とその応答を取り消して再送信する")
        self.btn_clear = QPushButton("履歴クリア", root)
        self.lbl_status = QLabel("", root)
        row.addWidget(self.btn_send)
        row.addWidget(self.btn_retry)
        row.addWidget(self.btn_clear)
        row.addWidget(self.lbl_status, 1)
        self.lbl_ctx = QLabel("", root)
        self.lbl_ctx.setStyleSheet("color:#666; font-size:11px")
        self.lbl_ctx.setToolTip(
            "ctx: コンテキスト使用量(直近API応答のprompt_tokens実測値、\n"
            "未取得時は~付きで文字数÷3の推定)。右はモデルの上限。\n"
            "Σ: このチャットの累計トークン。$: 推定コスト(価格情報時)")
        row.addWidget(self.lbl_ctx)
        lay.addLayout(row)

        self.setWidget(root)
        self._load_settings()
        self._restore_chats()
        self._snapshot_fields()

        self.cmb_provider.currentIndexChanged.connect(
            self._on_provider_changed)
        self.cmb_model.activated.connect(self._on_model_activated)
        self.cmb_model.currentTextChanged.connect(
            self._on_model_text_changed)
        self.btn_models.clicked.connect(self._fetch_models)
        self.btn_send.clicked.connect(self._send_or_abort)
        self.btn_retry.clicked.connect(self._retry)
        self.btn_clear.clicked.connect(self._clear)
        self.btn_newchat.clicked.connect(self._new_chat)
        self.cmb_chats.activated.connect(self._switch_chat)
        self.btn_chat_export.clicked.connect(self._export_chat)
        self.btn_chat_del.clicked.connect(self._delete_chat)
        self.btn_settings.toggled.connect(self._on_settings_toggled)
        self.btn_agent_edit.clicked.connect(self._edit_agent)
        self.cmb_agent.activated.connect(self._on_agent_activated)
        self.btn_skill_edit.clicked.connect(self._edit_skills)
        self.btn_mcp.clicked.connect(self._edit_mcp)
        self.input.sig_submit.connect(self._send)
        self.sig_append.connect(self._append)
        self.sig_instructions.connect(self._refresh_instructions)
        self.sig_agent_changed.connect(self._on_agent_changed)
        self.sig_confirm.connect(self._on_confirm)
        self.sig_status.connect(self.lbl_status.setText)
        self.sig_busy.connect(self._set_busy)
        self.sig_models.connect(self._on_models)
        self.btn_signin.clicked.connect(self._signin)
        self.sig_signin.connect(self._on_signin)
        self.sig_open_url.connect(
            lambda u: QDesktopServices.openUrl(QUrl(u)))

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
        self.chk_confirm.setChecked(
            str(s.value(_SETTING.format("confirm"), "false")).lower()
            in ("1", "true"))
        # API設定の表示状態: 保存値が無い初回だけ、
        # キー未設定なら開く・設定済みなら畳む
        v = s.value(_SETTING.format("settings_visible"), None)
        if v is None:
            v = not credential_store.get_secret(f"ai_{pid}_api_key")
        else:
            v = str(v).lower() in ("1", "true")
        self.btn_settings.setChecked(bool(v))
        self.box_api.setVisible(self.btn_settings.isChecked())
        self._refresh_agents(s.value(_SETTING.format("agent"), ""))
        self._refresh_skills()
        self._update_mcp_label()

    def _on_settings_toggled(self, on):
        self.box_api.setVisible(on)
        QSettings().setValue(_SETTING.format("settings_visible"), on)

    # ---- エージェント(常時注入の指示書) ----

    def _refresh_agents(self, select_id=None):
        """エージェントコンボを ~/.qgis-live/agents/*.md で再構築する。"""
        cur = (select_id if select_id is not None
               else self.cmb_agent.currentData())
        self.cmb_agent.blockSignals(True)
        self.cmb_agent.clear()
        self.cmb_agent.addItem("(なし)", None)
        for a in ai_client.list_agents():
            self.cmb_agent.addItem(a["title"], a["id"])
            self.cmb_agent.setItemData(
                self.cmb_agent.count() - 1, a["path"],
                Qt.ItemDataRole.ToolTipRole)
        idx = self.cmb_agent.findData(cur)
        self.cmb_agent.setCurrentIndex(idx if idx >= 0 else 0)
        self.cmb_agent.blockSignals(False)

    def _on_agent_activated(self, _idx):
        QSettings().setValue(_SETTING.format("agent"),
                             self.cmb_agent.currentData() or "")
        self._update_ctx_label()

    def _edit_agent(self):
        dlg = _InstructionsDialog(
            self, kind="agents", select=self.cmb_agent.currentData())
        dlg.exec()
        self._refresh_agents()
        self._refresh_skills()

    # ---- スキル(オンデマンド手順書。選択不要で全件が一覧に載る) ----

    def _refresh_skills(self):
        """スキルコンボを ~/.qgis-live/skills/*.md + 同梱品で再構築する。"""
        cur = self.cmb_skill.currentData()
        self.cmb_skill.blockSignals(True)
        self.cmb_skill.clear()
        skills = ai_client.list_skills()
        if not skills:
            self.cmb_skill.addItem("(なし)", None)
        for s in skills:
            label = s["title"] + (" (同梱)" if s["builtin"] else "")
            self.cmb_skill.addItem(label, s["id"])
            tip = s["path"]
            if s.get("desc"):
                tip = s["desc"] + "\n" + s["path"]
            self.cmb_skill.setItemData(
                self.cmb_skill.count() - 1, tip,
                Qt.ItemDataRole.ToolTipRole)
        idx = self.cmb_skill.findData(cur)
        self.cmb_skill.setCurrentIndex(idx if idx >= 0 else 0)
        self.cmb_skill.blockSignals(False)

    def _edit_skills(self):
        dlg = _InstructionsDialog(
            self, kind="skills", select=self.cmb_skill.currentData())
        dlg.exec()
        self._refresh_skills()
        self._refresh_agents()

    def _refresh_instructions(self):
        """AIのai_*ツールが指示書を更新した後のコンボ再構築。"""
        self._refresh_agents()
        self._refresh_skills()

    def _on_agent_changed(self, aid):
        """AIの ai_select_agent で選択中エージェントが切替わった。"""
        idx = self.cmb_agent.findData(aid or None)
        self.cmb_agent.setCurrentIndex(idx if idx >= 0 else 0)
        QSettings().setValue(_SETTING.format("agent"), aid or "")
        self._update_ctx_label()

    # ---- 外部MCPサーバ ----

    def _update_mcp_label(self):
        """MCP設定の状態を行ラベルに反映する。"""
        try:
            n = len(ai_client.mcp_servers_config())
        except ai_client.ApiError as e:
            self.lbl_mcp.setText(f"設定エラー: {e}")
            return
        self.lbl_mcp.setText(
            f"{n}サーバ" if n else "未設定")

    def _edit_mcp(self):
        dlg = _McpDialog(self)
        dlg.exec()
        self._update_mcp_label()
        if dlg.saved:
            self._reset_mcp()      # 次の送信で再ディスカバリ

    def _reset_mcp(self):
        """接続中のMCPセッションを閉じて未発見状態に戻す。"""
        for s in self._mcp_sessions.values():
            try:
                s.close()
            except Exception:
                pass
        self._mcp_sessions = {}
        self._mcp_done = False
        ai_client.register_extra_tools([], {})

    def _ensure_mcp(self):
        """外部MCPサーバへ接続してツールを登録する(ワーカースレッド)。

        初回送信時の1回だけ実行。設定変更は _edit_mcp でリセットされる。
        """
        if self._mcp_done:
            return
        self._mcp_done = True
        if not ai_client.mcp_servers_config():
            self._emit(self.sig_append, "tool", "MCPサーバ未設定")
            return
        self._emit(self.sig_status, "MCPサーバへ接続中…")
        r = ai_client.mcp_discover(
            on_status=lambda m: self._emit(
                self.sig_append, "tool", m))
        ai_client.register_extra_tools(r["tools"], r["callers"])
        self._mcp_sessions = r["sessions"]
        for name, err in r["errors"].items():
            self._emit(self.sig_append, "error",
                       f"MCP '{name}' 接続失敗: {err}")
        ok = {n: len(s.tools) for n, s in r["sessions"].items()}
        if ok:
            self._emit(self.sig_append, "tool",
                       "MCP接続: " + ", ".join(
                           f"{n}({c}ツール)" for n, c in ok.items()))

    def _load_provider_fields(self):
        """現在のプロバイダの保存値(無ければ既定)を入力欄へ反映する。"""
        s = QSettings()
        pid = self._provider()
        d = ai_client.PROVIDERS[pid]
        self.w_signin.setVisible(pid == "copilot")
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
        s.setValue(_SETTING.format("confirm"),
                   self.chk_confirm.isChecked())

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
        self._signin_abort = True  # 進行中のデバイスフローがあれば止める
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
            self._update_ctx_label()
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
        self._update_ctx_label()   # 上限表示がモデル依存のため更新

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
        if kind == "assistant":
            # AI応答はMarkdownレンダリング(表・コードブロック・見出し等)
            body = f"<div style='color:{color}'>{_md(text)}</div>"
        elif kind == "tool":
            body = (f"<span style='color:{color}'>"
                    f"<pre style='margin:2px 0'>{_esc(text)}</pre></span>")
        else:
            body = f"<span style='color:{color}'>{_esc(text)}</span>"
        self.view.append(
            f"<div style='margin:6px 0'>"
            f"<b style='color:{color}'>[{label}]</b> {body}</div>")

    def _set_busy(self, busy):
        self._busy = busy
        self.input.setEnabled(not busy)
        # 実行中は送信ボタンを「中断」に変える
        self.btn_send.setText("中断" if busy else "送信")
        self.btn_retry.setEnabled(not busy and bool(self._history))
        self.btn_chat_export.setEnabled(not busy)
        if busy:
            self.lbl_status.setText("実行中…")
        if not busy:
            self._update_ctx_label()   # 往復終了=履歴確定のタイミング

    def _update_ctx_label(self):
        """コンテキスト使用量と累計トークン/コストを右下に表示する。"""
        # ctx: 直近API応答のprompt_tokensがあれば実測値、無ければ文字数推定
        actual = self._usage.get("last", 0)
        if actual:
            est, mark = actual, ""
        else:
            try:
                chars = len(self._build_system(
                    self._plugins, self.cmb_agent.currentData()))
            except Exception:
                chars = 0
            chars += sum(len(m.get("content") or "")
                         for m in self._history)
            est, mark = chars // 3, "~"  # 日本語~1.5/英~4字の中間
        info = self._model_infos.get(self._current_model()) or {}
        lim = info.get("context")
        parts = [f"ctx {mark}{ai_client.fmt_tokens(est)}"
                 + (f"/{ai_client.fmt_tokens(lim)}"
                    f" ({est * 100 // lim}%)" if lim else "")]
        # 累計: APIがusageを返した時だけ表示。価格が分かればコストも
        total = self._usage["in"] + self._usage["out"]
        if total:
            parts.append(f"Σ{ai_client.fmt_tokens(total)}")
            cost = ai_client.usage_cost(info, self._usage)
            if cost is not None:
                parts.append(f"${cost:.4f}" if cost < 1
                             else f"${cost:.2f}")
        self.lbl_ctx.setText(" · ".join(parts))

    def _clear(self):
        self._history.clear()
        self.view.clear()
        self._update_ctx_label()

    # ---- チャット履歴 ----

    def _chat_title(self, history):
        """先頭のユーザーメッセージからタイトルを作る。"""
        for m in history:
            if m.get("role") == "user" and m.get("content"):
                t = m["content"].splitlines()[0].strip()
                return t[:30] + ("…" if len(t) > 30 else "")
        return f"チャット{len(self._sessions)}"

    def _save_open_chat(self):
        """表示中チャットの状態(履歴+表示HTML)をセッションへ書き戻す。

        空ビューのtoHtml()は空body付きの文書を返すため、
        表示テキストが無い場合はhtmlを空にしておく
        (「新しいチャット」で空セッションが履歴化されないように)。
        """
        s = self._sessions[self._open_chat]
        s["history"] = self._history
        s["html"] = (self.view.toHtml()
                     if self.view.toPlainText().strip() else "")
        s["agent"] = self.cmb_agent.currentData()
        s["usage"] = self._usage

    def _load_chat(self, idx):
        """セッションを表示状態にする(履歴・HTML・エージェントを更新)。"""
        s = self._sessions[idx]
        self._history = s["history"]
        self.view.setHtml(s["html"])
        ai = self.cmb_agent.findData(s.get("agent"))
        self.cmb_agent.setCurrentIndex(ai if ai >= 0 else 0)
        self._usage = dict(s.get("usage")
                           or {"in": 0, "out": 0, "last": 0})
        self._open_chat = idx
        # 「現在のチャット」(0)は削除対象外
        self.btn_chat_del.setEnabled(idx > 0)
        self._update_ctx_label()

    def _new_chat(self):
        """現在のチャットを履歴へ保存し、新規チャットを開始する。

        過去チャット表示中でも押せる: その表示状態を保存した上で
        新しい「現在のチャット」を開く。現在のチャットが空なら
        その表示に戻るだけ。
        """
        self._save_open_chat()
        live = self._sessions[0]
        if live["history"] or live["html"]:
            live["title"] = self._chat_title(live["history"])
            self._sessions.append(live)
            self.cmb_chats.addItem(live["title"])
            self._sessions[0] = {"title": "現在のチャット",
                                 "history": [], "html": "", "agent": None}
        self._load_chat(0)
        self.cmb_chats.setCurrentIndex(0)

    def _switch_chat(self, idx):
        """履歴コンボの選択: 表示中を保存してから選択チャットを開く。"""
        if idx == self._open_chat or idx >= len(self._sessions):
            return
        self._save_open_chat()
        self._load_chat(idx)
        self._persist_chats()

    def _chats_path(self):
        """履歴永続化先 ~/.qgis-live/chats.json。"""
        return os.path.join(
            os.path.dirname(ai_client.agents_dir()), "chats.json")

    def _persist_chats(self):
        """アーカイブ済みチャット(セッション[1:])をファイルへ保存。"""
        try:
            data = self._sessions[1:][-50:]  # 最新50件まで
            with open(self._chats_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception:
            pass

    def _restore_chats(self):
        """起動時に保存済みチャットをセッションとコンボへ復元する。"""
        try:
            with open(self._chats_path(), "r", encoding="utf-8") as f:
                saved = json.load(f)
        except Exception:
            return
        if not isinstance(saved, list):
            return
        for s in saved:
            if not isinstance(s, dict) \
                    or ("history" not in s and "html" not in s):
                continue
            s.setdefault("title", "チャット")
            s.setdefault("history", [])
            s.setdefault("html", "")
            s.setdefault("agent", None)
            self._sessions.append(s)
            self.cmb_chats.addItem(str(s["title"]))

    def _delete_chat(self):
        """表示中の履歴チャットを削除して現在のチャットへ戻る。"""
        idx = self._open_chat
        if idx <= 0 or idx >= len(self._sessions):
            return  # 現在のチャット(0)は消せない
        del self._sessions[idx]
        self.cmb_chats.blockSignals(True)
        self.cmb_chats.removeItem(idx)
        self.cmb_chats.setCurrentIndex(0)
        self.cmb_chats.blockSignals(False)
        self._open_chat = -1        # _load_chatで確定させる
        self._load_chat(0)
        self._persist_chats()

    def _export_chat(self):
        """表示中チャットをMarkdownファイルへ保存。"""
        doc = QTextDocument()
        doc.setHtml(self.view.toHtml())
        md = doc.toMarkdown()
        if not md.strip():
            self._append("error", "保存する内容がありません")
            return
        title = self._sessions[self._open_chat].get("title") or "chat"
        path, _ = QFileDialog.getSaveFileName(
            self, "チャットを保存", f"{title}.md", "Markdown (*.md)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(md)
            self._append("tool", f"チャットを保存しました: {path}")
        except Exception as e:
            self._append("error", f"保存に失敗しました: {e}")

    def _on_destroyed(self):
        self._alive = False
        self._signin_abort = True
        self._reset_mcp()

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
        self._save_open_chat()
        self._persist_chats()
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

    # ---- GitHubサインイン (OAuthデバイスフロー) ----

    def _signin(self):
        """「GitHubでサインイン」: デバイスフローでトークンを取得する。

        ボタンはcopilot選択時のみ表示。ポーリングはワーカースレッド、
        完了は sig_signin でGUIスレッドに戻す。
        """
        self._signin_abort = False
        self.btn_signin.setEnabled(False)
        threading.Thread(target=self._signin_run, daemon=True,
                         name="qgis-ai-signin").start()

    def _signin_run(self):
        try:
            d = ai_client.github_device_code()
        except Exception as e:
            self._emit(self.sig_append, "error",
                       f"サインイン用デバイスコードの取得に失敗: {e}")
            self._emit(self.sig_signin, "copilot", "")
            return
        uri = d.get("verification_uri") or "https://github.com/login/device"
        code = d["user_code"]
        self._emit(self.sig_append, "tool",
                   f"GitHubサインイン: {uri} を開きコード {code} を入力")
        self._emit(self.sig_status,
                   f"GitHubでコード {code} を入力中…")
        self._emit(self.sig_open_url, uri)
        interval = max(int(d.get("interval") or 5), 3)
        deadline = time.time() + int(d.get("expires_in") or 900)
        token = err = None
        while time.time() < deadline:
            if self._signin_abort or not self._alive:
                err = "中止しました"
                break
            time.sleep(interval)
            try:
                r = ai_client.github_poll_access_token(d["device_code"])
            except Exception as e:
                err = f"ポーリング失敗: {e}"
                break
            if r.get("access_token"):
                token = r["access_token"]
                break
            e = r.get("error")
            if e == "slow_down":
                interval += 5
            elif e != "authorization_pending":
                err = (f"{e}: {r.get('error_description') or ''}"
                       .rstrip(": "))
                break
        if token:
            self._emit(self.sig_append, "tool",
                       "GitHubサインイン完了。トークンをAPIキー欄に設定"
                       "しました")
        else:
            self._emit(self.sig_append, "error",
                       f"GitHubサインイン: {err or 'コードの有効期限切れ'}")
        self._emit(self.sig_status, "")
        self._emit(self.sig_signin, "copilot", token or "")

    def _on_signin(self, pid, token):
        """デバイスフロー完了(GUIスレッド)。トークンをキー欄へ保存。"""
        self.btn_signin.setEnabled(True)
        if token and self._provider() == pid:
            self.ed_key.setText(token)
            self._save_provider_key(pid, token)
            self._snapshot_fields()

    # ---- 送信/エージェントループ ----

    def _send_or_abort(self):
        """送信ボタン: 実行中なら中断フラグを立てる。"""
        if self._busy:
            self._abort = True
            self.lbl_status.setText("中断中…")
            return
        self._send()

    def _retry(self):
        """最後の質問+応答を取り消して同じ質問を再送する。"""
        if self._busy or not self._history:
            return
        while self._history and self._history[-1]["role"] != "user":
            self._history.pop()
        if not self._history:
            return
        text = self._history.pop()["content"]
        self.input.setPlainText(text)
        self._send()

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
        self._plugins = plugins
        pid = self._provider()
        cfg = {
            "provider": pid,
            "base": (self.ed_endpoint.text().strip()
                     or ai_client.PROVIDERS[pid]["base"]),
            "key": self.ed_key.text().strip(),
            "model": (self._current_model()
                      or ai_client.PROVIDERS[pid]["model"]),
            "vision": self.chk_vision.isChecked(),
            "agent": self.cmb_agent.currentData(),
            "confirm": self.chk_confirm.isChecked(),
        }
        self._save_settings()
        self.input.clear()
        self._append("user", text)
        self._abort = False
        self.sig_busy.emit(True)
        threading.Thread(
            target=self._agent_run,
            args=(driver, cfg, plugins, text),
            daemon=True, name="qgis-ai-agent").start()

    def _build_system(self, plugins, agent_id):
        """選択中エージェント+スキル/エージェント一覧込みのsystem prompt。"""
        return ai_client.system_prompt(
            plugins,
            agent_text=ai_client.load_agent(agent_id),
            skills=ai_client.list_skills(),
            agents=ai_client.list_agents(),
            active_agent=agent_id)

    def _agent_run(self, driver, cfg, plugins, user_text):
        """ワーカースレッド: API呼出 + ツール実行のループ。"""
        try:
            prov = ai_client.get_provider(cfg["provider"])
        except ai_client.ApiError as e:
            self._emit(self.sig_append, "error", str(e))
            self._emit(self.sig_status, "")
            self._emit(self.sig_busy, False)
            return
        self._ensure_mcp()
        system = self._build_system(plugins, cfg.get("agent"))
        msgs = prov.build_messages(
            system, ai_client.trim_history(self._history), user_text)
        final_text = ""
        try:
            for _ in range(ai_client.MAX_TOOL_ROUNDS):
                if self._abort:
                    final_text = "(中断しました)"
                    self._emit(self.sig_append, "error", final_text)
                    break
                self._emit(self.sig_status, "API応答待ち…")
                data = prov.send(cfg["base"], cfg["key"], cfg["model"],
                                 system, msgs)
                turn = prov.parse(data)
                u = turn.get("usage")
                if u:
                    self._usage["in"] += u.get("in", 0)
                    self._usage["out"] += u.get("out", 0)
                    self._usage["last"] = u.get("in", 0)
                if turn["text"]:
                    self._emit(self.sig_append, "assistant", turn["text"])
                if not turn["calls"]:
                    final_text = turn["text"]
                    break
                results = []
                for c in turn["calls"]:
                    if self._abort:
                        results.append({"text": "ABORTED by user",
                                        "image": None})
                    else:
                        results.append(
                            self._run_tool(driver, cfg,
                                           c["name"], c["args"]))
                prov.append_exchange(msgs, turn, results)
                # ai_select_agent: 選択中エージェントの切替を反映し
                # システムプロンプトを組み直す(最後の指定が優先)
                sel = [r["agent_select"] for r in results
                       if "agent_select" in r]
                if sel:
                    aid = sel[-1]
                    cfg["agent"] = aid
                    system = self._build_system(plugins, aid or None)
                    if msgs and msgs[0].get("role") == "system":
                        msgs[0]["content"] = system  # OpenAI形式。
                        # Geminiはsend時にsystemを別渡しするため変数で追従
                    self._emit(self.sig_agent_changed, aid or "")
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
        if self._abort:
            return {"text": "ABORTED", "image": None}
        # 確認モード: 実行のたびにユーザへ可否を問う
        if cfg.get("confirm") and not self._confirm_tool(name, args):
            self._emit(self.sig_append, "tool",
                       f"{name} → ユーザーによりスキップ")
            return {"text": "SKIPPED: user denied", "image": None}
        if name in ai_client.INSTRUCTION_TOOL_NAMES:
            return self._run_instruction_tool(name, args)
        if (name or "").startswith("mcp_"):
            return self._run_extra_tool(name, args)
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

    def _run_instruction_tool(self, name, args):
        """ai_* ツール: 指示書ファイルのパネルローカル操作。

        ファイルI/OのみでGUI操作を含まないためワーカースレッドで
        実行できる。UIのコンボ更新はシグナルでGUIスレッドに戻す。
        """
        self._emit(self.sig_append, "tool",
                   f"{name} {json.dumps(args or {}, ensure_ascii=False)}")
        self._emit(self.sig_status, f"{name} 実行中…")
        r = {"text": "", "image": None}
        if name == "ai_select_agent":
            # 選択状態はパネルのUI状態。結果dictのagent_selectキーを
            # エージェントループが拾ってsystem promptを組み直す
            aid = ((args or {}).get("id") or "").strip()
            if aid and not any(a["id"] == aid
                               for a in ai_client.list_agents()):
                r["text"] = f"ERROR: agents '{aid}' が見つかりません"
            else:
                r["text"] = (f"active agent set: {aid}" if aid
                             else "active agent cleared")
                r["agent_select"] = aid
        else:
            try:
                r["text"] = ai_client.run_instruction_tool(name, args)
            except ai_client.ApiError as e:
                r["text"] = f"ERROR: {e}"
            except Exception as e:
                r["text"] = f"ERROR: {type(e).__name__}: {e}"
            self._emit(self.sig_instructions)
        text = r["text"]
        self._emit(self.sig_append, "tool",
                   f"→ {text[:2000]}"
                   + ("…" if len(text) > 2000 else ""))
        return r

    def _run_extra_tool(self, name, args):
        """外部MCPツール(mcp_<server>__<tool>)をセッション経由で実行。"""
        self._emit(self.sig_append, "tool",
                   f"{name} {json.dumps(args or {}, ensure_ascii=False)}")
        self._emit(self.sig_status, f"{name} 実行中…")
        try:
            text = ai_client.run_extra_tool(name, args)
        except ai_client.ApiError as e:
            text = f"ERROR: {e}"
        except Exception as e:
            text = f"ERROR: {type(e).__name__}: {e}"
        self._emit(self.sig_append, "tool",
                   f"→ {text[:2000]}"
                   + ("…" if len(text) > 2000 else ""))
        return {"text": text, "image": None}

    # ---- ツール実行の確認(確認モード) ----

    def _confirm_tool(self, name, args):
        """ワーカースレッド→GUIスレッドでYes/Noを聞き結果を返す。

        モーダル表示中もワーカーはポーリング待機し、中断やパネル
        消去で打ち切れる(デッドロック防止)。
        """
        self._confirm_event.clear()
        self._emit(self.sig_confirm, name,
                   json.dumps(args or {}, ensure_ascii=False)[:400])
        while not self._confirm_event.wait(0.3):
            if self._abort or not self._alive:
                return False
        return bool(self._confirm_result)

    def _on_confirm(self, name, args_text):
        """確認ダイアログを出す(GUIスレッド)。"""
        ok = QMessageBox.question(
            self, "ツール実行の確認",
            f"{name} を実行しますか?\n\n{args_text}",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes
        self._confirm_result = ok
        self._confirm_event.set()


class _McpDialog(QDialog):
    """外部MCPサーバ設定(~/.qgis-live/mcp_servers.json)の編集。

    Claude Desktop互換のJSONをそのまま編集する。
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("外部MCPサーバ設定")
        self.resize(560, 420)
        self.saved = False
        lay = QVBoxLayout(self)
        lbl = QLabel(
            "外部MCPサーバを {\"mcpServers\": {...}} 形式で設定します。\n"
            "command=stdio起動 / url=Streamable HTTP。"
            "発見したツールは mcp_<サーバ>__<ツール> で使えます。\n"
            "保存すると次の送信で再接続されます。", self)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color:#666; font-size:11px")
        lay.addWidget(lbl)
        self.ed = QPlainTextEdit(self)
        try:
            with open(ai_client.mcp_config_path(), "r",
                      encoding="utf-8") as f:
                text = f.read()
        except Exception:
            text = json.dumps(ai_client.MCP_CONFIG_TEMPLATE,
                              ensure_ascii=False, indent=2)
        self.ed.setPlainText(text)
        lay.addWidget(self.ed, 1)
        # 接続例(read-only)。クリックでエディタへマージ挿入できる
        grp = QGroupBox("接続例", self)
        gl = QVBoxLayout(grp)
        gl.setContentsMargins(4, 4, 4, 4)
        self.ed_sample = QPlainTextEdit(grp)
        self.ed_sample.setReadOnly(True)
        self.ed_sample.setPlainText(
            json.dumps(ai_client.MCP_CONFIG_TEMPLATE,
                       ensure_ascii=False, indent=2))
        self.ed_sample.setMaximumHeight(120)
        self.ed_sample.setStyleSheet(
            "font-family:Consolas,monospace; font-size:11px;"
            "background:#f6f6f6")
        gl.addWidget(self.ed_sample)
        btn_insert = QPushButton("例をエディタへ挿入", grp)
        gl.addWidget(btn_insert)
        lay.addWidget(grp)
        row = QHBoxLayout()
        btn_save = QPushButton("保存", self)
        btn_close = QPushButton("閉じる", self)
        row.addWidget(btn_save)
        row.addStretch(1)
        row.addWidget(btn_close)
        lay.addLayout(row)
        btn_save.clicked.connect(self._save)
        btn_insert.clicked.connect(self._insert_sample)
        btn_close.clicked.connect(self.reject)

    def _insert_sample(self):
        """接続例をエディタのmcpServersへマージ挿入する。"""
        try:
            d = json.loads(self.ed.toPlainText() or "{}")
        except Exception as e:
            QMessageBox.warning(self, "MCP設定",
                                f"JSONが読めません: {e}")
            return
        if not isinstance(d, dict):
            d = {}
        sv = d.setdefault("mcpServers", {})
        for name, conf in ai_client.MCP_CONFIG_TEMPLATE[
                "mcpServers"].items():
            if name not in sv:
                sv[name] = conf
        self.ed.setPlainText(
            json.dumps(d, ensure_ascii=False, indent=2))

    def _save(self):
        try:
            ai_client.mcp_save_config(self.ed.toPlainText())
        except ai_client.ApiError as e:
            QMessageBox.warning(self, "MCP設定", str(e))
            return
        self.saved = True
        self.accept()


class _InstructionsDialog(QDialog):
    """指示書(agents|skills の *.md)の作成・編集・削除ダイアログ。

    保存は常にユーザ側 ~/.qgis-live/<kind>/ へ書く。
    プラグイン同梱(bundled)は読み取り専用だが、同名で保存すれば
    ユーザ側ファイルとして優先される(実質の上書き)。
    """

    _KINDS = [("agents", "エージェント"), ("skills", "スキル")]

    def __init__(self, parent, kind="agents", select=None):
        super().__init__(parent)
        self.setWindowTitle("指示書編集 (エージェント/スキル)")
        self.resize(760, 480)
        lay = QVBoxLayout(self)
        self.cmb_kind = QComboBox(self)
        for kid, label in self._KINDS:
            self.cmb_kind.addItem(label, kid)
        lay.addWidget(self.cmb_kind)
        self.cmb = QComboBox(self)
        lay.addWidget(self.cmb)
        self.ed_name = QLineEdit(self)
        self.ed_name.setPlaceholderText(
            "名前 (ファイル名。<名前>.md で保存。例: map-design)")
        lay.addWidget(self.ed_name)
        # 編集(Markdown入力)と表示(レンダリング)を左右に分割
        split = QSplitter(Qt.Orientation.Horizontal, self)
        ed_box = QGroupBox("編集 (Markdown)", split)
        eb = QVBoxLayout(ed_box)
        eb.setContentsMargins(4, 4, 4, 4)
        self.ed_body = QPlainTextEdit(ed_box)
        eb.addWidget(self.ed_body)
        pv_box = QGroupBox("表示", split)
        pb = QVBoxLayout(pv_box)
        pb.setContentsMargins(4, 4, 4, 4)
        self.preview = QTextBrowser(pv_box)
        self.preview.setOpenExternalLinks(True)
        pb.addWidget(self.preview)
        split.addWidget(ed_box)
        split.addWidget(pv_box)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 1)
        lay.addWidget(split, 1)
        self.ed_body.textChanged.connect(self._update_preview)
        self.lbl_hint = QLabel("", self)
        self.lbl_hint.setStyleSheet("color:#666; font-size:11px")
        self.lbl_hint.setWordWrap(True)
        lay.addWidget(self.lbl_hint)
        row = QHBoxLayout()
        self.btn_save = QPushButton("保存", self)
        self.btn_del = QPushButton("削除", self)
        self.btn_dir = QPushButton("フォルダを開く", self)
        btn_close = QPushButton("閉じる", self)
        row.addWidget(self.btn_save)
        row.addWidget(self.btn_del)
        row.addWidget(self.btn_dir)
        row.addStretch(1)
        row.addWidget(btn_close)
        lay.addLayout(row)
        self.cmb_kind.activated.connect(lambda _i: self.reload())
        self.cmb.activated.connect(self._pick)
        self.btn_save.clicked.connect(self._save)
        self.btn_del.clicked.connect(self._delete)
        self.btn_dir.clicked.connect(self._open_dir)
        btn_close.clicked.connect(self.accept)
        self._items = {}
        i = self.cmb_kind.findData(kind)
        self.cmb_kind.setCurrentIndex(i if i >= 0 else 0)
        self.reload(select)

    def _update_preview(self):
        """編集中のMarkdownを表示ペインにレンダリングする。"""
        self.preview.setMarkdown(self.ed_body.toPlainText())

    def _kind(self):
        return self.cmb_kind.currentData() or "agents"

    def _kind_label(self):
        return self.cmb_kind.currentText()

    def reload(self, select=None):
        kind = self._kind()
        self._items = {a["id"]: a for a in
                       ai_client.list_instruction_files(kind)}
        self.lbl_hint.setText(
            "エージェント: 選択中は毎回system promptに注入"
            if kind == "agents" else
            "スキル: 一覧のみプロンプトに載り、モデルが必要時に"
            " qgis_pyeval の open() で本文を読む")
        self.cmb.blockSignals(True)
        self.cmb.clear()
        self.cmb.addItem(f"＋ 新規{self._kind_label()}", "")
        for a in self._items.values():
            label = a["title"] + (" (同梱)" if a["builtin"] else "")
            self.cmb.addItem(label, a["id"])
        self.cmb.blockSignals(False)
        if select:
            i = self.cmb.findData(select)
            if i > 0:
                self.cmb.setCurrentIndex(i)
        self._pick(self.cmb.currentIndex())

    def _pick(self, _idx):
        a = self._items.get(self.cmb.currentData() or "")
        if a is None:
            self.ed_name.setText("")
            self.ed_body.setPlainText("")
            return
        self.ed_name.setText(a["id"])
        try:
            with open(a["path"], "r", encoding="utf-8") as f:
                body = f.read()
        except Exception:
            body = ""
        self.ed_body.setPlainText(body)

    def _save(self):
        try:
            p = ai_client.save_instruction(
                self._kind(), self.ed_name.text(),
                self.ed_body.toPlainText())
        except Exception as e:
            QMessageBox.warning(self, "保存失敗", str(e))
            return
        stem = os.path.splitext(os.path.basename(p))[0]
        self.reload(stem)

    def _delete(self):
        aid = self.cmb.currentData() or ""
        if not aid:
            return
        a = self._items.get(aid)
        if a and a["builtin"]:
            QMessageBox.information(
                self, "削除不可",
                "プラグイン同梱の指示書は削除できません")
            return
        if QMessageBox.question(
                self, "削除",
                f"{self._kind_label()} '{aid}' を削除しますか?"
                ) != QMessageBox.StandardButton.Yes:
            return
        ai_client.delete_instruction(self._kind(), aid)
        self.reload()

    def _open_dir(self):
        d = (ai_client.agents_dir() if self._kind() == "agents"
             else ai_client.skills_dir())
        os.makedirs(d, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(d))


def _tabify_with_sibling(iface, panel):
    """同じドック領域に表示中のドックがあれば分割せずタブ化する。

    AIアシスタントを開いた時にレイヤパネル等の既存ドックと
    縦に分かれるのではなく、タブで重なるようにする。
    """
    from qgis.PyQt.QtWidgets import QDockWidget
    mw = iface.mainWindow()
    area = mw.dockWidgetArea(panel)
    for d in mw.findChildren(QDockWidget):
        if (d is not panel and d.isVisible()
                and mw.dockWidgetArea(d) == area):
            mw.tabifyDockWidget(d, panel)
            return


def show_panel(iface, get_driver, panel):
    """ドックを(必要なら生成して)表示し、インスタンスを返す。"""
    if panel is None:
        panel = AiPanel(iface, get_driver)
        iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, panel)
        _tabify_with_sibling(iface, panel)
    panel.show()
    panel.raise_()
    return panel
