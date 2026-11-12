# -*- coding: utf-8 -*-
"""geo_launcher - kasugai_qgis ランチャーの QGIS プラグイン移植"""


def classFactory(iface):  # pylint: disable=invalid-name
    from .plugin import plugin

    return plugin(iface)
