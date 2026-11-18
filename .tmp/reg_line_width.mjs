// geo_userfunc.bridge.saveFunction -> reload で line_width を稼働QGISへ登録
const URL = 'http://127.0.0.1:8089/live/mcp';
async function call(name, args) {
  const r = await fetch(URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream' },
    body: JSON.stringify({ jsonrpc: '2.0', id: Math.floor(Math.random()*1e6), method: 'tools/call', params: { name, arguments: args } }),
  });
  const t = await r.text();
  // SSE 形式の場合は data: 行を拾う
  const m = t.match(/^data:\s*(.+)$/m);
  const j = JSON.parse(m ? m[1] : t);
  return j.result ?? j;
}
const source = `from qgis.core import *


@qgsfunction(args='auto', group='ユーザー関数')
def line_width(base, minimum, ref_scale, scale, feature, parent):
    """縮尺連動の線幅(mm)を返す。

    基準縮尺 ref_scale では base mm。ズームアウト(縮尺分母の増大)で
    base*ref_scale/scale に反比例して細くなり minimum で打止め、
    ズームイン側は base で頭打ちする。
    clamp(minimum, base*ref_scale/scale, base) と等価。
    KASUGAI Canvas (web/shared/qml-style.js EXPR_FUNCS) の
    line_width 実装と同じ縮尺則。
    """
    try:
        b = float(base)
        m = float(minimum)
        r = float(ref_scale)
        s = float(scale)
    except (TypeError, ValueError):
        return None
    if r <= 0 or s <= 0:
        return m
    w = b * r / s
    return min(max(w, m), b)
`;
console.log(JSON.stringify(await call('qgis_bridge_call', { plugin_id: 'geo_userfunc', method: 'saveFunction', args: ['line_width.py', source] }), null, 1).slice(0, 2000));
console.log('--- reload ---');
console.log(JSON.stringify(await call('qgis_bridge_call', { plugin_id: 'geo_userfunc', method: 'reload', args: [] }), null, 1).slice(0, 2000));
