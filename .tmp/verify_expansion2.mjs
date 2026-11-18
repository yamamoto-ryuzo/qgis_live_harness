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
from geo_webview import kasugai_export as ke
exps = ke._user_func_expansions()
cases = [
  'line_width(0.2,0.08,15000,@map_scale)',
  'if(@map_scale>=100000, 1+line_width(0.2,0.08,15000,@map_scale), 0.3)',
  "case when x>1 then line_width(0.2,0.08,15000,@map_scale) else 2 end",
  '"field" * line_width(0.2,0.08,15000,@map_scale) + zen2han(char(65297))',
  "'literal line_width(x)'",
  'line_width(0.2,0.08,15000,@map_scale -- trailing' + chr(10) + ')',
  'if(a>1,line_width(0.2,0.08,15000,@map_scale),line_width(0.5,0.1,25000,@map_scale))',
]
out = {}
for c in cases:
    try:
        out[c] = ke._expand_user_func_expr(c, exps)
    except Exception as ex:
        out[c] = 'ERR ' + str(ex)
result = json.dumps(out, ensure_ascii=False)
` }));
