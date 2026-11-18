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
from qgis.core import QgsExpression, QgsExpressionNode
src = '"field" * line_width(0.2,0.08,15000,@map_scale) + zen2han(chr(65297))'
e = QgsExpression(src)
out = {'valid': e.isValid(), 'err': str(e.parserErrorString()) if e.hasParserError() else None}
root = e.rootNode()
out['root_nt'] = int(root.nodeType())
funcs = QgsExpression.Functions()
def dump_tree(n, d=0):
    o = {'nt': int(n.nodeType()), 'type': type(n).__name__, 'dump': n.dump(),
         'span': [n.parserFirstLine, n.parserFirstColumn, n.parserLastLine, n.parserLastColumn]}
    if n.nodeType() == QgsExpressionNode.ntFunction:
        try: o['fname'] = funcs[n.fnIndex()].name()
        except Exception as ex: o['fname'] = 'ERR:' + str(ex)
        kids = n.args().list() if n.args() is not None else []
    elif n.nodeType() == QgsExpressionNode.ntBinaryOperator:
        kids = [n.opLeft(), n.opRight()]
    else:
        kids = []
    o['kids'] = [dump_tree(k, d+1) for k in kids if k is not None]
    return o
out['tree'] = dump_tree(root)
result = json.dumps(out, ensure_ascii=False)
` }));
