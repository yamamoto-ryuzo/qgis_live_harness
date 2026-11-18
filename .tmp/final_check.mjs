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
  return j.result?.content?.[0]?.text ?? JSON.stringify(j);
}
// 保存済みファイルの実パスと内容
const rf = JSON.parse(await call('qgis_bridge_call', { plugin_id: 'geo_userfunc', method: 'readFunction', args: ['line_width.py'] }));
console.log('readFunction.ok:', rf.ok, '| source bytes:', rf.source?.length);
// グループ確認 + 実 QML の DD 式を DM_3 レイヤコンテキストで評価
console.log(await call('qgis_pyeval', { code: `
from qgis.core import QgsExpression, QgsExpressionContext, QgsExpressionContextUtils, QgsProject
grp = [(f.name(), f.group()) for f in QgsExpression.Functions() if f.name() == 'line_width']
lyr = QgsProject.instance().mapLayersByName('DM_3')
out = {'group': grp}
if lyr:
    lyr = lyr[0]
    ctx = QgsExpressionContext()
    ctx.appendScope(QgsExpressionContextUtils.mapSettingsScope(iface.mapCanvas().mapSettings()))
    ctx.appendScope(QgsExpressionContextUtils.layerScope(lyr))
    e = QgsExpression('line_width(0.2,0.08,15000,@map_scale)')
    out['dm3_ctx'] = {'scale': iface.mapCanvas().scale(), 'val': e.evaluate(ctx), 'err': str(e.evalErrorString()) if e.hasEvalError() else None}
result = out
` }));
