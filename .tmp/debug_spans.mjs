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
import json
from qgis.core import QgsExpression
src = '1 + 2 * line_width(0.2,0.08,15000,@map_scale)'
e = QgsExpression(src)
def sp(n):
    return [n.parserFirstLine, n.parserFirstColumn, n.parserLastLine, n.parserLastColumn]
root = e.rootNode()
mul = root.opRight()
fn = mul.opRight()
out = {'len': len(src)}
for nm, n in [('root(+)', root), ('mul(*)', mul), ('fn', fn)]:
    out[nm] = sp(n)
for i, a in enumerate(fn.args().list()):
    out['arg%d' % i] = sp(a) + [a.dump()]
    out['arg%d_slice_1b' % i] = src[a.parserFirstColumn-1:a.parserLastColumn]
    out['arg%d_slice_alt' % i] = src[a.parserFirstColumn-1:a.parserLastColumn-1] if a.parserLastColumn > 1 else ''
out['src'] = src
result = json.dumps(out, ensure_ascii=False)
` }));
