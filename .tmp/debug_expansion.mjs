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
src = 'line_width(0.2,0.08,15000,@map_scale)'
e = QgsExpression(src)
out = {'valid': e.isValid(), 'err': str(e.parserErrorString()) if e.hasParserError() else None}
root = e.rootNode()
out['root_type'] = type(root).__name__ if root else None
out['root_nt'] = int(root.nodeType()) if root else None
out['ntFunction'] = int(QgsExpressionNode.ntFunction)
if root:
    out['span'] = [root.parserFirstLine, root.parserFirstColumn, root.parserLastLine, root.parserLastColumn]
    try:
        out['fnIndex'] = root.fnIndex()
        out['fnName'] = QgsExpression.Functions()[root.fnIndex()].name()
    except Exception as ex:
        out['fn_err'] = str(ex)
    try:
        out['args'] = [a.dump() for a in root.args().list()]
    except Exception as ex:
        out['args_err'] = str(ex)
result = json.dumps(out, ensure_ascii=False)
` }));
