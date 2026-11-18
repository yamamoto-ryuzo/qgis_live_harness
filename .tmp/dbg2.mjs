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
out = {}
for s in ['"field" * line_width(0.2,0.08,15000,@map_scale)',
          'zen2han(chr(65297))',
          '"field" * line_width(0.2,0.08,15000,@map_scale) + zen2han(chr(65297))',
          'chr(65297)']:
    e = QgsExpression(s)
    out[s] = {'valid': e.isValid(), 'err': str(e.parserErrorString()) if e.hasParserError() else None}
result = json.dumps(out, ensure_ascii=False)
` }));
