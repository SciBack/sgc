import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const RULES = [
  ['posible DNI', /(?<!\d)\d{8}(?!\d)/g],
  ['correo personal', /\b[A-Z0-9._%+-]+@(?!example\.invalid\b)[A-Z0-9.-]+\.[A-Z]{2,}\b/gi],
  ['secreto', /(?:password|passwd|token|authorization|secret)\s*[:=]\s*["']?[A-Za-z0-9_\-/.]{8,}/gi],
  ['cookie de sesión', /\bsid=[A-Za-z0-9%._-]+/gi],
];

async function walk(dir) {
  const out = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    if (['node_modules', '.astro'].includes(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...await walk(full)); else out.push(full);
  }
  return out;
}

export async function verifyPrivacy(dirs) {
  const errors = [];
  for (const dir of dirs) for (const file of await walk(dir)) {
    // Los bundles vendor minificados contienen números de precisión y correos de
    // fixtures upstream; el artefacto propio verificable es HTML y el contenido fuente.
    if (!/\.(?:md|mdx|html|json)$/.test(file)) continue;
    const content = await readFile(file, 'utf8');
    for (const [label, regex] of RULES) for (const match of content.matchAll(regex)) {
      errors.push(`${file}:${content.slice(0, match.index).split('\n').length}: ${label}`);
    }
  }
  return errors;
}

async function main() {
  const dirs = process.argv.slice(2).map((dir) => path.resolve(dir));
  const errors = await verifyPrivacy(dirs.length ? dirs : [path.resolve('src/content/docs'), path.resolve('dist')]);
  if (errors.length) { console.error(errors.join('\n')); process.exitCode = 1; }
  else console.log('Privacidad: no se detectaron datos o secretos prohibidos.');
}
if (import.meta.url === pathToFileURL(process.argv[1]).href) await main();
