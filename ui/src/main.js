(function () {
  const $ = (sel) => document.querySelector(sel);
  const status = $("#status");
  const listEl = $("#layer-list");

  function setStatus(msg, isError) {
    status.textContent = msg;
    status.className = isError ? "error" : "";
  }

  function layerLabel(layer) {
    const name = layer.name || layer.id || "(unknown)";
    return layer.valid === false ? `⚠ ${name}` : name;
  }

  async function refresh() {
    try {
      const layers = await BridgeClient.callJson("listLayers");
      listEl.innerHTML = "";
      layers.forEach((layer) => {
        const li = document.createElement("li");
        li.textContent = layerLabel(layer);
        li.dataset.layerId = layer.id;
        li.addEventListener("click", () => activate(layer.id, li));
        listEl.appendChild(li);
      });
      setStatus(`${layers.length} レイヤー`, false);
    } catch (e) {
      setStatus(`listLayers failed: ${e.message || e}`, true);
    }
  }

  async function activate(layerId, li) {
    const res = await BridgeClient.callJson("setActiveLayer", layerId);
    if (!res.ok) {
      setStatus(res.error, true);
      return;
    }
    listEl.querySelectorAll("li").forEach((n) => n.classList.remove("active"));
    li.classList.add("active");
    setStatus(`active: ${res.active}`, false);
  }

  async function zoom() {
    const res = await BridgeClient.callJson("zoomToActiveLayer");
    setStatus(res.ok ? "ズームしました" : res.error, !res.ok);
  }

  async function init() {
    $("#btn-refresh").addEventListener("click", refresh);
    $("#btn-zoom").addEventListener("click", zoom);
    try {
      const info = await BridgeClient.callJson("pluginInfo");
      $("#qgis-version").textContent = `QGIS ${info.qgis}`;
    } catch (e) {
      $("#qgis-version").textContent = "bridge unavailable";
    }
    await refresh();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
