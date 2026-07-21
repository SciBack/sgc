import { readFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';

export function verifyCacheConfig(config) {
  const errors = [];
  if (!config.includes('location = /manual')) errors.push('redirect/base /manual ausente');
  if (!config.includes('location ^~ /manual/_astro/')) errors.push('assets versionados sin bloque dedicado');
  if (!/location \^~ \/manual\/_astro\/[\s\S]*immutable/.test(config)) errors.push('assets sin caché immutable');
  if (!/location \/manual\/[\s\S]*no-store/.test(config)) errors.push('contenido protegido sin no-store');
  if (/location \/manual\/[\s\S]*Cache-Control\s+["']?public/.test(config)) errors.push('contenido protegido con caché pública');
  if (/Cache-Control\s+["']?public/.test(config) && !config.includes('location ^~ /manual/_astro/')) errors.push('caché pública fuera de assets versionados');
  if (!config.includes('try_files $uri $uri/index.html =404')) errors.push('404 real ausente');
  return errors;
}

async function main() {
  const config = await readFile(process.argv[2] || 'nginx.conf', 'utf8');
  const errors = verifyCacheConfig(config);
  if (errors.length) { console.error(errors.join('\n')); process.exitCode = 1; }
  else console.log('Base, caché y 404 de Nginx válidos.');
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) await main();
