// Render a list of stills with one bundle + one browser.
// usage: node scripts/stills.mjs [--scale=0.5] [--out=work/stills] frame1 frame2 ...
import {bundle} from '@remotion/bundler';
import {openBrowser, renderStill, selectComposition, ensureBrowser} from '@remotion/renderer';
import path from 'node:path';
import fs from 'node:fs';

const args = process.argv.slice(2);
const opt = (k, d) => {
  const a = args.find((x) => x.startsWith(`--${k}=`));
  return a ? a.split('=')[1] : d;
};
const frames = args.filter((a) => !a.startsWith('--')).map(Number);
const scale = Number(opt('scale', '0.5'));
const out = opt('out', 'work/stills');
fs.mkdirSync(out, {recursive: true});
const chromiumOptions = {gl: 'angle'};
const t0 = Date.now();
await ensureBrowser();
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts'), onProgress: () => {}});
console.log(`bundled in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
const browser = await openBrowser('chrome', {chromiumOptions});
const composition = await selectComposition({serveUrl, id: 'Main', puppeteerInstance: browser, chromiumOptions});
for (const f of frames) {
  const t1 = Date.now();
  const file = path.join(out, `f${String(f).padStart(4, '0')}.png`);
  await renderStill({
    composition,
    serveUrl,
    output: file,
    frame: f,
    scale,
    imageFormat: 'png',
    puppeteerInstance: browser,
    chromiumOptions,
    timeoutInMilliseconds: 180000,
    onBrowserLog: (l) => {
      if (l.type === 'error' || l.type === 'warning') console.log(`[browser ${l.type}] ${l.text.slice(0, 400)}`);
    },
  });
  console.log(`frame ${f} -> ${file} (${((Date.now() - t1) / 1000).toFixed(1)}s)`);
}
await browser.close({silent: true});
