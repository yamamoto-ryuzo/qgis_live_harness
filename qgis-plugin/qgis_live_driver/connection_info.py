"""接続情報ダイアログ(初回利用の導線)。

リモート制御を有効化したユーザーが「次に何をすればよいか」迷わないよう、
MCP/RESTの接続情報と、MCPクライアントへそのまま貼れる設定JSONを
コピー可能な形でまとめて表示する。

- メニュー「プラグイン > QGIS Live Driver > Connection Info」から開く
- リモート制御トグルをONにした直後にも自動表示される
- リモート制御OFFでも開ける。その場合は有効化手順と
  stdio shim の設定(セッション自動検出のため接続情報を含まない)だけを出す
"""

import json
import os
import sys

from qgis.PyQt.QtCore import QCoreApplication


def _tr(s):
    return QCoreApplication.translate("qgis_live_driver", s)


def _python_exe():
    """stdio shim を動かせるPython実行パスを推定する。

    QGIS内では sys.executable が qgis-bin.exe を指すため使えない。
    同梱Pythonは sys.exec_prefix/python.exe にある(実測済み)。
    見つからなければ PATH 解決任せの "python" を返す。
    """
    name = "python.exe" if os.name == "nt" else "python"
    for base in (sys.exec_prefix, sys.base_prefix):
        cand = os.path.join(base, name)
        if os.path.isfile(cand):
            return cand
    return "python"


def _stdio_config(plugin_dir):
    """MCPクライアント用 stdio 設定(JSON文字列)を返す。

    shimはレジストリから稼働セッションを自動検出するため、
    リモート制御OFFでも同じ設定を出せる。
    """
    shim = os.path.join(plugin_dir, "mcp_stdio.py")
    return json.dumps(
        {"mcpServers": {"qgis-live": {
            "command": _python_exe(), "args": [shim]}}},
        ensure_ascii=False, indent=2)


def _http_config(port, token):
    return json.dumps(
        {"mcpServers": {"qgis-live": {
            "url": f"http://127.0.0.1:{port}/mcp",
            "headers": {"Authorization": f"Bearer {token}"}}}},
        ensure_ascii=False, indent=2)


def _curl_example(port, token):
    return (f'curl.exe -H "Authorization: Bearer {token}" '
            f"http://127.0.0.1:{port}/api/status")


def _repo_status(plugin_dir):
    """harness repo の解決結果を返す(mode_switch側の解決と同一経路)。"""
    try:
        from .mode_switch import repo_root
        return repo_root(os.path.join(plugin_dir, "__init__.py"))
    except Exception:  # nosec B110  # 設計上の許容
        return None


def build_info(plugin):
    """表示用テキストとコピー用スニペットを組み立てて返す。"""
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    drv = plugin.driver
    lines = []
    snippets = {"stdio": _stdio_config(plugin_dir)}
    repo = _repo_status(plugin_dir)
    lines.append(
        _tr("Harness repository") + ": "
        + (repo or _tr(
            "(not configured — set it via Deploy Mode or the "
            "Locate button below)")))
    if drv is None:
        lines.append(_tr(
            "Remote control is OFF.\n"
            "Enable it via Plugins > QGIS Live Driver > "
            "Remote Control (localhost only), then press Refresh."))
        lines.append("")
    else:
        port = drv.http_port
        reg_dir = os.environ.get(
            "QGIS_LIVE_REGISTRY",
            os.path.join(os.path.expanduser("~"), ".qgis-live"))
        reg_path = getattr(plugin, "_reg_path", None) or os.path.join(
            reg_dir, f"{os.getpid()}-qgis_live_driver.json")
        lines.append(_tr("Remote control is enabled."))
        lines.append("")
        if port:
            lines.append(
                f"MCP (Streamable HTTP): http://127.0.0.1:{port}/mcp")
            lines.append(
                f"REST API base:         http://127.0.0.1:{port}/api")
        lines.append(f"{_tr('Registry file')}: {reg_path}")
        lines.append(f"{_tr('Live dir')}: {drv.dir}")
        lines.append(f"{_tr('Token')}: {drv.token}")
        lines.append("")
        if port:
            snippets["http"] = _http_config(port, drv.token)
            snippets["curl"] = _curl_example(port, drv.token)
            snippets["token"] = drv.token
    lines.append("--- " + _tr(
        "MCP client config (stdio shim; auto-discovers this session)")
        + " ---")
    lines.append(snippets["stdio"])
    if "http" in snippets:
        lines.append("")
        lines.append("--- " + _tr(
            "MCP client config (Streamable HTTP)") + " ---")
        lines.append(snippets["http"])
        lines.append("")
        lines.append("--- " + _tr("REST example (curl)") + " ---")
        lines.append(snippets["curl"])
    return "\n".join(lines), snippets


