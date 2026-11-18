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
fn = root.opRight()
out = {
  'root_span': [root.parserFirstLine(), root.parserFirstColumn(), root.parserLastLine(), root.parserLastColumn()],
  'fn_span': [fn.parserFirstLine(), fn.parserFirstColumn(), fn.parserLastLine(), fn.parserLastColumn()],
  'fn_text_slice': src[fn.parserFirstColumn()-1:fn.parserLastColumn()] if fn.parserFirstColumn() >= 1 else None,
  'fn_text_slice0': src[fn.parserFirstColumn():fn.parserLastColumn()],
}
arg0 = fn.args().list()[0]
out['arg0_span'] = [arg0.parserFirstLine(), arg0.parserFirstColumn(), arg0.parserLastLine(), arg0.parserLastColumn()]
out['arg0_slice'] = src[arg0.parserFirstColumn()-1:arg0.parserLastColumn()]
# condition 内の WhenThen アクセサ
c = QgsExpression("case when x>1 then line_width(0.2,0.08,15000,@map_scale) else 2 end").rootNode()
conds = c.conditions()
out['conds_type'] = type(conds).__name__
w = conds[0]
out['whenthen_attrs'] = sorted(a for a in dir(w) if not a.startswith('_'))
# between / index
b = QgsExpression("x between 1 and line_width(0.2,0.08,15000,@map_scale)").rootNode()
out['between_attrs'] = sorted(a for a in dir(b) if not a.startswith('_') and a not in ('NamedNode','NodeList','NodeType','cachedStaticValue','clone','dump','effectiveNode','eval','evalNode','hasCachedStaticValue','isStatic','needsGeometry','nodeType','prepare','prepareNode','referencedColumns','referencedFunctions','referencedVariables')) if b else 'None'
result = out
` }));
