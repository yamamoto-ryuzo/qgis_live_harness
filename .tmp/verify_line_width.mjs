const URL = 'http://127.0.0.1:8089/live/mcp';
async function call(name, args) {
  const r = await fetch(URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream' },
    body: JSON.stringify({ jsonrpc: '2.0', id: Math.floor(Math.random()*1e6), method: 'tools/call', params: { name, arguments: args } }),
  });
  const t = await r.text();
  const m = t.match(/^data:\s*(.+)$/m);
  const j = JSON.parse(m ? m[1] : t);
  const txt = j.result?.content?.[0]?.text ?? JSON.stringify(j);
  return txt;
}
// 1) 登録確認 + リテラル引数での評価
console.log(await call('qgis_pyeval', { code: `
from qgis.core import QgsExpression, QgsExpressionContext, QgsExpressionContextUtils
names = sorted(f.name() for f in QgsExpression.Functions() if f.name() == 'line_width')
ctx = QgsExpressionContext()
vals = {}
for s in (5000, 15000, 30000, 100000, 1000000):
    e = QgsExpression(f'line_width(0.2,0.08,15000,{s})')
    vals[s] = e.evaluate(ctx)
result = {'registered': names, 'vals': vals}
` }));
// 2) @map_scale 連動: mapCanvas の mapSettings スコープで評価
console.log(await call('qgis_pyeval', { code: `
from qgis.core import QgsExpression, QgsExpressionContext, QgsExpressionContextUtils
ctx = QgsExpressionContext()
ctx.appendScope(QgsExpressionContextUtils.mapSettingsScope(iface.mapCanvas().mapSettings()))
e = QgsExpression('line_width(0.2,0.08,15000,@map_scale)')
result = {'scale': iface.mapCanvas().scale(), 'val': e.evaluate(ctx), 'err': str(e.evalErrorString()) if e.hasEvalError() else None}
` }));
