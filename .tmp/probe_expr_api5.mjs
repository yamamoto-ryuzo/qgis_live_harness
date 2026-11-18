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
from qgis.core import QgsExpression
src = "1 + 2 * line_width(0.2,0.08,15000,@map_scale)"
e = QgsExpression(src)
root = e.rootNode()
fn = root.opRight().opRight()
def span(n):
    return [n.parserFirstLine, n.parserFirstColumn, n.parserLastLine, n.parserLastColumn]
out = {
  'root_span': span(root),
  'fn_span': span(fn),
}
fs = fn.parserFirstColumn
fe = fn.parserLastColumn
out['slice_1base'] = src[fs-1:fe]
out['slice_0base'] = src[fs:fe]
arg0 = fn.args().list()[0]
out['arg0_span'] = span(arg0)
out['arg0_slice'] = src[arg0.parserFirstColumn-1:arg0.parserLastColumn]
c = QgsExpression("case when x>1 then line_width(0.2,0.08,15000,@map_scale) else 2 end").rootNode()
w = c.conditions()[0]
out['whenthen_attrs'] = sorted(a for a in dir(w) if not a.startswith('_'))
b = QgsExpression("x between 1 and line_width(0.2,0.08,15000,@map_scale)").rootNode()
out['between_type'] = type(b).__name__
out['between_attrs'] = sorted(a for a in dir(b) if not a.startswith('_')) if b else None
i = QgsExpression("arr[1]").rootNode()
out['idx_type'] = type(i).__name__
out['idx_attrs'] = sorted(a for a in dir(i) if not a.startswith('_'))
result = out
` }));
