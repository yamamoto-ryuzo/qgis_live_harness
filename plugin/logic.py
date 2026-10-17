"""QGIS非依存の純粋ロジック。pytestで単体検証するためQGISをimportしないこと。"""


def summarize_layers(layers):
    """レイヤオブジェクト列をJSONシリアライズ可能な要約に変換する。

    layers: .id() / .name() / .isValid() / .type() を持つオブジェクトの列。
    テストではモックやデータクラスを渡せばよい。
    """
    summary = []
    for layer in layers:
        summary.append({
            "id": layer.id(),
            "name": layer.name(),
            "valid": bool(layer.isValid()),
            "type": str(layer.type()),
        })
    return summary


def format_layer_label(layer_dict):
    """UI表示用ラベル。無効レイヤは警告マークを付ける。"""
    name = layer_dict.get("name") or layer_dict.get("id") or "(unknown)"
    if not layer_dict.get("valid", True):
        return f"⚠ {name}"
    return name
