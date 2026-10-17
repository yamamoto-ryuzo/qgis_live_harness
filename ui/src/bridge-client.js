/**
 * bridge-client.js
 *
 * QGIS実機では QWebChannel 経由で Python(PluginBridge) に接続し、
 * 通常ブラウザでは mock-bridge.js の MockBridge にフォールバックする。
 * 呼び出し側は `BridgeClient.call(method, ...args) -> Promise` だけを使う。
 */
window.BridgeClient = (function () {
  let bridgePromise = null;

  function connectQWebChannel() {
    return new Promise((resolve, reject) => {
      if (typeof qt === "undefined" || typeof QWebChannel === "undefined") {
        reject(new Error("QWebChannel not available"));
        return;
      }
      new QWebChannel(qt.webChannelTransport, (channel) => {
        if (channel.objects && channel.objects.bridge) {
          resolve(channel.objects.bridge);
        } else {
          reject(new Error("bridge object not registered"));
        }
      });
    });
  }

  function getBridge() {
    if (!bridgePromise) {
      bridgePromise = connectQWebChannel().catch(() => {
        console.info("[BridgeClient] QWebChannel unavailable, using MockBridge");
        return window.MockBridge;
      });
    }
    return bridgePromise;
  }

  async function call(method, ...args) {
    const bridge = await getBridge();
    return new Promise((resolve, reject) => {
      try {
        bridge[method](...args, (result) => resolve(result));
      } catch (e) {
        reject(e);
      }
    });
  }

  async function callJson(method, ...args) {
    const raw = await call(method, ...args);
    return typeof raw === "string" ? JSON.parse(raw) : raw;
  }

  return { getBridge, call, callJson };
})();
