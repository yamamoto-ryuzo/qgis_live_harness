# -*- coding: utf-8 -*-
"""geo_driver メニュー所有トークンの回帰テスト。

reloadPlugin(ホットリロード)では旧インスタンスの遅延 _menu_cleanup が
新インスタンスの initGui によるアクション追加「後」に実行される。
旧実装は「現行自身のアクションを参照一致で除外」するだけだったため、
unloadで参照がNoneになった旧インスタンスのsweepが新世代のアクションを
全て除去+deleteLaterし、サブメニューが空になっていた。

本テストは QTimer.singleShot をキューに変えるQtスタブでその実行順を
再現し、_MENU_OWNER_PROP トークンによる世代保護を検証する。
"""

import sys
import types

import pytest

# ---- qgis.PyQt スタブ(geo_driver import 前に差し込む) ----

_TIMER_QUEUE = []
_SETTINGS = {}


class _Sig:
    def connect(self, fn):
        self.fn = fn

    def disconnect(self):
        self.fn = None


class _QCoreApplication:
    @staticmethod
    def translate(ctx, s):
        return s  # テストは英語ソースのまま


class _QTimer:
    @staticmethod
    def singleShot(msec, fn):
        _TIMER_QUEUE.append(fn)


class _QSettings:
    def value(self, key, default=None):
        return _SETTINGS.get(key, default)

    def setValue(self, key, val):
        _SETTINGS[key] = val


class _QAction:
    def __init__(self, text="", parent=None):
        self._text = text
        self._props = {}
        self._menu = None
        self.triggered = _Sig()
        self.toggled = _Sig()
        self.deleted = False
        self._checked = False
        self._blocked = False

    def text(self):
        if self.deleted:
            raise RuntimeError("deleted")
        return self._text

    def menu(self):
        return self._menu

    def setProperty(self, k, v):
        self._props[k] = v

    def property(self, k):
        return self._props.get(k)

    def setCheckable(self, b):
        pass

    def setChecked(self, b):
        self._checked = b

    def blockSignals(self, b):
        self._blocked = b

    def deleteLater(self):
        self.deleted = True


class _QMenu:
    def __init__(self, title="", parent=None):
        self._title = title
        self._actions = []
        self.aboutToShow = _Sig()
        self._menu_action = _QAction(title)
        self._menu_action._menu = self
        self.deleted = False

    def title(self):
        return self._title

    def menuAction(self):
        return self._menu_action

    def actions(self):
        return list(self._actions)

    def addAction(self, a):
        self._actions.append(a)
        return a

    def removeAction(self, a):
        if a in self._actions:
            self._actions.remove(a)

    def addSeparator(self):
        pass

    def clear(self):
        self._actions.clear()

    def deleteLater(self):
        self.deleted = True


class _FakeMenuBar:
    def __init__(self, plugins_menu):
        self._plugins_menu = plugins_menu
        self._top = _QAction("Plugins")
        self._top._menu = plugins_menu

    def actions(self):
        return [self._top]


class _FakeMainWindow:
    def __init__(self):
        self._plugins_menu = _QMenu("Plugins")
        self._menubar = _FakeMenuBar(self._plugins_menu)
        self._props = {}

    def menuBar(self):
        return self._menubar

    def setProperty(self, k, v):
        self._props[k] = v

    def property(self, k):
        return self._props.get(k)


class _FakeIface:
    """iface.addPluginToMenu / removePluginMenu のQGIS意味論を再現。

    addPluginToMenu: 名前一致のサブメニューをfind-or-createして追加。
    removePluginMenu: 名前一致のサブメニューから除去(空になっても
    サブメニュー自体は残す=実機の観測挙動)。
    """

    def __init__(self):
        self._mw = _FakeMainWindow()
        self._plugins_menu = self._mw._plugins_menu

    def mainWindow(self):
        return self._mw

    def _submenu(self, name, create=False):
        for a in self._plugins_menu.actions():
            m = a.menu()
            if m is not None and m.title() == name:
                return m
        if not create:
            return None
        m = _QMenu(name)
        self._plugins_menu.addAction(m.menuAction())
        return m

    def addPluginToMenu(self, name, action):
        self._submenu(name, create=True).addAction(action)

    def removePluginMenu(self, name, action):
        m = self._submenu(name)
        if m is not None:
            m.removeAction(action)

    def messageBar(self):
        return None


def _install_qgis_stubs():
    qtcore = types.ModuleType("qgis.PyQt.QtCore")
    qtcore.QCoreApplication = _QCoreApplication
    qtcore.QTimer = _QTimer
    qtcore.QSettings = _QSettings
    qtwidgets = types.ModuleType("qgis.PyQt.QtWidgets")
    qtwidgets.QAction = _QAction
    qtwidgets.QMenu = _QMenu
    pyqt = types.ModuleType("qgis.PyQt")
    pyqt.QtCore = qtcore
    pyqt.QtWidgets = qtwidgets
    qgis = types.ModuleType("qgis")
    qgis.PyQt = pyqt
    sys.modules.setdefault("qgis", qgis)
    sys.modules["qgis.PyQt"] = pyqt
    sys.modules["qgis.PyQt.QtCore"] = qtcore
    sys.modules["qgis.PyQt.QtWidgets"] = qtwidgets


_install_qgis_stubs()

import geo_driver  # noqa: E402
from geo_driver import GeoDriverPlugin  # noqa: E402

# スイート内で先に geo_driver がスタブ無しimport済みの場合、
# モジュール変数 QCoreApplication は None のまま。メソッドは
# モジュールグローバルを参照するため直接差し替える。
geo_driver.QCoreApplication = _QCoreApplication


def _flush():
    while _TIMER_QUEUE:
        _TIMER_QUEUE.pop(0)()


def _submenu(iface):
    return iface._submenu(GeoDriverPlugin._MENU_NAME)


@pytest.fixture
def iface():
    _TIMER_QUEUE.clear()
    _SETTINGS.clear()
    return _FakeIface()


def test_reload_keeps_new_generation_menu(iface):
    p1 = GeoDriverPlugin(iface)
    p1.initGui()
    _flush()
    sub = _submenu(iface)
    assert sub is not None
    assert len(sub.actions()) == 5

    # reloadPlugin相当: unload→新インスタンスinitGui→遅延cleanup実行
    p1.unload()
    p2 = GeoDriverPlugin(iface)
    p2.initGui()
    _flush()

    sub = _submenu(iface)
    assert sub is not None
    # 新世代の5項目(AI Assistant/Remote Control/Connection Info/
    # Hot Reload/Deploy Mode)が全て残っている
    assert len(sub.actions()) == 5
    for a in (p2._ai_action, p2._action, p2._conn_action,
              p2._mode_action, p2._hot_menu.menuAction()):
        assert a in sub.actions()
        assert not a.deleted
    # 旧世代のアクションは除去済み
    for a in (p1._ai_action, p1._action, p1._conn_action,
              p1._mode_action):
        assert a not in sub.actions()


def test_sweep_still_removes_orphans(iface):
    p1 = GeoDriverPlugin(iface)
    p1.initGui()
    _flush()
    sub = _submenu(iface)
    # 無刻印の同名孤児(旧版・クラッシュ残存の模擬)
    orphan = _QAction("AI Assistant")
    sub.addAction(orphan)

    p1.unload()
    p2 = GeoDriverPlugin(iface)
    p2.initGui()
    _flush()

    sub = _submenu(iface)
    assert orphan not in sub.actions()
    assert len(sub.actions()) == 5
