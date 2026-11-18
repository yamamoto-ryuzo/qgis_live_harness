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
from qgis.core import QgsProject
p = QgsProject.instance()
root = p.layerTreeRoot()
vis = []
for node in root.findLayers():
    lyr = node.layer()
    vis.append({'name': node.name(), 'visible': node.isVisible(), 'count': lyr.featureCount() if lyr else -1, 'id': lyr.id() if lyr else None})
result = json.dumps({'file': p.fileName(), 'layers': len(p.mapLayers()), 'tree': vis}, ensure_ascii=False)
` }));
