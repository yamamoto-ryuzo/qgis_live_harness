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
console.log(await call('qgis_pyeval', { code: `
from qgis.core import QgsExpression, QgsExpressionNode, QgsExpressionNodeFunction
e = QgsExpression('line_width(0.2,0.08,15000,@map_scale)')
rn = e.rootNode()
out = {
  'parse': e.isValid(),
  'ntype': int(rn.nodeType()),
  'ntFunction': int(QgsExpressionNode.ntFunction),
  'has_fnIndex': hasattr(rn, 'fnIndex'),
  'has_args': hasattr(rn, 'args'),
  'has_nodes': hasattr(rn, 'nodes'),
}
try:
    out['fnIndex'] = rn.fnIndex()
except Exception as ex:
    out['fnIndex_err'] = str(ex)
try:
    args = rn.args()
    out['args_type'] = type(args).__name__
    out['args_list'] = [a.dump() for a in args.list()]
except Exception as ex:
    out['args_err'] = str(ex)
# 子ノード走査(非関数ノードの子も取れるか)
e2 = QgsExpression('1+2*line_width(0.2,0.08,15000,@map_scale)')
r2 = e2.rootNode()
try:
    kids = r2.nodes()
    out['nodes_type'] = type(kids).__name__
    out['nodes_dumps'] = [k.dump() for k in kids.list()]
except Exception as ex:
    out['nodes_err'] = str(ex)
out['node_attrs'] = [a for a in dir(rn) if not a.startswith('_')]
result = out
` }));
