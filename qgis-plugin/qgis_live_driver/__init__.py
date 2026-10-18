import json
import os
import tempfile
import time
import traceback


def _log(msg):
    log = os.environ.get(
        "WEBENGINE_LOG_PATH",
        os.path.join(os.environ.get("TEMP", "/tmp"), "plugin_load.log"),
    )
    try:
        os.makedirs(os.path.dirname(log), exist_ok=True)
        with open(log, "a", encoding="utf-8") as f:
            f.write(str(msg) + "\n")
    except Exception:
        pass


def _http_allowed():
    """QGIS_LIVE_TOOLS から公開コマンド種別の集合を読む(None=全許可)。"""
    raw = os.environ.get("QGIS_LIVE_TOOLS", "").strip()
    if raw and raw != "*":
        return {t.strip().lower().removeprefix("qgis_")
                for t in raw.split(",") if t.strip()}
    return None


def _registry_dir():
    # spawnされる側(MCPクライアントのshim等)が環境変数を持たないため、
    # 検出情報は固定パス ~/.qgis-live/ に書き出す
    return os.environ.get(
        "QGIS_LIVE_REGISTRY",
        os.path.join(os.path.expanduser("~"), ".qgis-live"),
    )


def _restrict_file(path):
    """トークン等を含むファイルをユーザ限定ACLにする(best-effort)。"""
    try:
        if os.name == "nt":
            import subprocess
            user = os.environ.get("USERNAME") or ""
            if user:
                subprocess.run(
                    ["icacls", path, "/inheritance:r",
                     "/grant:r", f"{user}:F"],
                    capture_output=True, timeout=10)
        else:
            os.chmod(path, 0o600)
    except Exception:
        pass


