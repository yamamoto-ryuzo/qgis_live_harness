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
    ('unary', '-x'),
    ('cond', "case when x>1 then 'a' else 'b' end"),
    ('inop', "x in (1,2,3)"),
    ('idx', 'arr[1]'),
]:
    e = QgsExpression(src)
    n = e.rootNode()
    out[label] = {'type': type(n).__name__, 'nt': int(n.nodeType()),
                  'attrs': sorted([a for a in dir(n) if not a.startswith('_') and a not in (
                      'NamedNode','NodeList','NodeType','cachedStaticValue','clone','dump','effectiveNode',
                      'eval','evalNode','hasCachedStaticValue','isStatic','needsGeometry','nodeType',
                      'parserFirstColumn','parserFirstLine','parserLastColumn','parserLastLine','prepare',
                      'prepareNode','referencedColumns','referencedFunctions','referencedVariables')])}
# 演算子テキストの取り方
b = QgsExpression('1+2').rootNode()
try:
    out['binop_text'] = b.text() if callable(getattr(b,'text',None)) else b.text
except Exception as ex:
    out['binop_text_err'] = str(ex)
try:
    out['binop_op'] = int(b.op())
except Exception as ex:
    out['binop_op_err'] = str(ex)
result = out
` }));
