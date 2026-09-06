// Mechanical size exports of the approved emblem; no redraw or logo changes.
// Run with sharp installed locally or NODE_PATH pointing to the bundled libraries.
const sharp = require('sharp');
const path = require('node:path');
const assets = path.resolve(__dirname, '../site/public');
const source = path.join(assets, 'southern-flow-emblem-badge.png');
(async () => {
  for (const [name, size] of [['favicon-32.png', 32], ['icon-192.png', 192], ['apple-touch-icon.png', 180]]) {
    await sharp(source).resize(size, size, {
      fit: 'contain', background: { r: 255, g: 255, b: 255, alpha: 0 },
    }).png({ compressionLevel: 9 }).toFile(path.join(assets, name));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
