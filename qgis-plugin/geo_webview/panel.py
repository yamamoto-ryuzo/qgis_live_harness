# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GeoWebViewPanel
                                 A QGIS plugin
 Navigate QGIS map views through external permalink system - Panel Version
                             -------------------
        begin                : 2025-10-05
        git sha              : $Format:%H$
        copyright            : (C) 2025 by yamamoto-ryuzo
        email                :
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDockWidget, QWidget
from qgis.PyQt.QtCore import Qt, QSize, QCoreApplication
from qgis.PyQt.QtGui import QGuiApplication, QIcon

# UIファイルのパスを指定
FORM_CLASS = None
try:
    FORM_CLASS, _ = uic.loadUiType(os.path.join(
        os.path.dirname(__file__), 'panel_base.ui'))
except Exception:
    # Defer UI loading errors to runtime. Keep FORM_CLASS as None so the
    # module can be imported in environments where Qt/PyQt or uic is not
    # available (for example when running static analysis or tests).
    FORM_CLASS = None


class GeoWebViewPanel(QDockWidget):
    """geo_webviewのパネルクラス

    Qt Designerで作成されたUIファイルを読み込んでドッキング可能なパネルとして表示
    """

    def __init__(self, parent=None):
        """コンストラクタ

        Args:
            parent: 親ウィジェット
        """
        super(GeoWebViewPanel, self).__init__(parent)

        # パネルのタイトルを設定
        self.setWindowTitle(QCoreApplication.translate(
            'geo_webview', "WebView"))

        # ドッキングエリアを設定（左側を優先、右側も可能）
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        # 内部ウィジェットを作成
        self.widget = QWidget()
        # If FORM_CLASS could not be loaded (e.g. uic unavailable), create a
        # minimal fallback UI so the plugin can still import and display a
        # helpful message instead of failing entirely.
        if FORM_CLASS is None:
            self.ui = None
            try:
                # Create a minimal placeholder UI
                from qgis.PyQt.QtWidgets import QLabel, QVBoxLayout
                layout = QVBoxLayout()
                label = QLabel(self.tr("Could not load the UI file. Please consider reinstalling the plugin."))
                layout.addWidget(label)
                self.widget.setLayout(layout)
            except Exception:  # nosec B110  # 設計上の許容
                # If even Qt widgets are not available, leave widget empty
                pass
        else:
            self.ui = FORM_CLASS()
            self.ui.setupUi(self.widget)

        # 直接アクセス用のプロパティを追加（ui が None の場合は None を代入）
        self.pushButton_generate = getattr(self.ui, 'pushButton_generate', None)
        self.pushButton_navigate = getattr(self.ui, 'pushButton_navigate', None)
        self.pushButton_copy = getattr(self.ui, 'pushButton_copy', None)
        # newly added UI elements
        self.pushButton_clipboard = getattr(self.ui, 'pushButton_clipboard', None)
        self.pushButton_paste = getattr(self.ui, 'pushButton_paste', None)
        self.pushButton_settings = getattr(self.ui, 'pushButton_settings', None)
        self.lineEdit_permalink = getattr(self.ui, 'lineEdit_permalink', None)
        self.lineEdit_navigate = getattr(self.ui, 'lineEdit_navigate', None)
        self.label_server_status = getattr(self.ui, 'label_server_status', None)
        self.comboBox_themes = getattr(self.ui, 'comboBox_themes', None)
        # テーマ保存UI(panel_base.ui のテーマ選択行の直下)
        self.lineEdit_theme_name = getattr(self.ui, 'lineEdit_theme_name', None)
        self.pushButton_save_theme = getattr(self.ui, 'pushButton_save_theme', None)

        # KASUGAI Canvas エクスポート/起動ボタン・エンジン選択
        self.pushButton_kasugai_export = getattr(self.ui, 'pushButton_kasugai_export', None)
        self.pushButton_kasugai_launch = getattr(self.ui, 'pushButton_kasugai_launch', None)
        self.pushButton_kasugai_launch_hosted = getattr(self.ui, 'pushButton_kasugai_launch_hosted', None)
        self.pushButton_kasugai_folder = getattr(self.ui, 'pushButton_kasugai_folder', None)
        # エクスポート物のZIPダウンロード(ブラウザ経由・要HTTPサーバー)
        self.pushButton_kasugai_zip = getattr(self.ui, 'pushButton_kasugai_zip', None)
        # ドキュメントサイト(GitHub Pages)を開くヘルプボタン
        self.pushButton_kasugai_help = getattr(self.ui, 'pushButton_kasugai_help', None)
        # Canvas の UI設定管理画面(ローカルアプリ専用)を開くボタン
        self.pushButton_kasugai_admin = getattr(self.ui, 'pushButton_kasugai_admin', None)
        # 保存先表示(クリックでフォルダ選択)と既定リセット
        self.pushButton_kasugai_outdir = getattr(self.ui, 'pushButton_kasugai_outdir', None)
        self.pushButton_kasugai_outdir_reset = getattr(self.ui, 'pushButton_kasugai_outdir_reset', None)
        self._kasugai_outdir_path = ''
        self.comboBox_engine = getattr(self.ui, 'comboBox_engine', None)
        # CDN(ホスト版エンジン)選択コンボ(▶ WebView のチャンネル)
        self.comboBox_hosted = getattr(self.ui, 'comboBox_hosted', None)
        # ベクター出力形式コンボ(推奨形式スイッチのパネル側入口)
        self.comboBox_vector_format = getattr(
            self.ui, 'comboBox_vector_format', None)
        # 非表示レイヤのデータ変換スキップ(高速化)チェック
        self.checkBox_visible_only = getattr(
            self.ui, 'checkBox_visible_only', None)
        # カスタムレイヤタブ(site= 付与+custom-layer タブ)チェック
        self.checkBox_site_control = getattr(
            self.ui, 'checkBox_site_control', None)
        # レイヤ別 .kasc オプション設定テーブル(site/order/list/opts)
        self.treeWidget_kasugai_layers = getattr(
            self.ui, 'treeWidget_kasugai_layers', None)
        self.pushButton_kasugai_layers_refresh = getattr(
            self.ui, 'pushButton_kasugai_layers_refresh', None)
        self.pushButton_kasugai_layers_edit = getattr(
            self.ui, 'pushButton_kasugai_layers_edit', None)
        self.pushButton_kasugai_layers_view = getattr(
            self.ui, 'pushButton_kasugai_layers_view', None)
        self.pushButton_kasugai_legend_up = getattr(
            self.ui, 'pushButton_kasugai_legend_up', None)
        self.pushButton_kasugai_legend_down = getattr(
            self.ui, 'pushButton_kasugai_legend_down', None)
        self._kasugai_layers_mode = 'edit'
        try:
            self._init_kasugai_layers_ui()
        except Exception:  # nosec B110  # 設計上の許容
            pass
        try:
            self._init_kasugai_filter_ui()
        except Exception:  # nosec B110  # 設計上の許容
            pass
        # HTTP server toggle checkbox (added to UI)
        self.checkBox_server_toggle = getattr(self.ui, 'checkBox_server_toggle', None)
        # External control checkbox (new in UI)
        self.checkBox_external_control = getattr(self.ui, 'checkBox_external_control', None)
        # Port number spinbox (new in UI)
        self.spinBox_port = getattr(self.ui, 'spinBox_port', None)
        # Check access button (new in UI)
        self.pushButton_check_access = getattr(self.ui, 'pushButton_check_access', None)
        # Standard port buttons (new in UI)
        self.pushButton_port_80 = getattr(self.ui, 'pushButton_port_80', None)
        self.pushButton_port_443 = getattr(self.ui, 'pushButton_port_443', None)

        # 共有/プレゼンテーション/MAC認証の追加UI(動的生成)
        self.groupBox_sharing = None
        self.pushButton_present = None
        self.comboBox_received = None
        self.checkBox_mac_auth = None
        self.lineEdit_mac_auth = None
        try:
            self._build_sharing_group()
        except Exception:  # nosec B110  # 設計上の許容
            pass

        # ウィジェットを設定
        self.setWidget(self.widget)

        # パネルのサイズを設定（左側パネルに適したサイズ）
        self.setMinimumWidth(250)
        self.setMaximumWidth(400)

        # パネルの特徴を設定
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable |
                         QDockWidget.DockWidgetFeature.DockWidgetFloatable |
                         QDockWidget.DockWidgetFeature.DockWidgetClosable)

        # UI要素を翻訳
        self.translate_ui()

        # KASUGAI Canvas 未インストール時は「▶ Canvas」をグレーアウト。
        # ドックの再表示時にも再判定し、インストール/設定後に有効化されるようにする
        try:
            self.visibilityChanged.connect(self._on_visibility_changed)
        except Exception:  # nosec B110  # 設計上の許容
            pass

        # 設定ボタンのアイコンを読み込み、枠付きスタイルを適用
        try:
            if self.pushButton_settings is not None:
                try:
                    icon_path = os.path.join(os.path.dirname(__file__), 'icon', 'setting.png')
                    if os.path.exists(icon_path):
                        self.pushButton_settings.setIcon(QIcon(icon_path))
                        self.pushButton_settings.setIconSize(QSize(20, 20))
                    # add framed look similar to ICO frame
                    self.pushButton_settings.setStyleSheet('border:1px solid #888; border-radius:4px; padding:2px;')
                except Exception:  # nosec B110  # 設計上の許容
                    pass
                # connect to placeholder settings dialog opener
                try:
                    from .settings_dialog import SettingsDialog

                    def _open_settings():
                        try:
                            dlg = SettingsDialog(self)
                            dlg.exec()
                            # インストール先の登録/解除を「▶ Canvas」に即反映
                            self.update_canvas_launch_state()
                        except Exception:  # nosec B110  # 設計上の許容
                            pass

                    self.pushButton_settings.clicked.connect(_open_settings)
                except Exception:  # nosec B110  # 設計上の許容
                    # no settings dialog available; ignore
                    pass
        except Exception:  # nosec B110  # 設計上の許容
            pass

        # クリップボード関連のシグナルを接続
        try:
            _ = QGuiApplication.clipboard()
            if self.pushButton_clipboard is not None:
                # コピー: 現在の permalink テキストをクリップボードへ
                self.pushButton_clipboard.clicked.connect(self._on_copy_permalink_to_clipboard)
            if self.pushButton_paste is not None:
                # 貼り付け: クリップボードから navigate テキストボックスへ
                self.pushButton_paste.clicked.connect(self._on_paste_from_clipboard)
        except Exception:  # nosec B110  # 設計上の許容
            # Qt 環境が利用できない場合は無視
            pass

    def translate_ui(self):
        """UI要素のテキストを翻訳"""
        # NOTE: i18n/<lang>.json のコンテキスト 'geo_webview' に対応させるため
        # ラッパー関数ではなく QCoreApplication.translate を直接呼ぶこと
        from qgis.PyQt.QtCore import QCoreApplication

        # タブタイトル
        if getattr(self.ui, 'tabWidget_main', None) is not None:
            for _name, _text in (
                    ('tab_web', "Web"),
                    ('tab_theme', "Theme"),
                    ('tab_permalink', "Permalink"),
                    ('tab_share', "Share")):
                _page = getattr(self.ui, _name, None)
                if _page is not None:
                    _idx = self.ui.tabWidget_main.indexOf(_page)
                    if _idx >= 0:
                        self.ui.tabWidget_main.setTabText(
                            _idx, QCoreApplication.translate('geo_webview', _text))

        # グループボックスのタイトル
        if hasattr(self.ui, 'groupBox_webdist'):
            self.ui.groupBox_webdist.setTitle(QCoreApplication.translate('geo_webview', "Web Distribution (Serverless)"))
        if hasattr(self.ui, 'groupBox_server'):
            self.ui.groupBox_server.setTitle(QCoreApplication.translate('geo_webview', "HTTP Server"))
        if hasattr(self.ui, 'groupBox_generate'):
            self.ui.groupBox_generate.setTitle(QCoreApplication.translate('geo_webview', "Generate Permalink"))
        if hasattr(self.ui, 'groupBox_permalink'):
            self.ui.groupBox_permalink.setTitle(QCoreApplication.translate('geo_webview', "Current Permalink"))
        if hasattr(self.ui, 'groupBox_navigate'):
            self.ui.groupBox_navigate.setTitle(QCoreApplication.translate('geo_webview', "Navigate to Location"))

        # ラベル
        if hasattr(self.ui, 'label_webdist_info'):
            self.ui.label_webdist_info.setText(QCoreApplication.translate('geo_webview', "Export the project as a .kasc+canvas_data/ package playable on Cesium / MapLibre / OpenLayers / Leaflet / GSI Maps / Navara — deliver from any static host."))
        if hasattr(self.ui, 'label_engine'):
            self.ui.label_engine.setText(QCoreApplication.translate('geo_webview', "Engine:"))
        if hasattr(self.ui, 'label_hosted'):
            self.ui.label_hosted.setText(QCoreApplication.translate('geo_webview', "CDN:"))
        if hasattr(self.ui, 'comboBox_hosted'):
            self.ui.comboBox_hosted.setToolTip(QCoreApplication.translate(
                'geo_webview',
                "Hosted engine channel used by ▶ WebView — 'stable'/'unstable' (kasugai-canvas-web stages) or a custom base URL ending with '/'"))
        if hasattr(self.ui, 'label_generate_info'):
            self.ui.label_generate_info.setText(QCoreApplication.translate('geo_webview', "Generate a permalink for the current map view"))
        if hasattr(self.ui, 'label_theme_selection'):
            self.ui.label_theme_selection.setText(QCoreApplication.translate('geo_webview', "Theme/Layer State:"))
        if hasattr(self.ui, 'label_navigate_info'):
            self.ui.label_navigate_info.setText(QCoreApplication.translate('geo_webview', "Enter a permalink to navigate"))

        # Buttons now include the icon/label together; set button texts instead
        if hasattr(self.ui, 'label_kasugai'):
            self.ui.label_kasugai.setText(QCoreApplication.translate('geo_webview', "KASUGAI Canvas:"))
        if hasattr(self.ui, 'pushButton_kasugai_export'):
            self.ui.pushButton_kasugai_export.setText(QCoreApplication.translate('geo_webview', "Export"))
            self.ui.pushButton_kasugai_export.setToolTip(QCoreApplication.translate(
                'geo_webview',
                "Export visible layers as a KASUGAI Canvas project (.kasc + canvas_data/ + engine launcher HTMLs) — files only"))
        if hasattr(self.ui, 'pushButton_kasugai_launch'):
            self.ui.pushButton_kasugai_launch.setText(QCoreApplication.translate('geo_webview', "▶ Canvas"))
        if hasattr(self.ui, 'pushButton_kasugai_launch_hosted'):
            self.ui.pushButton_kasugai_launch_hosted.setText(QCoreApplication.translate('geo_webview', "▶ WebView"))
            self.ui.pushButton_kasugai_launch_hosted.setToolTip(QCoreApplication.translate(
                'geo_webview',
                "Open via serverless WEB delivery — hosted engine (GitHub Pages, channel = CDN combo) + this server's data delivery (no Canvas install needed; requires internet + HTTP server running)"))
        if hasattr(self.ui, 'comboBox_engine'):
            self.ui.comboBox_engine.setToolTip(QCoreApplication.translate(
                'geo_webview',
                "Engine used by the Open button (the exported package plays on all engines)"))
            # エンジン選択を itemData 付きで再構成(.ui 側の項目は上書き)
            try:
                current = self.ui.comboBox_engine.currentData()
            except Exception:  # nosec B110  # 設計上の許容
                current = None
            self.ui.comboBox_engine.blockSignals(True)
            self.ui.comboBox_engine.clear()
            self.ui.comboBox_engine.addItem("Cesium (3D)", 'cesium')
            self.ui.comboBox_engine.addItem("MapLibre", 'maplibre')
            self.ui.comboBox_engine.addItem("OpenLayers", 'openlayers')
            self.ui.comboBox_engine.addItem("Leaflet", 'leaflet')
            self.ui.comboBox_engine.addItem("GSI Maps", 'gsimaps')
            self.ui.comboBox_engine.addItem("Navara", 'navara')
            if current:
                idx = self.ui.comboBox_engine.findData(current)
                if idx >= 0:
                    self.ui.comboBox_engine.setCurrentIndex(idx)
            self.ui.comboBox_engine.blockSignals(False)
        if hasattr(self.ui, 'label_vformat'):
            self.ui.label_vformat.setText(QCoreApplication.translate('geo_webview', "Format:"))
        if hasattr(self.ui, 'comboBox_vector_format'):
            self.ui.comboBox_vector_format.setToolTip(QCoreApplication.translate(
                'geo_webview',
                "Vector export format — 'native' references readable sources as-is; 'recommended' converts all vectors to FlatGeobuf and places them in canvas_data/ (flatgeobuf: lines, bbox=auto range reads in Canvas); 'geojson' converts ALL vectors to GeoJSON for other WebGIS interop"))
            # 項目を itemData 付きで再構成(.ui 側の項目は上書き)
            try:
                current = self.ui.comboBox_vector_format.currentData()
            except Exception:  # nosec B110  # 設計上の許容
                current = None
            self.ui.comboBox_vector_format.blockSignals(True)
            self.ui.comboBox_vector_format.clear()
            self.ui.comboBox_vector_format.addItem(
                QCoreApplication.translate('geo_webview', "native (reference as-is)"), 'native')
            self.ui.comboBox_vector_format.addItem(
                QCoreApplication.translate('geo_webview', "recommended (FlatGeobuf → canvas_data/)"), 'recommended')
            self.ui.comboBox_vector_format.addItem(
                QCoreApplication.translate('geo_webview', "geojson (WEB interop → GeoJSON)"), 'geojson')
            if current:
                idx = self.ui.comboBox_vector_format.findData(current)
                if idx >= 0:
                    self.ui.comboBox_vector_format.setCurrentIndex(idx)
            self.ui.comboBox_vector_format.blockSignals(False)
        if hasattr(self.ui, 'checkBox_visible_only'):
            self.ui.checkBox_visible_only.setText(QCoreApplication.translate(
                'geo_webview', "Visible data only (faster)"))
            self.ui.checkBox_visible_only.setToolTip(QCoreApplication.translate(
                'geo_webview',
                "Only output visible layers — hidden layers are not written to the .kasc at all (basemap-group XYZ candidates keep their base: rows for the background selector, as before). Skipped layers cannot be turned on in Canvas. Uncheck to emit hidden layers as | off rows with all data converted (whole-project migration)"))
        if hasattr(self.ui, 'checkBox_site_control'):
            self.ui.checkBox_site_control.setText(QCoreApplication.translate(
                'geo_webview', "Custom layers tab"))
            self.ui.checkBox_site_control.setToolTip(QCoreApplication.translate(
                'geo_webview',
                'Group layers by their layer-tree group name into a custom "Layers" tab in KASUGAI Canvas (site=<group> on each layer row + custom-layer plugin tab for per-group on/off and ordering). All layers stay on the standard tab (shown as "System layers" while the custom tab exists); use list=off to hide a row there. Ungrouped layers go to "Misc". Per-layer override: layer custom properties kasugai_site / kasugai_order'))
        if hasattr(self.ui, 'pushButton_kasugai_folder'):
            self.ui.pushButton_kasugai_folder.setText('📁')
            self.ui.pushButton_kasugai_folder.setToolTip(
                QCoreApplication.translate(
                    'geo_webview',
                    "Open the export folder (.kasc / canvas_data/ / engine launchers)"))
        if hasattr(self.ui, 'pushButton_kasugai_outdir_reset'):
            self.ui.pushButton_kasugai_outdir_reset.setToolTip(
                QCoreApplication.translate(
                    'geo_webview',
                    "Reset to the default destination (KASUGAI Canvas install or Documents)"))
        if hasattr(self.ui, 'pushButton_kasugai_zip'):
            self.ui.pushButton_kasugai_zip.setText('ZIP')
            self.ui.pushButton_kasugai_zip.setToolTip(
                QCoreApplication.translate(
                    'geo_webview',
                    "Download the export package as kasugai_canvas_<channel>.zip in the browser — generated on demand at download time (requires the HTTP server running). The filename follows the CDN combo channel. For static-host deployment and Re:Earth geo_suite 'qgis:' import"))
        if hasattr(self.ui, 'pushButton_kasugai_help'):
            self.ui.pushButton_kasugai_help.setToolTip(
                QCoreApplication.translate(
                    'geo_webview',
                    "Open the geo_webview documentation site in the browser"))
        if hasattr(self.ui, 'pushButton_kasugai_admin'):
            self.ui.pushButton_kasugai_admin.setText(
                QCoreApplication.translate('geo_webview', "Admin"))
            self.ui.pushButton_kasugai_admin.setToolTip(
                QCoreApplication.translate(
                    'geo_webview',
                    "Open the KASUGAI Canvas UI-config admin screen in the browser — per-engine UI show/hide, control defaults and startup tab. Requires the local Canvas app running (port 8510)"))

        # ボタン
        if hasattr(self.ui, 'pushButton_generate'):
            self.ui.pushButton_generate.setText(QCoreApplication.translate('geo_webview', "Generate Permalink"))
        if hasattr(self.ui, 'pushButton_copy'):
            self.ui.pushButton_copy.setText(QCoreApplication.translate('geo_webview', "URLCopy"))
        if hasattr(self.ui, 'pushButton_navigate'):
            self.ui.pushButton_navigate.setText(QCoreApplication.translate('geo_webview', "Navigate"))
        if hasattr(self.ui, 'pushButton_save_theme'):
            self.ui.pushButton_save_theme.setText(QCoreApplication.translate('geo_webview', "Save Theme"))
            self.ui.pushButton_save_theme.setToolTip(QCoreApplication.translate('geo_webview', "Save the current layer visibility and styles as a map theme"))
        if hasattr(self.ui, 'lineEdit_theme_name'):
            self.ui.lineEdit_theme_name.setPlaceholderText(QCoreApplication.translate('geo_webview', "New theme name"))

        # プレースホルダーテキスト
        if hasattr(self.ui, 'lineEdit_permalink'):
            self.ui.lineEdit_permalink.setPlaceholderText(QCoreApplication.translate('geo_webview', "Generated permalink will appear here"))
        if hasattr(self.ui, 'lineEdit_navigate'):
            self.ui.lineEdit_navigate.setPlaceholderText(QCoreApplication.translate('geo_webview', "Paste permalink here"))

        # コンボボックスの項目
        if hasattr(self.ui, 'comboBox_themes'):
            # 既存の項目をクリアして翻訳済みの項目を追加
            self.ui.comboBox_themes.clear()
            self.ui.comboBox_themes.addItem(QCoreApplication.translate('geo_webview', "-- No Theme (Position Only) --"), "__no_theme__")
            # ツールチップも翻訳
            self.ui.comboBox_themes.setToolTip(QCoreApplication.translate('geo_webview', "Select theme option: no theme (position only) or specific theme"))
        # External control checkbox
        if hasattr(self.ui, 'checkBox_external_control'):
            self.ui.checkBox_external_control.setText(QCoreApplication.translate('geo_webview', "External Control"))
            self.ui.checkBox_external_control.setToolTip(QCoreApplication.translate('geo_webview', "When enabled, map view can be updated by external URLs"))
        # Server enable checkbox (HTTP Server グループ内)
        if hasattr(self.ui, 'checkBox_server_toggle'):
            self.ui.checkBox_server_toggle.setText(QCoreApplication.translate('geo_webview', "Enable"))
            self.ui.checkBox_server_toggle.setToolTip(QCoreApplication.translate('geo_webview', "Start/stop the embedded HTTP server (/kasugai, /export-data/, /present, /screenshot)"))

        # 「▶ Canvas」の有効/無効とツールチップをインストール状態に合わせる
        self.update_canvas_launch_state()

    def _on_visibility_changed(self, visible):
        if visible:
            self.update_canvas_launch_state()

    # --- レイヤ別 .kasc オプション設定(Layers タブ) --------------------
    # site= / order= / list=off / 追加opts をレイヤ customProperty
    # (kasugai_site/kasugai_order/kasugai_list/kasugai_opts)へ
    # 読み書きする。エクスポート側は customProperty をそのまま読むため
    # UI と .kasc の間に別の保存層は持たない。

    def _init_kasugai_layers_ui(self):
        """Layers タブのテーブル配線(初回構築・更新ボタン・ツリー変更追従)。"""
        tw = self.treeWidget_kasugai_layers
        if tw is None:
            return
        tw.itemChanged.connect(self._on_kasugai_layer_item_changed)
        if self.pushButton_kasugai_layers_refresh is not None:
            self.pushButton_kasugai_layers_refresh.clicked.connect(
                self._rebuild_kasugai_layers)
        # EDIT/VIEW トグル(排他)
        if self.pushButton_kasugai_layers_edit is not None:
            self.pushButton_kasugai_layers_edit.clicked.connect(
                lambda: self._set_kasugai_layers_mode('edit'))
        if self.pushButton_kasugai_layers_view is not None:
            self.pushButton_kasugai_layers_view.clicked.connect(
                lambda: self._set_kasugai_layers_mode('view'))
        if self.pushButton_kasugai_legend_up is not None:
            self.pushButton_kasugai_legend_up.clicked.connect(
                lambda: self._move_kasugai_legend(-1))
        if self.pushButton_kasugai_legend_down is not None:
            self.pushButton_kasugai_legend_down.clicked.connect(
                lambda: self._move_kasugai_legend(+1))
        if self.checkBox_site_control is not None:
            # custom-layer ON/OFF で site 列の自動値(グレー)が変わる
            self.checkBox_site_control.toggled.connect(
                lambda checked: self._rebuild_kasugai_layers())
        tabw = getattr(self.ui, 'tabWidget_main', None)
        if tabw is not None:
            tabw.currentChanged.connect(
                lambda idx: self._rebuild_kasugai_layers())
        try:
            from qgis.core import QgsProject
            prj = QgsProject.instance()
            for sig in ('layersAdded', 'layersRemoved'):
                try:
                    getattr(prj, sig).connect(self._rebuild_kasugai_layers)
                except Exception:
                    pass
            try:
                prj.layerTreeRoot().nameChanged.connect(
                    lambda *a: self._rebuild_kasugai_layers())
            except Exception:
                pass
        except Exception:  # nosec B110  # 設計上の許容
            pass
        self._rebuild_kasugai_layers()

    # --- 属性フィルタ(Filter タブ) ---------------------------------
    def _init_kasugai_filter_ui(self):
        """Filter タブの初期化。site(グループ)/共通数値属性/演算子/値で
        サイト内の全レイヤへフィルタ(subset string)を一括適用する。"""
        self.comboBox_filter_site = getattr(
            self.ui, 'comboBox_filter_site', None)
        if self.comboBox_filter_site is None:
            return
        self.comboBox_filter_field = getattr(
            self.ui, 'comboBox_filter_field', None)
        self.comboBox_filter_op = getattr(
            self.ui, 'comboBox_filter_op', None)
        self.lineEdit_filter_value = getattr(
            self.ui, 'lineEdit_filter_value', None)
        self.label_filter_status = getattr(
            self.ui, 'label_filter_status', None)
        self.widget_filter_row_num = getattr(
            self.ui, 'widget_filter_row_num', None)
        self.widget_filter_row_str = getattr(
            self.ui, 'widget_filter_row_str', None)
        self.comboBox_filter_op2 = getattr(
            self.ui, 'comboBox_filter_op2', None)
        self.comboBox_filter_value = getattr(
            self.ui, 'comboBox_filter_value', None)
        self.checkBox_filter_multi = getattr(
            self.ui, 'checkBox_filter_multi', None)
        self.widget_filter_row_multi = getattr(
            self.ui, 'widget_filter_row_multi', None)
        self.comboBox_filter_op3 = getattr(
            self.ui, 'comboBox_filter_op3', None)
        self.listWidget_filter_values = getattr(
            self.ui, 'listWidget_filter_values', None)
        if self.comboBox_filter_op is not None:
            self.comboBox_filter_op.addItems(
                ['=', '!=', '<', '<=', '>', '>='])
        if self.comboBox_filter_op2 is not None:
            self.comboBox_filter_op2.addItems(['=', '!='])
        if self.comboBox_filter_op3 is not None:
            self.comboBox_filter_op3.addItems(['IN', 'NOT IN'])
        if self.widget_filter_row_multi is not None:
            self.widget_filter_row_multi.setVisible(False)
        if self.checkBox_filter_multi is not None:
            self.checkBox_filter_multi.toggled.connect(
                lambda _c: self._update_filter_mode())
        self.comboBox_filter_site.currentIndexChanged.connect(
            lambda _i: self._refresh_filter_fields())
        if self.comboBox_filter_field is not None:
            self.comboBox_filter_field.currentIndexChanged.connect(
                lambda _i: self._update_filter_mode())
        ab = getattr(self.ui, 'pushButton_filter_apply', None)
        if ab is not None:
            ab.clicked.connect(self._apply_kasugai_filter)
        cb = getattr(self.ui, 'pushButton_filter_clear', None)
        if cb is not None:
            cb.clicked.connect(self._clear_kasugai_filter)
        # タブを開いたとき最新のサイト一覧に更新
        twm = getattr(self.ui, 'tabWidget_main', None)
        if twm is not None:
            twm.currentChanged.connect(
                lambda _i: self._refresh_filter_sites())
        self._refresh_filter_sites()

    def _site_groups_for_filter(self):
        """site名 → メンバーのベクターレイヤ一覧(「その他」含む)。

        Layers タブの site= 解決規則(customProperty/グループ自動)と
        同一のロジックでグルーピングする。
        """
        try:
            from . import kasugai_export
            bm_names = kasugai_export._basemap_group_names()
            bm_index = kasugai_export._basemap_group_index
            opts_of = kasugai_export._canvas_layer_opts
        except Exception:  # nosec B110  # 設計上の許容
            return {}
        auto_on = bool(self.checkBox_site_control
                       and self.checkBox_site_control.isChecked())
        out = {}
        for layer, groups, _node in self._kasugai_layer_rows():
            try:
                o = opts_of(layer, groups,
                            bm_index(groups, bm_names), auto_on)
            except Exception:  # nosec B110  # 設計上の許容
                continue
            site = o['site'] or 'その他'
            try:
                if layer.fields() is None:
                    continue
            except Exception:  # nosec B110  # 設計上の許容
                continue
            out.setdefault(site, []).append(layer)
        return out

    def _current_filter_layers(self):
        cb = getattr(self, 'comboBox_filter_site', None)
        if cb is None:
            return []
        return self._site_groups_for_filter().get(
            cb.currentText(), [])

    def _refresh_filter_sites(self):
        cb = getattr(self, 'comboBox_filter_site', None)
        if cb is None:
            return
        cur = cb.currentText()
        cb.blockSignals(True)
        cb.clear()
        for site in self._site_groups_for_filter():
            cb.addItem(site)
        cb.blockSignals(False)
        idx = cb.findText(cur)
        cb.setCurrentIndex(idx if idx >= 0 else 0)
        self._refresh_filter_fields()

    def _refresh_filter_fields(self):
        fb = getattr(self, 'comboBox_filter_field', None)
        if fb is None:
            return
        layers = self._current_filter_layers()
        cur = fb.currentText()
        fb.clear()
        # メンバー全レイヤに共通する属性フィールドを列挙
        # (数値フィールドには '(num)' を付記)
        common = None
        numeric = {}
        for layer in layers:
            names = {}
            try:
                for f in layer.fields():
                    try:
                        names[f.name()] = bool(f.isNumeric())
                    except Exception:  # nosec B110  # 設計上の許容
                        names[f.name()] = False
            except Exception:  # nosec B110  # 設計上の許容
                names = {}
            if common is None:
                common = dict(names)
            else:
                for k in list(common):
                    if k not in names:
                        del common[k]
                    else:
                        common[k] = common[k] and names[k]
        common = common or {}
        for name in sorted(common):
            label = '{0} (num)'.format(name) if common[name] else name
            fb.addItem(label, name)
        idx = fb.findData(cur)
        if idx >= 0:
            fb.setCurrentIndex(idx)
        if not common:
            self._update_filter_status('No common field')
        else:
            self._update_filter_status()
        self._update_filter_mode()

    def _filter_field_is_numeric(self):
        """選択フィールドが全メンバーで数値型なら True。"""
        fb = self.comboBox_filter_field
        field = (fb.currentData() or fb.currentText()
                 if fb is not None else '')
        if not field:
            return False
        numeric, found = True, False
        for layer in self._current_filter_layers():
            try:
                idx = layer.fields().indexFromName(field)
            except Exception:  # nosec B110  # 設計上の許容
                idx = -1
            if idx < 0:
                continue
            found = True
            try:
                if not layer.fields().at(idx).isNumeric():
                    numeric = False
            except Exception:  # nosec B110  # 設計上の許容
                numeric = False
        return found and numeric

    def _update_filter_mode(self):
        """フィールド型と複数選択で入力行を切替。

        - 数値・単一 → 演算子(= != < <= > >=) + 数値入力
        - その他・単一 → = / != + メンバーの既存値ドロップダウン
        - 複数選択 → IN / NOT IN + 既存値チェックリスト(数値も可)
        """
        num_w = getattr(self, 'widget_filter_row_num', None)
        str_w = getattr(self, 'widget_filter_row_str', None)
        mw = getattr(self, 'widget_filter_row_multi', None)
        if num_w is None or str_w is None:
            return
        numeric = self._filter_field_is_numeric()
        multi = bool(self.checkBox_filter_multi
                     and self.checkBox_filter_multi.isChecked())
        num_w.setVisible(numeric and not multi)
        str_w.setVisible((not numeric) and not multi)
        if mw is not None:
            mw.setVisible(multi)
        if numeric and not multi:
            return
        # 既存値をメンバー全レイヤから列挙(ドロップダウン/リスト共用)
        vb = getattr(self, 'comboBox_filter_value', None)
        if vb is None:
            return
        fb = self.comboBox_filter_field
        field = (fb.currentData() or fb.currentText()
                 if fb is not None else '')
        values = set()
        layers = self._current_filter_layers()
        # 適用中フィルタが値の列挙まで絞ってしまうため一時解除
        saved = []
        for layer in layers:
            try:
                saved.append((layer, layer.subsetString() or ''))
                layer.setSubsetString('')
            except Exception:  # nosec B110  # 設計上の許容
                pass
        try:
            for layer in layers:
                try:
                    for ft in layer.getFeatures():
                        v = ft.attribute(field)
                        if v is not None:
                            values.add(str(v))
                        if len(values) > 100:
                            break
                except Exception:  # nosec B110  # 設計上の許容
                    pass
                if len(values) > 100:
                    break
        finally:
            for layer, sub in saved:
                try:
                    layer.setSubsetString(sub)
                except Exception:  # nosec B110  # 設計上の許容
                    pass
        cur = vb.currentText()
        vb.blockSignals(True)
        vb.clear()
        vb.addItems(sorted(values)[:100])
        vb.blockSignals(False)
        idx = vb.findText(cur)
        if idx >= 0:
            vb.setCurrentIndex(idx)
        # 複数選択モード: チェックリストに同じ既存値を列挙
        lw = getattr(self, 'listWidget_filter_values', None)
        if lw is not None:
            from qgis.PyQt.QtWidgets import QListWidgetItem
            checked = set()
            for i in range(lw.count()):
                it = lw.item(i)
                if it is not None and it.checkState() == \
                        Qt.CheckState.Checked:
                    checked.add(it.text())
            lw.blockSignals(True)
            lw.clear()
            for v in sorted(values)[:100]:
                it = QListWidgetItem(v)
                it.setFlags(
                    it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                it.setCheckState(
                    Qt.CheckState.Checked if v in checked
                    else Qt.CheckState.Unchecked)
                lw.addItem(it)
            lw.blockSignals(False)

    def _update_filter_status(self, msg=None):
        lb = getattr(self, 'label_filter_status', None)
        if lb is None:
            return
        if msg is not None:
            lb.setText(msg)
            return
        # メンバーの先頭レイヤのフィルタを表示(全レイヤ共通の前提)
        layers = self._current_filter_layers()
        sub = ''
        if layers:
            try:
                sub = layers[0].subsetString() or ''
            except Exception:  # nosec B110  # 設計上の許容
                pass
        lb.setText(sub)

    def _apply_kasugai_filter(self):
        layers = self._current_filter_layers()
        fb = self.comboBox_filter_field
        field = (fb.currentData() or fb.currentText()
                 if fb is not None else '')
        op = (self.comboBox_filter_op.currentText()
              if self.comboBox_filter_op is not None else '=')
        if not layers or not field:
            self._update_filter_status('Select a site and field')
            return
        numeric = self._filter_field_is_numeric()
        multi = bool(self.checkBox_filter_multi
                     and self.checkBox_filter_multi.isChecked())
        lw = getattr(self, 'listWidget_filter_values', None)
        if multi and lw is not None:
            sel = []
            for i in range(lw.count()):
                it = lw.item(i)
                if it is not None and it.checkState() == \
                        Qt.CheckState.Checked:
                    sel.append(it.text())
            if not sel:
                self._update_filter_status('Select values')
                return
            op3 = (self.comboBox_filter_op3.currentText()
                   if self.comboBox_filter_op3 is not None
                   else 'IN')
            if numeric:
                vals = ','.join(sel)
            else:
                vals = ','.join(
                    "'{0}'".format(v.replace("'", "''"))
                    for v in sel)
            expr = '"{0}" {1} ({2})'.format(
                field.replace('"', '""'), op3, vals)
        elif numeric:
            txt = (self.lineEdit_filter_value.text().strip()
                   if self.lineEdit_filter_value is not None else '')
            try:
                num = float(txt)
            except (TypeError, ValueError):
                self._update_filter_status('Enter a number')
                return
            num_s = str(int(num)) if num == int(num) else str(num)
            expr = '"{0}" {1} {2}'.format(field.replace('"', '""'),
                                          op, num_s)
        else:
            op2 = (self.comboBox_filter_op2.currentText()
                   if self.comboBox_filter_op2 is not None
                   else '=')
            txt = (self.comboBox_filter_value.currentText().strip()
                   if self.comboBox_filter_value is not None else '')
            if txt == '':
                self._update_filter_status('Select a value')
                return
            expr = '"{0}" {1} \'{2}\''.format(
                field.replace('"', '""'), op2,
                txt.replace("'", "''"))
        n = 0
        for layer in layers:
            try:
                if layer.setSubsetString(expr):
                    n += 1
                layer.triggerRepaint()
            except Exception:  # nosec B110  # 設計上の許容
                pass
        self._update_filter_status(
            '{0} ({1} layers)'.format(expr, n) if n
            else 'Filter failed')

    def _clear_kasugai_filter(self):
        for layer in self._current_filter_layers():
            try:
                layer.setSubsetString('')
                layer.triggerRepaint()
            except Exception:  # nosec B110  # 設計上の許容
                pass
        self._update_filter_status('')

    def _set_kasugai_layers_mode(self, mode):
        """EDIT(編集テーブル)/VIEW(出力結果表示)を切り替える。"""
        self._kasugai_layers_mode = mode
        if self.pushButton_kasugai_layers_edit is not None:
            self.pushButton_kasugai_layers_edit.blockSignals(True)
            self.pushButton_kasugai_layers_edit.setChecked(mode == 'edit')
            self.pushButton_kasugai_layers_edit.blockSignals(False)
        if self.pushButton_kasugai_layers_view is not None:
            self.pushButton_kasugai_layers_view.blockSignals(True)
            self.pushButton_kasugai_layers_view.setChecked(mode == 'view')
            self.pushButton_kasugai_layers_view.blockSignals(False)
        self._rebuild_kasugai_layers()

    def _kasugai_layer_rows(self):
        """(layer, groups, node) のツリー順リスト。グループ自体は行にしない。"""
        from qgis.core import QgsProject, QgsLayerTreeLayer
        rows = []

        def _walk(node, groups):
            for ch in node.children():
                if isinstance(ch, QgsLayerTreeLayer):
                    lyr = ch.layer()
                    if lyr is not None:
                        rows.append((lyr, list(groups), ch))
                else:
                    _walk(ch, groups + [ch.name()])
        _walk(QgsProject.instance().layerTreeRoot(), [])
        return rows

    def _rebuild_kasugai_layers(self, *args):
        """Layers タブの行を現在のレイヤツリーで再構築する。"""
        tw = self.treeWidget_kasugai_layers
        if tw is None:
            return
        from qgis.PyQt.QtWidgets import QTreeWidgetItem
        from qgis.PyQt.QtGui import QBrush, QColor
        try:
            from . import kasugai_export
            bm_names = kasugai_export._basemap_group_names()
            bm_index = kasugai_export._basemap_group_index
        except Exception:  # nosec B110  # 設計上の許容
            bm_names, bm_index = (), lambda g, n=None: None
        auto_on = bool(self.checkBox_site_control
                       and self.checkBox_site_control.isChecked())
        if self._kasugai_layers_mode == 'view':
            self._rebuild_kasugai_layers_view(
                tw, bm_names, bm_index, auto_on)
            return
        tw.setColumnCount(4)
        tw.setHeaderLabels(['Layer', 'site', 'list', 'opts'])
        gray = QBrush(QColor(140, 140, 140))
        tw.blockSignals(True)
        try:
            tw.clear()
            for layer, groups, _node in self._kasugai_layer_rows():
                name = '/'.join(groups + [layer.name()])
                it = QTreeWidgetItem([name, '', '', ''])
                it.setData(0, Qt.ItemDataRole.UserRole, layer.id())
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsEditable |
                            Qt.ItemFlag.ItemIsUserCheckable)
                # 凡例: 行アイコン + 分類凡例は子行(▲▼ボタンで並替)
                litems = self._kasugai_legend_items(
                    layer, self._opts_tokens(layer))
                if litems:
                    it.setIcon(0, self._kasugai_legend_icon(litems[0]))
                if len(litems) > 1:
                    for li in litems:
                        c = QTreeWidgetItem([li.label(), '', '', ''])
                        c.setData(0, Qt.ItemDataRole.UserRole, 'legend')
                        c.setIcon(0, self._kasugai_legend_icon(li))
                        it.addChild(c)
                    it.setExpanded(True)
                # 個別指定 > 自動(custom-layer ON のときグループパス)
                site = layer.customProperty('kasugai_site', None)
                auto = '' if bm_index(groups, bm_names) is not None \
                    else '/'.join(groups)
                if site is None:
                    if auto_on and auto:
                        it.setText(1, auto)
                        it.setForeground(1, gray)
                        it.setToolTip(1, 'auto: {0}'.format(auto))
                else:
                    it.setText(1, site)
                it.setCheckState(
                    2, Qt.CheckState.Checked
                    if str(layer.customProperty(
                        'kasugai_list', '') or '').strip() == 'off'
                    else Qt.CheckState.Unchecked)
                opts = layer.customProperty('kasugai_opts', None)
                if opts:
                    it.setText(3, str(opts))
                it.setToolTip(3, 'key=value key=value ...')
                tw.addTopLevelItem(it)
            tw.resizeColumnToContents(0)
        finally:
            tw.blockSignals(False)

    def _rebuild_kasugai_layers_view(self, tw, bm_names, bm_index,
                                     auto_on):
        """VIEW モード: Canvas で実際に見えるパネル構成を再現する
        (編集不可)。custom-layer プラグインと同じ規則:

        - 「レイヤタブ (custom-layer)」(site= が1件以上あるときのみ出る):
          site ごとのグループ(.kasc 初出順)+メンバー(order= 昇順、
          無指定は末尾)。site 無しレイヤは末尾「その他」に集約
        """
        from qgis.PyQt.QtWidgets import QTreeWidgetItem
        try:
            from . import kasugai_export
            opts_of = kasugai_export._canvas_layer_opts
        except Exception:  # nosec B110  # 設計上の許容
            opts_of = None

        def _opts(layer, groups):
            if opts_of is None:
                return {'site': None, 'order': None, 'list': None,
                        'opts': []}
            try:
                return opts_of(layer, groups,
                               bm_index(groups, bm_names), auto_on)
            except Exception:  # nosec B110  # 設計上の許容
                return {'site': None, 'order': None, 'list': None,
                        'opts': []}

        tw.blockSignals(True)
        try:
            tw.setColumnCount(2)
            tw.setHeaderLabels(['Canvas', ''])
            tw.clear()
            sites, misc = {}, []
            for layer, groups, node in self._kasugai_layer_rows():
                vis = True
                try:
                    vis = bool(node.itemVisibilityChecked())
                except Exception:  # nosec B110  # 設計上の許容
                    pass
                o = _opts(layer, groups)
                if o['list'] == 'off':
                    # list=off は Canvas の一覧に出ないので
                    # VIEW にも出さない
                    continue
                name = '/'.join(groups + [layer.name()])
                label = name
                note = ('order={0}'.format(o['order'])
                        if o['order'] else '')
                if o['site']:
                    sites.setdefault(o['site'], []).append(
                        (o, layer, label, note, vis))
                else:
                    misc.append((o, layer, label, note, vis))
            if sites:
                root_sc = QTreeWidgetItem(['レイヤタブ (custom-layer)',
                                           'before=layers-panel'])
                root_sc.setFlags(root_sc.flags()
                                 & ~Qt.ItemFlag.ItemIsEditable)
                tw.addTopLevelItem(root_sc)

                def _member_key(m):
                    try:
                        return (0, float(m[0]['order']))
                    except (TypeError, ValueError):
                        return (1, 0)

                def _attach_legend(it, layer, o):
                    items = self._kasugai_legend_items(
                        layer, o.get('opts', []))
                    try:
                        if len(items) == 1:
                            # 単一シンボルは行アイコン(Canvas の行内
                            # スウォッチ相当)
                            it.setIcon(
                                0, self._kasugai_legend_icon(items[0]))
                        elif len(items) > 1:
                            for li in items:
                                c = QTreeWidgetItem([li.label(), ''])
                                c.setFlags(
                                    c.flags()
                                    & ~Qt.ItemFlag.ItemIsEditable)
                                c.setData(
                                    0, Qt.ItemDataRole.UserRole,
                                    'legend')
                                c.setIcon(
                                    0, self._kasugai_legend_icon(li))
                                it.addChild(c)
                    except Exception:  # nosec B110  # 設計上の許容
                        pass

                def _member_item(o, layer, label, note, vis):
                    it = QTreeWidgetItem([label, note])
                    it.setFlags((it.flags()
                                 & ~Qt.ItemFlag.ItemIsEditable)
                                | Qt.ItemFlag.ItemIsUserCheckable)
                    it.setCheckState(
                        0, Qt.CheckState.Checked if vis
                        else Qt.CheckState.Unchecked)
                    it.setData(
                        0, Qt.ItemDataRole.UserRole, layer.id())
                    _attach_legend(it, layer, o)
                    return it

                def _sync_group_check(g):
                    n = g.childCount()
                    on = sum(
                        g.child(i).checkState(0)
                        == Qt.CheckState.Checked
                        for i in range(n))
                    st = (Qt.CheckState.Checked if on == n
                          else Qt.CheckState.Unchecked if on == 0
                          else Qt.CheckState.PartiallyChecked)
                    tw.blockSignals(True)
                    g.setCheckState(0, st)
                    tw.blockSignals(False)

                for sname, members in sites.items():
                    g = QTreeWidgetItem(
                        [sname, '{0}'.format(len(members))])
                    g.setFlags((g.flags()
                                & ~Qt.ItemFlag.ItemIsEditable)
                               | Qt.ItemFlag.ItemIsUserCheckable)
                    root_sc.addChild(g)
                    for o, layer, label, note, vis in sorted(
                            members, key=_member_key):
                        g.addChild(_member_item(
                            o, layer, label, note, vis))
                    _sync_group_check(g)
                if misc:
                    g = QTreeWidgetItem(['その他',
                                         '{0}'.format(len(misc))])
                    g.setFlags((g.flags()
                                & ~Qt.ItemFlag.ItemIsEditable)
                               | Qt.ItemFlag.ItemIsUserCheckable)
                    root_sc.addChild(g)
                    for o, layer, label, note, vis in misc:
                        g.addChild(_member_item(
                            o, layer, label, note, vis))
                    _sync_group_check(g)
            tw.expandAll()
            tw.resizeColumnToContents(0)
        finally:
            tw.blockSignals(False)

    def _opts_tokens(self, layer):
        """レイヤの kasugai_opts を key=value トークン列で返す。"""
        try:
            extra = layer.customProperty('kasugai_opts', None)
        except Exception:  # nosec B110  # 設計上の許容
            return []
        return [t for t in str(extra or '').replace('|', ' ').split()
                if t]

    def _kasugai_legend_items(self, layer, opts_tokens):
        """凡例項目を Canvas の順序(レンダラのシンボル順)で返す。

        ``legend_order=asc|desc|reverse|ラベル列挙`` トークンを適用する。
        """
        try:
            r = layer.renderer()
            items = (list(r.legendSymbolItems())
                     if r is not None else [])
        except Exception:  # nosec B110  # 設計上の許容
            return []
        spec = ''
        for tok in opts_tokens or []:
            if str(tok).startswith('legend_order='):
                spec = str(tok).split('=', 1)[1].strip()
        if not spec or len(items) < 2:
            return items
        if spec == 'reverse':
            return list(reversed(items))
        if spec == 'asc':
            return sorted(items, key=lambda i: i.label())
        if spec == 'desc':
            return sorted(items, key=lambda i: i.label(), reverse=True)
        pos = {t.strip(): i for i, t in enumerate(spec.split(','))}
        return sorted(items, key=lambda i: pos.get(i.label(), 1e9))

    def _kasugai_legend_icon(self, li):
        """QgsLegendSymbolItem の QIcon(シンボルスウォッチ)を返す。"""
        try:
            from qgis.core import QgsSymbolLayerUtils
            s = li.symbol()
            if s is None:
                return QIcon()
            return QgsSymbolLayerUtils.symbolPreviewIcon(
                s, QSize(16, 16))
        except Exception:  # nosec B110  # 設計上の許容
            return QIcon()

    def _move_kasugai_legend(self, delta):
        """▲▼ の移動処理(VIEW モードのみ)。

        - グループ直下のメンバー行 → グループ内で移動し、メンバーへ
          表順の order=1..N を振り直す(カスタムタブの凡例順に反映)
        - メンバー直下の凡例項目行 → 移動し legend_order= を
          kasugai_opts へ保存
        """
        tw = self.treeWidget_kasugai_layers
        if tw is None or self._kasugai_layers_mode != 'view':
            return
        it = tw.currentItem()
        if it is None or it.parent() is None:
            return
        if it.data(0, Qt.ItemDataRole.UserRole) == 'legend':
            self._move_kasugai_legend_row(tw, it, delta)
        elif it.parent().parent() is not None:
            self._move_kasugai_member_row(tw, it, delta)

    def _move_kasugai_legend_row(self, tw, it, delta):
        """凡例の項目行を動かし legend_order= を保存する。"""
        parent = it.parent()
        lid = parent.data(0, Qt.ItemDataRole.UserRole)
        idx = parent.indexOfChild(it)
        ni = idx + delta
        if ni < 0 or ni >= parent.childCount():
            return
        from qgis.core import QgsProject
        layer = QgsProject.instance().mapLayer(lid)
        if layer is None:
            return
        tw.blockSignals(True)
        try:
            parent.takeChild(idx)
            parent.insertChild(ni, it)
            tw.setCurrentItem(it)
        finally:
            tw.blockSignals(False)
        labels = [parent.child(i).text(0)
                  for i in range(parent.childCount())]
        toks = [t for t in self._opts_tokens(layer)
                if not t.startswith('legend_order=')]
        toks.append('legend_order={0}'.format(','.join(labels)))
        layer.setCustomProperty('kasugai_opts', ' '.join(toks))

    def _move_kasugai_member_row(self, tw, it, delta):
        """グループ内のメンバー行を動かし、メンバーへ表順の
        order=1..N を振り直す(カスタムタブの凡例順に反映)。"""
        grp = it.parent()
        if grp.text(0) == 'その他':
            # misc は order= を持たず .kasc 順なので動かさない
            return
        idx = grp.indexOfChild(it)
        ni = idx + delta
        if ni < 0 or ni >= grp.childCount():
            return
        tw.blockSignals(True)
        try:
            grp.takeChild(idx)
            grp.insertChild(ni, it)
            tw.setCurrentItem(it)
            for pos in range(grp.childCount()):
                grp.child(pos).setText(1, 'order={0}'.format(pos + 1))
        finally:
            tw.blockSignals(False)
        from qgis.core import QgsProject
        prj = QgsProject.instance()
        for pos in range(grp.childCount()):
            lid = grp.child(pos).data(0, Qt.ItemDataRole.UserRole)
            layer = prj.mapLayer(lid)
            if layer is not None:
                layer.setCustomProperty('kasugai_order', str(pos + 1))

    def _on_kasugai_view_item_checked(self, item):
        """VIEW のチェックボックス → レイヤツリーの表示/非表示に反映。

        メンバー行は個別に、グループ行はメンバー一括で
        ``itemVisibilityChecked`` を切り替える(非表示は
        Canvas 同様に未チェック行として残る)。
        """
        from qgis.core import QgsProject
        tw = self.treeWidget_kasugai_layers
        checked = item.checkState(0) == Qt.CheckState.Checked
        if item.parent() is None:
            return
        if item.parent().parent() is None:
            # グループ行 → メンバー一括
            tw.blockSignals(True)
            try:
                for i in range(item.childCount()):
                    m = item.child(i)
                    if m.data(0, Qt.ItemDataRole.UserRole) in (None,
                                                             'legend'):
                        continue
                    m.setCheckState(
                        0, Qt.CheckState.Checked if checked
                        else Qt.CheckState.Unchecked)
            finally:
                tw.blockSignals(False)
            root = QgsProject.instance().layerTreeRoot()
            for i in range(item.childCount()):
                lid = item.child(i).data(
                    0, Qt.ItemDataRole.UserRole)
                node = root.findLayer(lid)
                if node is not None:
                    node.setItemVisibilityChecked(checked)
            return
        if item.data(0, Qt.ItemDataRole.UserRole) in (None, 'legend'):
            return
        # メンバー行 → グループ状態の更新 + 個別切替
        # (ノード切替が rebuild シグナルを発火し得るため先に更新)
        g = item.parent()
        n = g.childCount()
        on = sum(g.child(i).checkState(0) == Qt.CheckState.Checked
                 for i in range(n))
        st = (Qt.CheckState.Checked if on == n
              else Qt.CheckState.Unchecked if on == 0
              else Qt.CheckState.PartiallyChecked)
        tw.blockSignals(True)
        g.setCheckState(0, st)
        tw.blockSignals(False)
        node = QgsProject.instance().layerTreeRoot().findLayer(
            item.data(0, Qt.ItemDataRole.UserRole))
        if node is not None:
            node.setItemVisibilityChecked(checked)

    def _on_kasugai_layer_item_changed(self, item, col):
        """セル編集をレイヤ customProperty へ反映する。"""
        if self.treeWidget_kasugai_layers is None:
            return
        if col == 0:
            if self._kasugai_layers_mode == 'view':
                self._on_kasugai_view_item_checked(item)
            return
        from qgis.core import QgsProject
        lid = item.data(0, Qt.ItemDataRole.UserRole)
        layer = QgsProject.instance().mapLayer(lid)
        if layer is None:
            return
        if col == 1:
            key, val = 'kasugai_site', item.text(1).strip()
        elif col == 2:
            key = 'kasugai_list'
            val = 'off' if item.checkState(2) == Qt.CheckState.Checked \
                else ''
        elif col == 3:
            key, val = 'kasugai_opts', item.text(3).strip()
        else:
            return
        if val == '':
            layer.removeCustomProperty(key)
        else:
            layer.setCustomProperty(key, val)
        # site 列を空にした場合は自動値(グレー)表示へ戻す
        if col == 1 and val == '':
            self._rebuild_kasugai_layers()

    def update_canvas_launch_state(self):
        """KASUGAI Canvas のインストール状態を「▶ Canvas」ボタンに、
        稼働状態を「Admin」ボタンに反映する。

        インストール先が検出できない(設定未登録かつインストーラ登録なし)
        場合はボタンを「Install KASUGAI Canvas」表示に変え、クリックで
        インストール導線(セットアップ/ポータブルZIP選択)へ進む。
        「▶ Canvas」は 8510 未稼働でもインストール済み exe を
        自動起動できるため稼働状態では無効化しない。
        「Admin」は稼働中アプリの /admin/ を開くだけなので、
        未稼働時はグレーアウトする。
        検出自体が失敗した場合は従来どおり通常表示のままにする。
        """
        btn = getattr(self.ui, 'pushButton_kasugai_launch', None)
        try:
            from . import kasugai_export
            installed = bool(kasugai_export.detect_kasugai_install_dir())
        except Exception:  # nosec B110  # 設計上の許容
            installed = True
        if btn is not None:
            btn.setEnabled(True)
            if installed:
                btn.setText(QCoreApplication.translate('geo_webview', "▶ Canvas"))
                btn.setToolTip(QCoreApplication.translate(
                    'geo_webview',
                    "Open the exported project in KASUGAI Canvas (main integrated player) — registers the existing .kasc with a running Canvas (port 8510) and switches to it. Requires a prior export (Export button)"))
            else:
                btn.setText(QCoreApplication.translate(
                    'geo_webview', "Install KASUGAI Canvas"))
                btn.setToolTip(QCoreApplication.translate(
                    'geo_webview',
                    "KASUGAI Canvas is not installed — click to install (setup with .kasc file association or portable ZIP), then open the project"))

        # 「Admin」は稼働中の Canvas アプリ(8510)が必須。未稼働なら無効化。
        # 稼働検出は /api/capabilities への短い HTTP 呼出しのみ。
        admin = getattr(self.ui, 'pushButton_kasugai_admin', None)
        if admin is not None:
            try:
                caps = kasugai_export.detect_kasugai()
            except Exception:  # nosec B110  # 設計上の許容
                caps = True
            admin.setEnabled(bool(caps))

    def set_kasugai_outdir(self, path):
        """保存先表示ボタンの内容を更新する。path はフルパス。"""
        self._kasugai_outdir_path = path or ''
        self._refresh_kasugai_outdir()

    def _refresh_kasugai_outdir(self):
        """保存先ボタンの表示を中央省略パス+フルパスツールチップにする。"""
        btn = getattr(self, 'pushButton_kasugai_outdir', None)
        if btn is None:
            return
        path = self._kasugai_outdir_path or ''
        try:
            fm = btn.fontMetrics()
            w = btn.width() if btn.width() > 40 else 200
            elide = getattr(getattr(Qt, 'TextElideMode', Qt), 'ElideMiddle')
            btn.setText(fm.elidedText(path or '—', elide, w - 12))
        except Exception:  # nosec B110  # 設計上の許容
            btn.setText(path or '—')
        btn.setToolTip(
            QCoreApplication.translate(
                'geo_webview',
                "Export destination folder — click to choose a different folder")
            + "\n" + path)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_kasugai_outdir()

    def update_server_status(self, port, running, network_url=None):
        """サーバーステータスを更新

        Args:
            port: サーバーポート番号
            running: サーバーが実行中かどうか
            network_url: LAN内の他マシンからアクセス可能なURL(あれば併記)
        """
        if running:
            status_text = QCoreApplication.translate('geo_webview', "HTTP Server: Running on http://localhost:{0}").format(port)
            if network_url:
                status_text += f" / {network_url}"
            style = "color: green; font-weight: bold;"
        else:
            status_text = QCoreApplication.translate('geo_webview', "HTTP Server: Stopped")
            style = "color: red; font-weight: bold;"

        self.label_server_status.setText(status_text)
        self.label_server_status.setStyleSheet(style)

        # Update spinBox_port to reflect current port
        try:
            if self.spinBox_port is not None:
                self.spinBox_port.blockSignals(True)
                self.spinBox_port.setValue(int(port))
                self.spinBox_port.blockSignals(False)
        except Exception:  # nosec B110  # 設計上の許容
            pass

        # Keep checkbox in sync if present
        try:
            if self.checkBox_server_toggle is not None:
                # block signals to avoid recursive calls
                self.checkBox_server_toggle.blockSignals(True)
                self.checkBox_server_toggle.setChecked(bool(running))
                self.checkBox_server_toggle.blockSignals(False)
        except Exception:  # nosec B110  # 設計上の許容
            pass
        # keep external control checkbox untouched here (no server relation)
        try:
            if self.checkBox_external_control is not None:
                # ensure it's boolean
                self.checkBox_external_control.blockSignals(True)
                self.checkBox_external_control.setChecked(bool(getattr(self.checkBox_external_control, 'isChecked', lambda: False)()))
                self.checkBox_external_control.blockSignals(False)
        except Exception:  # nosec B110  # 設計上の許容
            pass

    def _build_sharing_group(self):
        """共有/プレゼンテーション関連のウィジェットを動的に追加する。

        .ui ファイルを変更せず、メインの verticalLayout 末尾に
        groupBox を追加する。利用不可能な環境では何もしない。
        """
        from qgis.PyQt.QtWidgets import (
            QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton,
            QComboBox, QCheckBox, QLineEdit)
        tr = QCoreApplication.translate
        group = QGroupBox(tr('geo_webview', 'Sharing / Presentation'))
        vbox = QVBoxLayout(group)

        row1 = QHBoxLayout()
        self.pushButton_present = QPushButton(
            tr('geo_webview', 'Presentation Share'))
        self.pushButton_present.setToolTip(tr(
            'geo_webview',
            'Open a page that mirrors the QGIS canvas for window sharing'))
        row1.addWidget(self.pushButton_present)
        vbox.addLayout(row1)

        self.comboBox_received = QComboBox()
        self.comboBox_received.setToolTip(tr(
            'geo_webview',
            'Permalinks received from clients (latest 10). '
            'Selecting an entry copies it into the navigate field.'))
        vbox.addWidget(self.comboBox_received)

        self.checkBox_mac_auth = QCheckBox(
            tr('geo_webview', 'MAC address authentication'))
        self.checkBox_mac_auth.setToolTip(tr(
            'geo_webview',
            'When enabled, only registered client MAC addresses may access '
            'the HTTP server.'))
        vbox.addWidget(self.checkBox_mac_auth)
        self.lineEdit_mac_auth = QLineEdit()
        self.lineEdit_mac_auth.setPlaceholderText(tr(
            'geo_webview',
            'Allowed MAC addresses (comma separated). Empty = deny all'))
        vbox.addWidget(self.lineEdit_mac_auth)

        self.groupBox_sharing = group
        try:
            # タブ化されている場合は Share タブ内へ、無ければメインレイアウト末尾へ
            _tab = getattr(self.ui, 'tab_share', None)
            layout = (_tab.layout() if _tab is not None
                      else self.widget.layout())
            if layout is not None:
                layout.addWidget(group)
        except Exception:  # nosec B110  # 設計上の許容
            pass

    def update_received_history(self, entries):
        """受領パーマリンク履歴コンボを更新する(選択状態を維持)。"""
        combo = self.comboBox_received
        if combo is None:
            return
        try:
            current_url = None
            if combo.count() > 0 and combo.currentIndex() >= 0:
                current_url = combo.itemData(combo.currentIndex())
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(
                QCoreApplication.translate(
                    'geo_webview', '-- received permalinks --'), None)
            for ent in entries or []:
                url = ent.get('url') or ''
                label = '{0} {1} {2}'.format(
                    ent.get('time', ''), ent.get('client', ''),
                    ent.get('ua', '') or url[:60])
                combo.addItem(label, url)
            if current_url:
                idx = combo.findData(current_url)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
                else:
                    combo.setCurrentIndex(0)
            else:
                combo.setCurrentIndex(0)
        except Exception:  # nosec B110  # 設計上の許容
            pass
        finally:
            try:
                combo.blockSignals(False)
            except Exception:  # nosec B110  # 設計上の許容
                pass

    def set_server_toggle_handler(self, handler):
        """外部からトグルのハンドラを設定する

        handler: function(checked: bool) -> None
        """
        if self.checkBox_server_toggle is None:
            return
        try:
            # connect stateChanged -> handler
            self.checkBox_server_toggle.stateChanged.connect(lambda state: handler(bool(state)))
        except Exception:  # nosec B110  # 設計上の許容
            pass

    def set_external_control_handler(self, handler):
        """外部制御トグルのハンドラを設定する

        handler: function(checked: bool) -> None
        """
        if self.checkBox_external_control is None:
            return
        try:
            self.checkBox_external_control.stateChanged.connect(lambda state: handler(bool(state)))
        except Exception:  # nosec B110  # 設計上の許容
            pass

    def set_port_change_handler(self, handler):
        """ポート番号変更のハンドラを設定する

        handler: function(port: int) -> None
        """
        if self.spinBox_port is None:
            return
        try:
            self.spinBox_port.valueChanged.connect(lambda value: handler(int(value)))
        except Exception:  # nosec B110  # 設計上の許容
            pass

    # --- Clipboard handlers ---
    def _on_copy_permalink_to_clipboard(self):
        """lineEdit_permalink の内容をシステムクリップボードにコピーする"""
        try:
            text = ''
            if hasattr(self, 'lineEdit_permalink') and self.lineEdit_permalink is not None:
                text = self.lineEdit_permalink.text() or ''
            QGuiApplication.clipboard().setText(text)
        except Exception:  # nosec B110  # 設計上の許容
            pass

    def _on_paste_from_clipboard(self):
        """クリップボードからテキストを取得して lineEdit_navigate に貼り付ける"""
        try:
            cb = QGuiApplication.clipboard()
            text = cb.text() if cb is not None else ''
            if hasattr(self, 'lineEdit_navigate') and self.lineEdit_navigate is not None:
                self.lineEdit_navigate.setText(text)
        except Exception:  # nosec B110  # 設計上の許容
            pass
