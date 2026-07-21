import { access, readdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

async function files(dir, suffix = '.html') {
  const out = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...await files(full, suffix));
    else if (entry.name.endsWith(suffix)) out.push(full);
  }
  return out;
}

export async function verifyLinks(dist, base = '/manual') {
  const errors = [];
  const pages = await files(dist);
  const routeFor = (file) => {
    const rel = path.relative(dist, file).replaceAll(path.sep, '/');
    return rel === 'index.html' ? '/' : `/${rel.replace(/index\.html$/, '').replace(/\.html$/, '')}`;
  };
  const routeMap = new Map();
  for (const page of pages) routeMap.set(routeFor(page), await readFile(page, 'utf8'));
  for (const [route, html] of routeMap) {
    for (const match of html.matchAll(/href=["']([^"']+)["']/g)) {
      const href = match[1];
      if (/^(https?:|mailto:|tel:|data:|javascript:)/.test(href)) continue;
      if (href === '#_top') continue;
      const url = new URL(href, `https://manual.invalid${base}${route}`);
      if (!url.pathname.startsWith(`${base}/`) && url.pathname !== `${base}`) continue;
      let target = url.pathname.slice(base.length) || '/';
      if (path.extname(target)) {
        try { await access(path.join(dist, target)); }
        catch { errors.push(`${route}: asset inexistente ${href}`); }
        continue;
      }
      if (!target.endsWith('/') && !path.extname(target)) target += '/';
      const targetHtml = routeMap.get(target);
      if (!targetHtml) { errors.push(`${route}: enlace inexistente ${href}`); continue; }
      if (url.hash) {
        const id = decodeURIComponent(url.hash.slice(1)).replace(/["'<>]/g, '');
        if (!new RegExp(`id=["']${id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}["']`).test(targetHtml)) {
          errors.push(`${route}: ancla inexistente ${href}`);
        }
      }
    }
  }
  return errors;
}

async function main() {
  const dist = path.resolve(process.argv[2] || 'dist');
  const errors = await verifyLinks(dist, process.env.DOCS_BASE || '/manual');
  if (errors.length) { console.error(errors.join('\n')); process.exitCode = 1; }
  else console.log('Enlaces internos válidos.');
}
if (import.meta.url === pathToFileURL(process.argv[1]).href) await main();
