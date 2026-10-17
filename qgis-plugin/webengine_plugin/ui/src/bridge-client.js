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
      // transport.send の返信が稀に喪失する(Qt6.8の同期待ち+runJavaScript割り込み)
      // ため、initコールバックが来なければリトライしてチャネルを張り直す
      let attempts = 0;
      const attempt = () => {
        let done = false;
        const timer = setTimeout(() => {
          if (!done && ++attempts < 10) attempt();
        }, 3000);
        new QWebChannel(qt.webChannelTransport, (channel) => {
          if (done) return;
          done = true;
          clearTimeout(timer);
          if (channel.objects && channel.objects.bridge) {
            resolve(channel.objects.bridge);
          } else {
            reject(new Error("bridge object not registered"));
          }
        });
      };
      attempt();
    });
  }

  // 飛行中のsend数。transport.send が返信待ちの間に投げられた別の
  // renderer->browser メッセージ(runJavaScript, console.log 等)は喪失する
  // ため、LiveDriverのeval報告はこの値が0になるまで待ってから送る
  let inflight = 0;

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
    inflight++;
    try {
      return await new Promise((resolve, reject) => {
        try {
          bridge[method](...args, (result) => resolve(result));
        } catch (e) {
          reject(e);
        }
      });
    } finally {
      inflight--;
    }
  }

  async function callJson(method, ...args) {
    const raw = await call(method, ...args);
    return typeof raw === "string" ? JSON.parse(raw) : raw;
  }

  return { getBridge, call, callJson, inflightCount: () => inflight };
})();
