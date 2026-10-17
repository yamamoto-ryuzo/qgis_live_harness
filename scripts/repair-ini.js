const fs = require('fs');
const src = process.argv[2];
const dst = process.argv[3];
const BS = String.fromCharCode(92);
const bad = [
  'recentProjects' + BS + '8' + BS + 'path=',
  'recentProjects' + BS + '10' + BS + 'path=',
];
const replacement = 'Q:/ProjectFiles/ProjectFile.qgs';

const buf = fs.readFileSync(src);
const NL = 10;
const out = fs.createWriteStream(dst);
let pos = 0, fixed = 0, lines = 0;
while (pos < buf.length) {
  let end = buf.indexOf(NL, pos);
  if (end === -1) end = buf.length;
  const line = buf.subarray(pos, end + (end < buf.length ? 1 : 0));
  const head = line.subarray(0, 40).toString('latin1');
  const key = bad.find(k => head.startsWith(k));
  if (key && line.length > 1000) {
    out.write(key + replacement + '\n');
    fixed++;
  } else {
    out.write(line);
  }
  pos = end + 1;
  lines++;
}
out.end(() => {
  console.log('lines:', lines, 'fixed:', fixed);
  console.log('src:', buf.length, 'dst:', fs.statSync(dst).size);
});
