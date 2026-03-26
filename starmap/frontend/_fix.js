const fs = require('fs');
const c = fs.readFileSync('starmap/frontend/index.html', 'utf8');
const marker = '</body>\n</html>';
const idx = c.indexOf(marker);
console.log('first marker at', idx, 'of', c.length);
if (idx > 0) {
  fs.writeFileSync('starmap/frontend/index.html', c.slice(0, idx + marker.length), 'utf8');
  console.log('done');
}
