const fs = require('fs');
const rl = require('readline').createInterface({
  input: fs.createReadStream(process.argv[2])
});
const BS = String.fromCharCode(92);
const suffix = BS + 'path=';
let n = 0;
rl.on('line', l => {
  if (l.length > 1000 && l.startsWith('recentProjects') && l.includes(suffix)) {
    const key = l.slice(0, l.indexOf('='));
    console.log('KEY', key, 'len=', l.length);
    console.log('head:', JSON.stringify(l.slice(0, 300)));
    console.log('tail:', JSON.stringify(l.slice(-300)));
    if (++n >= 4) rl.close();
  }
});
