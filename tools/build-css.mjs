// Tree-shakes the site's original theme CSS (captured in _source/squarespace-css)
// down to the selectors used by the pages in public/, removes every reference to
// Squarespace hosts, and writes public/assets/css/theme.css.
// Usage: (cd tools && npm install) && node tools/build-css.mjs
import { PurgeCSS } from 'purgecss';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const srcDir = path.join(root, '_source', 'squarespace-css');
const skip = /user-account-core/;
const order = (f) => (f.includes('static.css') ? 0 : f.includes('site.css') ? 1 : 2);
const files = fs.readdirSync(srcDir).filter((f) => f.endsWith('.css') && !skip.test(f))
  .sort((a, b) => order(a) - order(b));
const seen = new Set();
const css = [];
for (const f of files) {
  const raw = fs.readFileSync(path.join(srcDir, f), 'utf8');
  const key = raw.length + ':' + raw.slice(0, 200);
  if (seen.has(key)) continue; // identical duplicate versions
  seen.add(key);
  css.push({ raw, name: f });
}
const content = [];
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).forEach((e) => {
  const p = path.join(d, e.name);
  if (e.isDirectory()) walk(p); else if (/\.(html|js)$/.test(e.name)) content.push(p);
});
walk(path.join(root, 'public'));

const result = await new PurgeCSS().purge({
  content,
  css,
  keyframes: true,
  // default-style token extractor, plus whole attribute values so selectors like
  // [data-definition-name="website.components.imageFluid"] survive (the default splits on dots)
  extractors: [{
    extensions: ['html', 'js'],
    extractor: (c) => {
      const t = new Set(c.match(/[A-Za-z0-9_\-:\/]+/g) || []);
      for (const m of c.matchAll(/=\s*["']([^"'<>]{1,200})["']/g)) {
        t.add(m[1]);
        m[1].split(/\s+/).forEach((x) => x && t.add(x));
      }
      return [...t];
    },
  }],
  fontFace: false,
  variables: false,
  safelist: {
    standard: ['hidden', 'is-active', 'is-open', 'added', 'loading', 'header--menu-open'],
    greedy: [/data-show/, /data-active/, /data-in\b/, /data-next/, /data-animated/, /data-loaded/, /data-selected/, /data-hover/],
  },
  dynamicAttributes: ['data-show', 'data-active', 'data-in', 'data-next', 'data-animated', 'data-loaded'],
});

let out = result.map((r) => r.css).join('\n');
// drop @font-face blocks and declarations that point at Squarespace hosts
out = out.replace(/@font-face\s*\{[^}]*\}/g, (m) => (/squarespace|sqspcdn/.test(m) ? '' : m));
out = out.replace(/[^;{}]*url\([^)]*(squarespace|sqspcdn)[^)]*\)[^;{}]*;?/g, '');
out = out.replace(/\/\*[^*]*\*+([^/*][^*]*\*+)*\//g, '');
const header = `/* theme.css — The Curl Tapes theme styles.\n   Derived from the site's original theme stylesheet (typography, colors, section/grid layout,\n   gallery, form, product styles) and reduced to the rules these pages use.\n   Regenerate with: node tools/build-css.mjs */\n`;
fs.writeFileSync(path.join(root, 'public', 'assets', 'css', 'theme.css'), header + out);
console.log('theme.css', (out.length / 1024).toFixed(1), 'KB from', files.length, 'files');
