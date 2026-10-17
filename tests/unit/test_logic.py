from webengine_plugin.logic import format_layer_label, summarize_layers


class FakeLayer:
    def __init__(self, id, name, valid=True, type="VectorLayer"):
        self._id, self._name, self._valid, self._type = id, name, valid, type

    def id(self):
        return self._id

    def name(self):
        return self._name

    def isValid(self):
        return self._valid

    def type(self):
        return self._type


def test_summarize_layers():
    layers = [FakeLayer("a", "道路"), FakeLayer("b", "DEM", valid=False, type="RasterLayer")]
    result = summarize_layers(layers)
    assert result[0] == {"id": "a", "name": "道路", "valid": True, "type": "VectorLayer"}
    assert result[1]["valid"] is False


def test_format_layer_label():
    assert format_layer_label({"name": "道路", "valid": True}) == "道路"
    assert format_layer_label({"name": "壊れ", "valid": False}) == "⚠ 壊れ"
    assert format_layer_label({"id": "x1"}) == "x1"
