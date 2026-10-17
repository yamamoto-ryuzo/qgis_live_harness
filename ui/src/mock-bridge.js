/**
 * mock-bridge.js
 *
 * 通常ブラウザ(Playwrightテスト用)で PluginBridge を模倣する。
 * メソッドはQWebChannelと同じ「最後の引数がコールバック」形式で呼ばれる。
 * 新しいbridgeメソッドを追加したらここにも対応するモックを追加すること。
 */
window.MockBridge = (function () {
  const layers = [
    { id: "mock_dem_001", name: "DEM 10m", valid: true, type: "RasterLayer" },
    { id: "mock_road_002", name: "道路中心線", valid: true, type: "VectorLayer" },
    { id: "mock_broken_003", name: "欠損レイヤー", valid: false, type: "VectorLayer" },
  ];
  let activeId = null;

  function reply(callback, payload) {
    setTimeout(() => callback(JSON.stringify(payload)), 0);
  }

  return {
    pluginInfo(callback) {
      reply(callback, { name: "WebEngine Plugin", version: "0.1.0", qgis: "mock-4.0.1" });
    },
    listLayers(callback) {
      reply(callback, layers);
    },
    setActiveLayer(layerId, callback) {
      const layer = layers.find((l) => l.id === layerId);
      if (!layer) {
        reply(callback, { ok: false, error: `layer not found: ${layerId}` });
      } else {
        activeId = layerId;
        reply(callback, { ok: true, active: layer.name });
      }
    },
    zoomToActiveLayer(callback) {
      if (!activeId) {
        reply(callback, { ok: false, error: "no active layer" });
      } else {
        reply(callback, { ok: true });
      }
    },
  };
})();
