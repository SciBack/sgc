import { access, readFile } from 'node:fs/promises';
import path from 'node:path';

const dist = path.resolve(process.argv[2] || 'dist');
const required = ['index.html', '404.html', 'sitemap-index.xml', 'pagefind/pagefind.js', 'institution.css'];
const errors = [];
for (const file of required) try { await access(path.join(dist, file)); } catch { errors.push(`ausente: ${file}`); }
const index = await readFile(path.join(dist, 'index.html'), 'utf8');
if (!index.includes('/manual/')) errors.push('base /manual ausente');
if (index.includes('sciback.github.io') || index.includes('/sgc/')) errors.push('host/base antiguos presentes');
if (!index.includes('noindex,nofollow')) errors.push('protección robots ausente');
if (errors.length) { console.error(errors.join('\n')); process.exitCode = 1; }
else console.log('Artefacto estático válido.');
