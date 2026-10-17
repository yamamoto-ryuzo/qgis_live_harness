def classFactory(iface):
    from .main_plugin import WebEnginePlugin
    return WebEnginePlugin(iface)
