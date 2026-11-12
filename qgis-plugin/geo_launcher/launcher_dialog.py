# -*- coding: utf-8 -*-
"""geo_launcher の管理ダイアログ。

kasugai_qgis ランチャーの Web UI 相当を Qt ウィジェットで提供する。
長時間処理 (robocopy/rclone/ネットワーク) は QThread ワーカーで実行し、
GUI スレッドを占有しない。
"""

import os

from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal, QSettings
from qgis.PyQt.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QPlainTextEdit, QPushButton, QVBoxLayout)

from . import launcher_core as core

PLUGIN_ID = core.PLUGIN_ID


def _tr(message):
    from qgis.PyQt.QtCore import QCoreApplication
    return QCoreApplication.translate(PLUGIN_ID, message)


class _Worker(QThread):
    """バックグラウンド実行ワーカー。fn() の結果を done で返す。"""

    log = pyqtSignal(str)
    done = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self):
        prev = core._log
        core.set_logger(self.log.emit)
        try:
            self.done.emit(self._fn())
        except Exception as e:  # noqa: BLE001 - ワーカー例外はUI通知へ
            self.failed.emit(str(e))
        finally:
            core.set_logger(prev)


class LauncherDialog(QDialog):
    def __init__(self, plugin, parent=None):
        super().__init__(parent or plugin.iface.mainWindow())
        self.plugin = plugin
        self._worker = None
        self.setWindowTitle(_tr("geo_launcher - QGIS/QField Launcher"))
        self.resize(760, 720)

        root = QVBoxLayout(self)

        # ---- 設定ディレクトリ ------------------------------------------
        dir_box = QGroupBox(_tr("Launcher folder (qgis_settings.json)"))
        form = QFormLayout(dir_box)
        dir_row = QHBoxLayout()
        self.dir_combo = QComboBox()
        self.dir_combo.setEditable(True)
        self.dir_combo.addItems(core.candidate_settings_dirs())
        saved = QSettings().value("geo_launcher/settings_dir", "")
        if saved:
            self.dir_combo.setCurrentText(saved)
        self.dir_combo.currentTextChanged.connect(self._on_dir_changed)
        dir_row.addWidget(self.dir_combo, 1)
        browse = QPushButton(_tr("Browse..."))
        browse.clicked.connect(self._browse_dir)
        dir_row.addWidget(browse)
        form.addRow(_tr("Folder"), dir_row)
        self.dir_status = QLabel("")
        form.addRow("", self.dir_status)
        root.addWidget(dir_box)

        # ---- 起動 -------------------------------------------------------
        launch_box = QGroupBox(_tr("Launch"))
        form = QFormLayout(launch_box)

        exe_row = QHBoxLayout()
        self.exe_combo = QComboBox()
        self.exe_combo.setEditable(True)
        exe_row.addWidget(self.exe_combo, 1)
        exe_browse = QPushButton(_tr("Browse..."))
        exe_browse.clicked.connect(self._browse_exe)
        exe_row.addWidget(exe_browse)
        form.addRow(_tr("Executable"), exe_row)

        self.profile_combo = QComboBox()
        self.profile_combo.setEditable(True)
        form.addRow(_tr("Profile"), self.profile_combo)

        self.project_list = QListWidget()
        self.project_list.setMaximumHeight(140)
        form.addRow(_tr("Projects"), self.project_list)

        self.role_combo = QComboBox()
        self.role_combo.addItems(core.ROLES)
        form.addRow(_tr("User role"), self.role_combo)

        self.dev_check = QCheckBox(_tr("Dev mode (QGIS Live Harness)"))
        form.addRow("", self.dev_check)

        btn_row = QHBoxLayout()
        self.launch_btn = QPushButton(_tr("Launch"))
        self.launch_btn.clicked.connect(self._launch)
        btn_row.addWidget(self.launch_btn)
        self.save_btn = QPushButton(_tr("Save settings"))
        self.save_btn.clicked.connect(self._save)
        btn_row.addWidget(self.save_btn)
        refresh = QPushButton(_tr("Reload"))
        refresh.clicked.connect(self.reload_all)
        btn_row.addWidget(refresh)
        btn_row.addStretch(1)
        form.addRow("", btn_row)
        root.addWidget(launch_box)

        # ---- 保守 -------------------------------------------------------
        maint_box = QGroupBox(_tr("Maintenance"))
        row = QHBoxLayout(maint_box)
        for label, slot in (
                ("Mount drives", self._mount_drives),
                ("Run local sync", self._local_sync),
                ("Seed profiles", self._seed_profiles),
                ("Reset profiles", self._reset_profiles)):
            b = QPushButton(_tr(label))
            b.clicked.connect(slot)
            row.addWidget(b)
        root.addWidget(maint_box)

        # ---- Live セッション --------------------------------------------
        sess_box = QGroupBox(_tr("QGIS Live Harness sessions"))
        sv = QVBoxLayout(sess_box)
        self.sessions_list = QListWidget()
        self.sessions_list.setMaximumHeight(110)
        sv.addWidget(self.sessions_list)
        srow = QHBoxLayout()
        srefresh = QPushButton(_tr("Refresh"))
        srefresh.clicked.connect(self._refresh_sessions)
        srow.addWidget(srefresh)
        srow.addStretch(1)
        sv.addLayout(srow)
        root.addWidget(sess_box)

        # ---- ログ -------------------------------------------------------
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(2000)
        root.addWidget(self.log_view, 1)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_btn = QPushButton(_tr("Close"))
        close_btn.clicked.connect(self.close)
        close_row.addWidget(close_btn)
        root.addLayout(close_row)

        self.reload_all()

    # ---- ユーティリティ -------------------------------------------------
    def settings_dir(self):
        return self.dir_combo.currentText().strip()

    def _append_log(self, msg):
        self.log_view.appendPlainText(str(msg))

    def _set_busy(self, busy):
        for w in (self.launch_btn, self.save_btn):
            w.setEnabled(not busy)
        self.launch_btn.setText(
            _tr("Working...") if busy else _tr("Launch"))

    def _run_bg(self, fn, on_done=None):
        if self._worker is not None and self._worker.isRunning():
            self._append_log(_tr("Another task is running. Please wait."))
            return
        self._set_busy(True)
        self._worker = _Worker(fn, self)
        self._worker.log.connect(self._append_log)
        self._worker.failed.connect(
            lambda e: self._append_log(_tr("Error: {0}").format(e)))

        def _done(result):
            self._set_busy(False)
            if on_done:
                on_done(result)
        self._worker.done.connect(_done)
        self._worker.finished.connect(
            lambda: self._set_busy(False))
        self._worker.start()

    def _load(self):
        """現行設定ディレクトリの解決済み (settings, dir, root) を返す。"""
        return core.resolve_settings_dir(self.settings_dir())

    # ---- イベント -------------------------------------------------------
    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(
            self, _tr("Select launcher folder"), self.settings_dir())
        if d:
            self.dir_combo.setCurrentText(d)

    def _browse_exe(self):
        p, _ = QFileDialog.getOpenFileName(
            self, _tr("Select QGIS executable"), "",
            "Executables (*.exe *.bat *.cmd);;All files (*)")
        if p:
            self.exe_combo.setCurrentText(p)

    def _on_dir_changed(self, text):
        d = (text or "").strip()
        ok = os.path.exists(core.settings_path(d)) if d else False
        self.dir_status.setText(
            "qgis_settings.json: "
            + (_tr("found") if ok else _tr("not found")))
        QSettings().setValue("geo_launcher/settings_dir", d)

    def reload_all(self):
        """設定ディレクトリから各リストを再読込する。"""
        d = core.find_settings_dir(self.settings_dir())
        if os.path.normcase(d) != os.path.normcase(self.settings_dir()):
            self.dir_combo.setCurrentText(d)
        self._on_dir_changed(self.settings_dir())
        try:
            settings, sdir, project_root = self._load()
        except Exception as e:  # noqa: BLE001
            self._append_log(_tr("Error: {0}").format(e))
            return

        self.profile_combo.clear()
        for p in core.list_profiles(sdir):
            self.profile_combo.addItem(p["name"], p["path"])
        cur_profile = settings.get("profile") or ""
        if cur_profile:
            i = self.profile_combo.findText(cur_profile)
            self.profile_combo.setCurrentIndex(i if i >= 0 else -1)
            if i < 0:
                self.profile_combo.setCurrentText(cur_profile)

        exe_current = settings.get("qgis_executable") or ""
        self.exe_combo.clear()
        for v in core.list_qgis_versions(portable_base=sdir):
            self.exe_combo.addItem(v["name"], v["path"])
        if exe_current:
            i = self.exe_combo.findData(exe_current)
            if i >= 0:
                self.exe_combo.setCurrentIndex(i)
            else:
                self.exe_combo.setCurrentText(exe_current)
        else:
            auto = core.auto_select_executable(
                settings, project_root,
                available=[{"name": self.exe_combo.itemText(i),
                            "path": self.exe_combo.itemData(i)}
                           for i in range(self.exe_combo.count())])
            if auto:
                i = self.exe_combo.findData(auto)
                if i >= 0:
                    self.exe_combo.setCurrentIndex(i)

        self.project_list.clear()
        current_proj = settings.get("current_project") or ""

        # 現在QGISで開いているプロジェクトを先頭に追加(既定で選択)
        try:
            from qgis.core import QgsProject
            open_proj = QgsProject.instance().fileName()
        except Exception:  # noqa: BLE001
            open_proj = ""
        if open_proj and os.path.isfile(open_proj):
            item = QListWidgetItem(
                _tr("[Current project] {0}").format(
                    os.path.basename(open_proj)))
            item.setData(Qt.ItemDataRole.UserRole, open_proj)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.project_list.addItem(item)

        for p in core.list_projects(settings, project_root):
            item = QListWidgetItem(p["display"])
            item.setData(Qt.ItemDataRole.UserRole, p["path"])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked
                if current_proj and
                os.path.normcase(p["path"]) ==
                os.path.normcase(current_proj)
                else Qt.CheckState.Unchecked)
            self.project_list.addItem(item)

        role = settings.get("userrole") or "Viewer"
        i = self.role_combo.findText(role)
        self.role_combo.setCurrentIndex(i if i >= 0 else 0)
        self.dev_check.setChecked(bool(settings.get("dev_mode")))
        self._refresh_sessions()

    def _refresh_sessions(self):
        self.sessions_list.clear()
        for s in core.list_live_sessions():
            pid = s.get("pid", "?")
            port = s.get("http_port", "?")
            alive = _tr("alive") if s.get("alive") else _tr("starting")
            profile = s.get("profile", "")
            self.sessions_list.addItem(
                "PID {0}  port {1}  {2}  {3}".format(
                    pid, port, alive, profile))

    def _selected_projects(self):
        out, seen = [], set()
        for i in range(self.project_list.count()):
            item = self.project_list.item(i)
            if item.checkState() != Qt.CheckState.Checked:
                continue
            p = item.data(Qt.ItemDataRole.UserRole)
            key = os.path.normcase(os.path.normpath(p or ""))
            if p and key not in seen:
                seen.add(key)
                out.append(p)
        return out

    def _exe_path(self):
        data = self.exe_combo.currentData()
        if data:
            return data
        return self.exe_combo.currentText().strip()

    # ---- 操作 -----------------------------------------------------------
    def _launch(self):
        try:
            settings, sdir, project_root = self._load()
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, PLUGIN_ID, str(e))
            return
        profile = self.profile_combo.currentText().strip() or "default"
        projects = self._selected_projects()
        exe = self._exe_path()
        role = self.role_combo.currentText() or "Viewer"
        dev = self.dev_check.isChecked()

        # 起動前に現在の UI 状態を設定へ反映 (Rust版と同じく mount/seed/
        # local_sync を起動フローへ含める)
        settings["profile"] = profile
        settings["qgis_executable"] = exe
        settings["userrole"] = role
        settings["dev_mode"] = dev
        if projects:
            settings["current_project"] = projects[0]

        # 選択プロファイルが現在のプロファイルと同じなら別プロセスを
        # 起動せず、この QGIS でプロジェクトを開く
        cur = self._current_profile_name()
        if cur and profile == cur:
            self._open_project_here(projects, settings, sdir)
            return

        def work():
            core.mount_drive_mappings(
                settings.get("drive_mappings", []), settings)
            core.copy_profiles_at_startup(sdir, settings)
            core.run_local_sync(settings, sdir)
            return core.launch_qgis(
                profile, projects, project_root, exe, role, dev, sdir)

        def done(n):
            if n:
                self._append_log(_tr("Launched {0} process(es).").format(n))
            else:
                self._append_log(_tr("No process was launched."))
        self._run_bg(work, done)

    def _open_project_here(self, projs, settings, sdir):
        """同一プロファイル時にプロジェクトをこのQGISで開く。

        mount/seed/local_sync の前処理は起動フローと同じく実行する。
        addProject はGUIスレッド必須なので done コールバックで呼ぶ。
        """
        if not projs:
            self._append_log(_tr("No project is selected."))
            return
        if len(projs) > 1:
            self._append_log(
                _tr("Only the first checked project will be opened."))
        path = projs[0]
        if not os.path.isfile(path):
            self._append_log(
                _tr("Project file not found: {0}").format(path))
            return

        def work():
            core.mount_drive_mappings(
                settings.get("drive_mappings", []), settings)
            core.copy_profiles_at_startup(sdir, settings)
            core.run_local_sync(settings, sdir)

        def done(_):
            # addProject は未保存変更があれば保存確認を出してくれる
            self.plugin.iface.addProject(path)
            self._append_log(
                _tr("Opened project in this QGIS: {0}").format(path))
        self._run_bg(work, done)

    def _current_profile_name(self):
        """実行中QGISのプロファイル名 (geo_custom 等) を返す。"""
        try:
            from qgis.core import QgsApplication
            return os.path.basename(os.path.normpath(
                QgsApplication.qgisSettingsDirPath()))
        except Exception:  # noqa: BLE001
            return ""

    def _save(self):
        try:
            _, sdir, _ = self._load()
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, PLUGIN_ID, str(e))
            return
        values = {
            "profile": self.profile_combo.currentText().strip(),
            "qgis_executable": self._exe_path(),
            "userrole": self.role_combo.currentText(),
            "dev_mode": self.dev_check.isChecked(),
        }
        projs = self._selected_projects()
        if projs:
            values["current_project"] = projs[0]
        try:
            p = core.save_settings(sdir, values)
            self._append_log(_tr("Saved: {0}").format(p))
        except OSError as e:
            self._append_log(_tr("Error: {0}").format(e))

    def _mount_drives(self):
        settings, sdir, _ = self._load()
        self._run_bg(lambda: core.mount_drive_mappings(
            settings.get("drive_mappings", []), settings))

    def _local_sync(self):
        settings, sdir, _ = self._load()
        self._run_bg(lambda: core.run_local_sync(settings, sdir))

    def _seed_profiles(self):
        settings, sdir, _ = self._load()
        self._run_bg(lambda: core.copy_profiles_at_startup(sdir, settings))

    def _reset_profiles(self):
        ret = QMessageBox.question(
            self, PLUGIN_ID,
            _tr("Delete all existing QGIS profiles and re-copy the "
                "distribution profiles?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return
        settings, sdir, _ = self._load()
        self._run_bg(lambda: core.reset_profiles(sdir, settings))
