from qgis.PyQt import QtWidgets, QtCore
import os
import tempfile

from qgis.PyQt.QtGui import QIcon


class SettingsDialog(QtWidgets.QDialog):
    """Settings dialog for KASUGAI Canvas integration configuration"""

    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setWindowTitle(QtCore.QCoreApplication.translate('geo_webview', "Settings"))
        self.setMinimumWidth(600)
        try:
            icon_path = os.path.join(os.path.dirname(__file__), 'icon', 'setting.png')
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception:  # nosec B110  # 設計上の許容
            pass

        # Initialize QSettings for persistent storage
        self.settings = QtCore.QSettings('GeoWebView', 'geo_webview')

        # Main layout
        layout = QtWidgets.QVBoxLayout()

        # Title
        title = QtWidgets.QLabel(QtCore.QCoreApplication.translate('geo_webview', "KASUGAI Canvas"))
        title.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(title)

        # KASUGAI Canvas install location (serverless export target)
        kasugai_group = QtWidgets.QGroupBox(QtCore.QCoreApplication.translate('geo_webview', "KASUGAI Canvas Install Location"))
        kasugai_layout = QtWidgets.QVBoxLayout()

        kasugai_path_layout = QtWidgets.QHBoxLayout()
        kasugai_path_label = QtWidgets.QLabel(QtCore.QCoreApplication.translate('geo_webview', "Install Path:"))
        self.kasugai_install_input = QtWidgets.QLineEdit()
        self.kasugai_install_input.setReadOnly(True)
        kasugai_path_layout.addWidget(kasugai_path_label)
        kasugai_path_layout.addWidget(self.kasugai_install_input)
        kasugai_layout.addLayout(kasugai_path_layout)

        kasugai_button_layout = QtWidgets.QHBoxLayout()
        btn_kasugai_browse = QtWidgets.QPushButton(QtCore.QCoreApplication.translate('geo_webview', "Browse..."))
        btn_kasugai_browse.clicked.connect(self._browse_kasugai_install)
        kasugai_button_layout.addWidget(btn_kasugai_browse)

        btn_kasugai_clear = QtWidgets.QPushButton(QtCore.QCoreApplication.translate('geo_webview', "Clear"))
        btn_kasugai_clear.setToolTip(QtCore.QCoreApplication.translate('geo_webview', "Export to the standalone output directory instead"))
        btn_kasugai_clear.clicked.connect(self._clear_kasugai_install)
        kasugai_button_layout.addWidget(btn_kasugai_clear)
        kasugai_button_layout.addStretch()
        kasugai_layout.addLayout(kasugai_button_layout)

        kasugai_info = QtWidgets.QLabel(
            QtCore.QCoreApplication.translate('geo_webview',
                                              "When set, KASUGAI export writes .kasc+DATA/ directly into "
                                              "<install>/projects/<project>/ so it appears in the Canvas project list.")
        )
        kasugai_info.setWordWrap(True)
        kasugai_info.setStyleSheet("color: #666;")
        kasugai_layout.addWidget(kasugai_info)

        kasugai_group.setLayout(kasugai_layout)
        layout.addWidget(kasugai_group)

        layout.addStretch()

        # Close button
        btn_close = QtWidgets.QPushButton(QtCore.QCoreApplication.translate('geo_webview', "Close"))
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

        self.setLayout(layout)

        # Load saved settings
        self._load_settings()

    def showEvent(self, event):
        """Refresh settings when dialog is shown to reflect latest values"""
        super().showEvent(event)
        self._load_settings()

    def _load_settings(self):
        """Load saved settings from QSettings and display them dynamically"""
        # KASUGAI Canvas install location
        install_path = self.settings.value('kasugai_install_path', '') or ''
        install_path = str(install_path).strip()
        if install_path and install_path != '__default__' and os.path.isdir(install_path):
            self.kasugai_install_input.setText(install_path)
            self._kasugai_install_path = install_path
        else:
            self.kasugai_install_input.setText(
                QtCore.QCoreApplication.translate('geo_webview', "[Not set] export to output directory"))
            self._kasugai_install_path = ''
            if install_path and install_path != '__default__':
                self.settings.setValue('kasugai_install_path', '')

    def _browse_kasugai_install(self):
        """Select KASUGAI Canvas install directory; export lands in <dir>/projects/."""
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            QtCore.QCoreApplication.translate('geo_webview', "Select KASUGAI Canvas Install Directory"),
            self._kasugai_install_path or tempfile.gettempdir()
        )
        if folder:
            self.kasugai_install_input.setText(folder)
            self._kasugai_install_path = folder
            self.settings.setValue('kasugai_install_path', folder)

    def _clear_kasugai_install(self):
        """Unset install dir: fall back to the standalone output directory."""
        self.kasugai_install_input.setText(
            QtCore.QCoreApplication.translate('geo_webview', "[Not set] export to output directory"))
        self._kasugai_install_path = ''
        self.settings.setValue('kasugai_install_path', '')