def show_dialog(plugin):
    """接続情報ダイアログを非モーダルで開いて返す。"""
    from qgis.PyQt.QtWidgets import (
        QApplication, QDialog, QDialogButtonBox, QHBoxLayout,
        QPlainTextEdit, QPushButton, QVBoxLayout)
    from qgis.PyQt.QtGui import QFontDatabase

    dlg = QDialog(plugin.iface.mainWindow())
    dlg.setWindowTitle(_tr("QGIS Live Driver — Connection Info"))
    lay = QVBoxLayout(dlg)

    text = QPlainTextEdit(dlg)
    text.setReadOnly(True)
    text.setFont(QFontDatabase.systemFont(
        QFontDatabase.SystemFont.FixedFont))
    lay.addWidget(text)

    btn_row = QHBoxLayout()
    copies = []
    for label, key in (
            (_tr("Copy MCP config (stdio)"), "stdio"),
            (_tr("Copy MCP config (HTTP)"), "http"),
            (_tr("Copy token"), "token"),
            (_tr("Copy REST example"), "curl")):
        b = QPushButton(label, dlg)
        btn_row.addWidget(b)
        copies.append((b, key))
    btn_row.addStretch(1)
    refresh_btn = QPushButton(_tr("Refresh"), dlg)
    btn_row.addWidget(refresh_btn)
    repo_btn = QPushButton(_tr("Locate harness repo…"), dlg)
    btn_row.addWidget(repo_btn)
    lay.addLayout(btn_row)

    btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close,
                            parent=dlg)
    btns.rejected.connect(dlg.reject)
    lay.addWidget(btns)

    state = {"snippets": {}}

    def _notify(msg):
        try:
            plugin._hot_notify("info", msg)
        except Exception:  # nosec B110  # 設計上の許容
            pass

    def _refresh():
        body, snippets = build_info(plugin)
        text.setPlainText(body)
        state["snippets"] = snippets
        for b, key in copies:
            b.setEnabled(key in snippets)

    def _make_copy(key):
        def _copy():
            s = state["snippets"].get(key)
            if s:
                QApplication.clipboard().setText(s)
                _notify(_tr("Copied to clipboard"))
        return _copy

    for b, key in copies:
        b.clicked.connect(_make_copy(key))
    refresh_btn.clicked.connect(_refresh)

    def _locate_repo():
        """harness repoフォルダを選択させてQSettingsへ保存する。"""
        from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        d = QFileDialog.getExistingDirectory(
            dlg, _tr("Select the qgis_live_harness repository folder"),
            _repo_status(plugin_dir) or "")
        if not d:
            return
        try:
            from .mode_switch import set_repo_path
            ok, msg = set_repo_path(d)
        except Exception as e:  # nosec B110  # 設計上の許容
            ok, msg = False, str(e)
        if not ok:
            QMessageBox.warning(
                dlg, "QGIS Live Driver",
                _tr("Not a harness repository") + "\n" + msg)
            return
        _notify(_tr("Harness repository set: {0}").format(d))
        _refresh()

    repo_btn.clicked.connect(_locate_repo)

    _refresh()
    dlg.resize(680, 560)
    dlg.show()
    return dlg
