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
from qgis.core import QgsExpression, QgsExpressionNode
out = {}
for label, src in [
    ('binop', '1+2*x'),
    ('unary', '-x'),
    ('cond', "case when x>1 then 'a' else 'b' end"),
    ('inop', "x in (1,2,3)"),
    ('notin', "x not in (1,2)"),
    ('idx', 'arr[1]'),
    ('col', '"field"'),
    ('var', '@map_scale'),
    ('lit', "'str'"),
]:
    e = QgsExpression(src)
    n = e.rootNode()
    d = {'type': type(n).__name__, 'nt': int(n.nodeType()), 'dump': n.dump(),
         'attrs': [a for a in dir(n) if not a.startswith('_')]}
    out[label] = d
result = out
` }));
