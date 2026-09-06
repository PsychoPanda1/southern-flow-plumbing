// Render a white favicon from the existing emblem, preserving its geometry.
// Run with sharp installed locally or NODE_PATH set to the bundled libraries.
const fs = require('node:fs');
const path = require('node:path');
const sharp = require('sharp');
const assets = path.resolve(__dirname, '../site/public');
const emblem = fs.readFileSync(path.join(assets, 'icon-192.png')).toString('base64');
const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="192" height="192" viewBox="0 0 192 192">
  <title>Southern Flow Plumbing</title>
  <defs>
    <filter id="white-emblem" color-interpolation-filters="sRGB">
      <!-- Make the dark artwork white and remove the light badge background. -->
      <feColorMatrix result="whiteArtwork" type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  -0.4252 -1.4304 -0.1444 0 2"/>
      <feComposite in="whiteArtwork" in2="SourceAlpha" operator="in"/>
    </filter>
  </defs>
  <image width="192" height="192" href="data:image/png;base64,${emblem}" filter="url(#white-emblem)"/>
</svg>
`;
(async () => {
  fs.writeFileSync(path.join(assets, 'favicon.svg'), svg);
  await sharp(Buffer.from(svg)).resize(32, 32).png().toFile(path.join(assets, 'favicon-white-32.png'));
})().catch(error => { console.error(error); process.exitCode = 1; });
