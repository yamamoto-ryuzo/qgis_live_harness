# -*- coding: utf-8 -*-
"""geo_launcher を AI/外部制御から利用するためのブリッジ。

plugin.bridge 属性にこのオブジェクトをぶら下げると、qgis_live_driver の
bridge_call コマンド(ファイルJSONL / REST /api/cmd / MCP qgis_bridge_call)
から ``qgis.utils.plugins['geo_launcher'].bridge.<method>(*args)`` が
プロセス内で直接呼ばれる。

各メソッドは JSON 文字列を返す(bridge_call 側で構造化される)。
ドメインエラーは ``{"ok": false, "error": ...}`` を返し、予期しない例外は
呼び出し元(driver の {"error": traceback})に委ねる。

例(MCP): qgis_bridge_call pluginId="geo_launcher"
         method="launch" args=["geo_custom"]
"""

import inspect
import json
import os

from qgis.PyQt.QtCore import QSettings

from . import launcher_core as core

PLUGIN_ID = core.PLUGIN_ID


class GeoLauncherBridge:
    NAME = "geo_launcher"
    SUMMARY = (
        "kasugai_qgis (QGIS/QField launcher) ported into QGIS. Reads "
        "qgis_settings.json from the launcher folder, lists "
        "profiles/projects/QGIS versions, launches QGIS/QField with role "
        "and dev-mode env injection, and performs drive mounting, "
        "local_sync and profile seeding.")
    WHEN_TO_USE = [
        "Launch a chosen profile/project/executable/role — auto-decides "
        "between opening the project in this QGIS (same profile) and "
        "starting a new QGIS/QField process (different profile)",
        "Read or update the launcher qgis_settings.json (profile, "
        "executable, role, dev_mode, current_project)",
        "Open a .qgs/.qgz project in the running QGIS without "
        "launching a new process (profile cannot be switched "
        "in-session)",
        "Run launcher maintenance: drive_mappings (subst/rclone), "
        "local_sync robocopy sync, distribution profile seed/reset",
        "List running QGIS Live Harness sessions (~/.qgis-live registry)",
    ]

    def __init__(self, plugin):
        self._plugin = plugin

    # ---- helpers --------------------------------------------------------
    @staticmethod
    def _ok(payload):
        return json.dumps({"ok": True, **payload}, ensure_ascii=False)

    @staticmethod
    def _err(msg):
        return json.dumps({"ok": False, "error": str(msg)},
                          ensure_ascii=False)

    def _method_catalog(self):
        out = []
        for name in sorted(dir(self)):
            if name.startswith("_") or name in (
                    "NAME", "SUMMARY", "WHEN_TO_USE"):
                continue
            attr = getattr(self, name)
            if callable(attr):
                out.append({"name": name,
                            "doc": (inspect.getdoc(attr) or "").strip()})
        return out

    def _load(self):
        """(settings, settings_dir, project_root) を返す。"""
        return core.resolve_settings_dir(self._dir())

    def _dir(self):
        saved = QSettings().value("geo_launcher/settings_dir", "")
        return core.find_settings_dir(saved or None)

    def _collect_logs(self, fn):
        """fn() を実行し、core のログ出力を収集して (result, logs) を返す。"""
        logs = []
        prev = core._log
        core.set_logger(logs.append)
        try:
            return fn(), logs
        finally:
            core.set_logger(prev)

    # ---- カタログ -------------------------------------------------------
    def pluginInfo(self):
        """プラグインの自己記述(id/summary/when_to_use/methods)を返す。"""
        return self._ok({
            "id": PLUGIN_ID,
            "name": self.NAME,
            "summary": self.SUMMARY,
            "when_to_use": list(self.WHEN_TO_USE),
            "invoke": {"type": "bridge_call", "plugin_id": PLUGIN_ID,
                       "method": "<method>", "args": []},
            "methods": self._method_catalog(),
            "state": {"settings_dir": self._dir()},
        })

    def status(self):
        """実行時状態(設定dir・設定概要・検出数)を返す。"""
        d = self._dir()
        try:
            from qgis.core import QgsApplication, QgsProject
            cur_profile = os.path.basename(os.path.normpath(
                QgsApplication.qgisSettingsDirPath()))
            cur_project = QgsProject.instance().fileName()
        except Exception:  # noqa: BLE001
            cur_profile = cur_project = ""
        info = {"current_profile": cur_profile,
                "current_project": cur_project,
                "settings_dir": d,
                "settings_file": core.settings_path(d),
                "settings_exists": os.path.exists(core.settings_path(d))}
        if info["settings_exists"]:
            try:
                s, sdir, root = self._load()
                info["resolved_settings_dir"] = sdir
                info["project_root"] = root
                info["profile"] = s.get("profile")
                info["qgis_executable"] = s.get("qgis_executable")
                info["userrole"] = s.get("userrole")
                info["dev_mode"] = bool(s.get("dev_mode"))
                info["profile_count"] = len(core.list_profiles(sdir))
                info["project_count"] = len(
                    core.list_projects(s, root))
                info["version_count"] = len(
                    core.list_qgis_versions(portable_base=sdir))
                info["local_sync_needed"] = core.local_sync_needed(s, sdir)
            except Exception as e:  # noqa: BLE001 - 状態取得の失敗は情報として返す
                info["load_error"] = str(e)
        info["live_sessions"] = len(core.list_live_sessions())
        return self._ok(info)

    # ---- 設定 -----------------------------------------------------------
    def settingsDir(self, path=None):
        """設定ディレクトリの取得/変更。path指定時はQSettingsへ保存する。"""
        if path:
            QSettings().setValue("geo_launcher/settings_dir", str(path))
        return self._ok({"settings_dir": self._dir()})

    def getSettings(self):
        """解決済み qgis_settings.json(オーバーライド適用後)を返す。"""
        s, sdir, root = self._load()
        return self._ok({"settings": s, "settings_dir": sdir,
                         "project_root": root})

    def setSettings(self, values):
        """qgis_settings.json へ保存する(既存の未知キーは温存)。

        values: dict または JSON 文字列。例: {"profile": "geo_custom"}
        """
        if isinstance(values, str):
            values = json.loads(values)
        if not isinstance(values, dict):
            return self._err("values must be a dict or JSON object string")
        _, sdir, _ = self._load()
        p = core.save_settings(sdir, values)
        return self._ok({"saved": p})

    # ---- 列挙 -----------------------------------------------------------
    def listProfiles(self):
        """利用可能なプロファイル名/パスの一覧を返す。"""
        _, sdir, _ = self._load()
        return self._ok({"profiles": core.list_profiles(sdir)})

    def listProjects(self):
        """project_path 由来の .qgs/.qgz プロジェクト一覧を返す。"""
        s, _, root = self._load()
        return self._ok({"projects": core.list_projects(s, root)})

    def listVersions(self):
        """検出された QGIS/QField 実行ファイル一覧を返す。"""
        _, sdir, _ = self._load()
        return self._ok({
            "versions": core.list_qgis_versions(portable_base=sdir)})

    def listSessions(self):
        """稼働中の QGIS Live Harness セッション一覧を返す。"""
        return self._ok({"sessions": core.list_live_sessions()})

    def projectVersion(self, path):
        """指定 .qgs/.qgz の <qgis version> 属性を返す。"""
        return self._ok({"path": path,
                         "version": core.get_project_file_version(path)})

    # ---- 起動 -----------------------------------------------------------
    @staticmethod
    def _current_profile_name():
        """実行中QGISのプロファイル名 (geo_custom 等) を返す。"""
        try:
            from qgis.core import QgsApplication
            return os.path.basename(os.path.normpath(
                QgsApplication.qgisSettingsDirPath()))
        except Exception:  # noqa: BLE001
            return ""

    def launch(self, profile=None, project=None, executable=None,
               role=None, dev=None, mode="auto", discard=False):
        """QGIS/QField を起動する。

        引数はすべて省略可(省略時は qgis_settings.json の値を使用)。
        - profile: プロファイル名 (例 "geo_custom")
        - project: .qgs/.qgz パス、パスのリスト、"current"(現在開いている
          プロジェクト)、または None(設定値)
        - executable: qgis.bat / qfield.exe 等のパス
        - role: "Viewer" / "Editor" / "Administrator"
        - dev: True で WEBENGINE_* 開発環境変数を注入
        - mode: "auto"(既定) / "process" / "in_place"。
          auto は選択プロファイルが現在のプロファイルと同じなら
          別プロセスを起動せずこのQGISでプロジェクトを開き、
          異なる場合のみ新プロセスを起動する。
          process は常に新プロセス、in_place は常にこのQGISで開く
          (プロファイル不一致でも)
        - discard: in_place で開く際、未保存変更を破棄するか
          (未保存がある場合は discard=True が必須)

        起動前に drive_mappings / プロファイルシード / local_sync を
        実行する(Rust版の起動フローと同じ)。robocopy/rclone を含むため
        時間がかかる場合があり、GUIスレッドをその間ブロックする。
        """
        s, sdir, root = self._load()
        profile = (profile or s.get("profile") or "default").strip()
        exe = executable or s.get("qgis_executable") or ""
        if not exe:
            exe = core.auto_select_executable(s, root)
        role = role or s.get("userrole") or "Viewer"
        dev = s.get("dev_mode") if dev is None else bool(dev)
        if project is None:
            projects = list(s.get("project_path") or [])
        elif isinstance(project, str):
            projects = [project]
        else:
            projects = list(project)
        # "current" は現在開いているプロジェクトファイルへ解決する
        if any(str(p).lower() == "current" for p in projects):
            try:
                from qgis.core import QgsProject
                current = QgsProject.instance().fileName()
            except Exception:  # noqa: BLE001
                current = ""
            if not current:
                return self._err(
                    "no project is currently open (or it has never "
                    "been saved to a file)")
            projects = [
                current if str(p).lower() == "current" else p
                for p in projects]

        # mount/seed/local_sync は launch の前段として実行
        _, pre_logs = self._collect_logs(lambda: (
            core.mount_drive_mappings(s.get("drive_mappings", []), s),
            core.copy_profiles_at_startup(sdir, s),
            core.run_local_sync(s, sdir)))

        # auto 判定: 同一プロファイルならこのQGISで開く
        cur = self._current_profile_name()
        mode_l = str(mode).lower()
        if mode_l == "in_place" or (
                mode_l == "auto" and cur and cur == profile):
            if not projects:
                return self._err(
                    "no project specified to open in this QGIS")
            opened = self._open_project_here(
                projects[0], bool(discard))
            if not opened.get("ok"):
                return json.dumps(opened, ensure_ascii=False)
            return self._ok({
                "mode": "in_place",
                "profile": profile,
                "current_profile": cur,
                "profile_mismatch": bool(cur and cur != profile),
                "opened": opened["opened"],
                "skipped_projects": projects[1:],
                "launched": 0,
                "logs": pre_logs,
            })
        launched, logs = self._collect_logs(lambda: core.launch_qgis(
            profile, projects, root, exe, role, bool(dev), sdir))
        return self._ok({
            "mode": "process",
            "profile": profile, "executable": exe, "role": role,
            "dev_mode": bool(dev), "projects": projects,
            "launched": launched,
            "logs": pre_logs + logs,
        })

    @staticmethod
    def _open_project_here(path, discard):
        """p.read() でプロジェクトを開く内部処理。dict を返す。"""
        from qgis.core import QgsProject
        p = QgsProject.instance()
        if not os.path.isfile(path):
            return {"ok": False,
                    "error": "project file not found: {}".format(path)}
        if p.isDirty() and not discard:
            return {"ok": False,
                    "error": "current project has unsaved changes; "
                             "pass discard=True to replace it"}
        if not p.read(path):
            return {"ok": False,
                    "error": "failed to read project: {}".format(path)}
        return {"ok": True, "opened": path}

    def openProject(self, path="current", discard=False):
        """指定プロジェクトをこのQGISで開く(別プロセスを起動しない)。

        - path: .qgs/.qgz のパス、または "current"(開き直し=リロード)
        - discard: 未保存変更を破棄して開くか。未保存がある場合は
          discard=True が必須(データ損失防止の安全側)

        プロファイル自体は実行中プロセスのものが継続する。
        """
        from qgis.core import QgsProject
        if str(path).lower() == "current":
            path = QgsProject.instance().fileName()
            if not path:
                return self._err("no project is currently open")
        res = self._open_project_here(path, bool(discard))
        return json.dumps(res, ensure_ascii=False)

    # ---- 保守 -----------------------------------------------------------
    def mountDrives(self):
        """drive_mappings (subst/rclone sync/rclone mount) を実行する。

        rclone sync/mount は時間がかかる場合があり、GUIスレッドを
        その間ブロックする。
        """
        s, _, _ = self._load()
        _, logs = self._collect_logs(
            lambda: core.mount_drive_mappings(
                s.get("drive_mappings", []), s))
        return self._ok({"logs": logs})

    def localSync(self):
        """local_sync (robocopy ミラー) を実行する。長時間の場合あり。"""
        s, sdir, _ = self._load()
        ran, logs = self._collect_logs(
            lambda: core.run_local_sync(s, sdir))
        return self._ok({"ran": bool(ran), "logs": logs})

    def syncProfiles(self):
        """profile_source_url のマニフェストから配布プロファイルを同期する。

        マニフェスト形式: {"version","url","sha256"}。
        version が profiles_version と同じなら何もしない。
        取得した zip は検証後 <settings_dir>/profiles を丸ごと置換する。
        """
        s, sdir, _ = self._load()
        try:
            changed, logs = self._collect_logs(
                lambda: core.sync_remote_profiles(s, sdir))
        except RuntimeError as e:
            return self._err(str(e))
        return self._ok({"changed": bool(changed), "logs": logs})

    def ensurePlugins(self, profile=None):
        """required_plugins の指定プラグインを対象プロファイルへ導入する。

        settings["required_plugins"]: [{"id":...}, {"id","url","sha256"}]
        url 未指定時は公式リポジトリから最新版を解決してダウンロード。
        profile 指定時はそのプロファイルのみ対象。現在のプロファイルへ
        導入された分は有効化して即ロードも試行する。
        """
        s, sdir, _ = self._load()
        names = [profile] if profile else None
        try:
            installed, logs = self._collect_logs(
                lambda: core.ensure_plugins(
                    s, sdir, profile_names=names))
        except RuntimeError as e:
            return self._err(str(e))
        loaded = []
        cur = self._current_profile_name()
        if installed and cur and (not names or cur in names):
            from qgis.utils import loadPlugin, startPlugin
            from qgis.PyQt.QtCore import QSettings
            for pid in installed:
                try:
                    QSettings().setValue("PythonPlugins/" + pid, True)
                    if loadPlugin(pid) and startPlugin(pid):
                        loaded.append(pid)
                except Exception:  # noqa: BLE001
                    pass
        return self._ok({
            "installed": installed, "loaded": loaded, "logs": logs})

    def seedProfiles(self):
        """配布 profiles を %APPDATA%\\QGIS 配下へシードする。

        profile_source_url 設定時は先にリモート同期される。
        required_plugins 設定時は必須プラグインの導入も行う。
        """
        s, sdir, _ = self._load()
        _, logs = self._collect_logs(
            lambda: core.copy_profiles_at_startup(sdir, s))
        return self._ok({"logs": logs})

    def resetProfiles(self, confirm=False):
        """既存 QGIS プロファイルを全削除し配布版を再コピーする。

        confirm=True が必須(破壊的操作のため)。長時間の場合あり。
        """
        if not confirm:
            return self._err(
                "confirm=True required: deletes existing QGIS profiles")
        s, sdir, _ = self._load()
        err, logs = self._collect_logs(
            lambda: core.reset_profiles(sdir, s))
        if err:
            return self._err(err)
        return self._ok({"logs": logs})

    # ---- ダイアログ -----------------------------------------------------
    def openDialog(self):
        """ランチャーダイアログを開く。"""
        self._plugin.open_dialog()
        return self._ok({"opened": True})

    def closeDialog(self):
        """ランチャーダイアログを閉じる。"""
        self._plugin.close_dialog()
        return self._ok({"closed": True})