class QgisLivePlugin:
    """UIを持たない制御専用プラグイン。

    有効化は2経路(どちらも localhost 限定・トークン必須):
      - WEBENGINE_LIVE_DIR env 設定 → 起動時に即時有効(開発用途)
      - メニューのトグル → QSettingsに保存され次回起動から自動有効

    公開面:
      - ファイルJSONL (commands.jsonl/results.jsonl) — 言語非依存の基底
      - HTTP 127.0.0.1:<auto port> (/mcp = MCP Streamable HTTP, /api/* = REST)
      - ~/.qgis-live/<pid>-qgis_live_driver.json — 接続情報+トークン(自動検出用)
    """

    SETTING_ENABLED = "qgis_live_driver/enabled"
    _MENU_NAME = "QGIS Live Driver"
    _OWN_ACTION_TEXTS = ("リモート制御 (localhostのみ)", "AI アシスタント")

    def __init__(self, iface):
        self.iface = iface
        self.driver = None
        self._http = None
        self._reg_path = None
        self._action = None
        self._ai_action = None
        self._ai_panel = None
        self._ai_driver = None

    def _own_menu(self):
        """プラグイン > QGIS Live Driver サブメニューを返す(無ければNone)。"""
        try:
            for top in self.iface.mainWindow().menuBar().actions():
                tm = top.menu()
                if tm is None:
                    continue
                for a in tm.actions():
                    sm = a.menu()
                    if sm is not None and sm.title() == self._MENU_NAME:
                        return sm
        except Exception:
            pass
        return None

    def _sweep_menu_actions(self):
        """同名テキストの残存アクションをメニューから除去する。

        過去世代のプラグインがunloadで除去し損ねたQAction(リロードで
        孤立したもの)を掃除する。initGuiで新規追加の前に呼ぶ。
        """
        menu = self._own_menu()
        if menu is None:
            return
        for a in list(menu.actions()):
            if a.text() in self._OWN_ACTION_TEXTS:
                try:
                    menu.removeAction(a)
                    a.deleteLater()
                except Exception:
                    pass

    def initGui(self):
        from qgis.PyQt.QtWidgets import QAction
        self._sweep_menu_actions()  # 前世代の孤立アクション除去
        self._ai_action = QAction("AI アシスタント",
                                  self.iface.mainWindow())
        self._ai_action.triggered.connect(self._open_ai_panel)
        self.iface.addPluginToMenu("QGIS Live Driver", self._ai_action)

        self._action = QAction("リモート制御 (localhostのみ)",
                               self.iface.mainWindow())
        self._action.setCheckable(True)
        self._action.toggled.connect(self._on_toggle)
        self.iface.addPluginToMenu("QGIS Live Driver", self._action)

        live_base = os.environ.get("WEBENGINE_LIVE_DIR")
        _log(f"qgis_live_driver initGui: live_base={live_base!r}")
        if live_base:
            self._start(live_base)  # dev経路: env優先で即起動
        elif self._settings_enabled():
            self._start(self._default_live_base())
        self._sync_action()

    # ---- AIアシスタントパネル ----

    def _open_ai_panel(self):
        from .ai_panel import show_panel
        self._ai_panel = show_panel(
            self.iface, self._panel_driver, self._ai_panel)

    def _panel_driver(self):
        """AIパネルのツール実行に使うLiveDriverを返す。

        リモート制御が有効なら既存ドライバを共有し、無効時はパネル専用の
        内部ドライバを作る。内部ドライバはレジストリ・HTTP公開面を持たず
        (tempdirのlive dirのみ)外部からは発見できない。
        生成はQTimerを含むため必ずGUIスレッドで行う。
        """
        if self.driver is not None:
            return self.driver
        if self._ai_driver is None:
            from .live_driver import LiveDriver
            live_dir = os.path.join(
                tempfile.gettempdir(), f"qgis-live-ai-{os.getpid()}")
            self._ai_driver = LiveDriver(live_dir, iface=self.iface)
        return self._ai_driver

    # ---- 有効化/無効化 ----

    def _default_live_base(self):
        # env未指定の配布利用ではレジストリ配下のユーザ専用dirを使う
        return os.path.join(_registry_dir(), "run")

    def _settings_enabled(self):
        try:
            from qgis.PyQt.QtCore import QSettings
            return str(QSettings().value(
                self.SETTING_ENABLED, "false")).lower() in ("1", "true")
        except Exception:
            return False

    def _set_setting(self, on):
        try:
            from qgis.PyQt.QtCore import QSettings
            QSettings().setValue(self.SETTING_ENABLED, bool(on))
        except Exception:
            pass

    def _sync_action(self):
        if self._action is not None:
            self._action.blockSignals(True)
            self._action.setChecked(self.driver is not None)
            self._action.blockSignals(False)

    def _on_toggle(self, checked):
        if checked and self.driver is None:
            from qgis.PyQt.QtWidgets import QMessageBox
            ret = QMessageBox.warning(
                self.iface.mainWindow(), "QGIS Live Driver",
                "ローカル(localhost)のクライアントからQGIS内部を"
                "遠隔操作できるようになります。\n"
                "pyeval はQGISプロセス内で任意のPythonを実行します。\n\n"
                "アクセスは起動ごとのセッショントークンで保護され、"
                "トークンはユーザ専用ファイルにのみ保存されますが、"
                "同一ユーザで動くプロセスは信頼できるものだけに"
                "してください。\n\n有効にしますか?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if ret != QMessageBox.StandardButton.Yes:
                self._sync_action()
                return
            self._set_setting(True)
            self._start(self._default_live_base())
            if self.driver is None:
                self._set_setting(False)
        elif not checked and self.driver is not None:
            self._set_setting(False)
            self._stop()
        self._sync_action()

    def _start(self, live_base):
        live_dir = os.path.join(
            live_base, f"qgis-{os.getpid()}", __package__)
        try:
            from .live_driver import LiveDriver
            self.driver = LiveDriver(live_dir, iface=self.iface)
            _log(f"qgis_live_driver LiveDriver active: {live_dir}")
        except Exception:
            _log("qgis_live_driver LiveDriver failed:\n"
                 + traceback.format_exc())
            return

        # 認証: セッショントークン必須。QGIS_LIVE_API_KEYは追加キーとして任意
        api_keys = {self.driver.token}
        env_key = os.environ.get("QGIS_LIVE_API_KEY") or None
        if env_key:
            api_keys.add(env_key)
        port = None
        try:
            from .mcp_http import start_http
            self._http, port = start_http(
                self.driver, api_keys=api_keys,
                allowed=_http_allowed())
            self.driver.http_port = port
            _log(f"qgis_live_driver HTTP API: http://127.0.0.1:{port}/ "
                 f"tools={sorted(_http_allowed()) if _http_allowed() else 'all'}")
        except Exception:
            _log("qgis_live_driver HTTP failed:\n"
                 + traceback.format_exc())

        try:
            reg_dir = _registry_dir()
            os.makedirs(reg_dir, exist_ok=True)
            self._reg_path = os.path.join(
                reg_dir, f"{os.getpid()}-{__package__}.json")
            with open(self._reg_path, "w", encoding="utf-8") as f:
                json.dump({
                    "pid": os.getpid(),
                    "plugin_id": __package__,
                    "live_dir": live_dir,
                    "http_port": port,
                    "mcp_url": (f"http://127.0.0.1:{port}/mcp"
                                if port else None),
                    "token": self.driver.token,
                    "http_tools": (sorted(_http_allowed())
                                   if _http_allowed() else "all"),
                    "started": time.time(),
                }, f)
            # トークンを含むためユーザ限定にする
            _restrict_file(self._reg_path)
            _restrict_file(os.path.join(live_dir, "token"))
        except Exception:
            _log("qgis_live_driver registry write failed:\n"
                 + traceback.format_exc())

    def _stop(self):
        if self._http is not None:
            try:
                self._http.shutdown()
            except Exception:
                pass
            self._http = None
        if self.driver is not None:
            try:
                self.driver.stop()
            except Exception:
                pass
            self.driver = None
        if self._reg_path is not None:
            try:
                os.remove(self._reg_path)
            except Exception:
                pass
            self._reg_path = None

    def unload(self):
        # unload中の例外はQGIS側で握り潰されつつ処理が続行され、
        # 除去前のアクションがメニューに孤立するため、全て個別に握り潰す
        if self._ai_panel is not None:
            try:
                self._ai_panel.close()
                self._ai_panel.deleteLater()
            except Exception:
                pass
            self._ai_panel = None
        if self._ai_driver is not None:
            try:
                self._ai_driver.stop()
            except Exception:
                pass
            self._ai_driver = None
        for action in (self._ai_action, self._action):
            if action is not None:
                try:
                    self.iface.removePluginMenu("QGIS Live Driver",
                                                action)
                    action.deleteLater()
                except Exception:
                    pass
        self._ai_action = None
        self._action = None
        self._sweep_menu_actions()  # 自身以外の残存も掃除
        try:
            self._stop()
        except Exception:
            pass


def classFactory(iface):
    return QgisLivePlugin(iface)
