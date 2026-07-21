import { access, readFile } from 'node:fs/promises';
import path from 'node:path';

const root = path.resolve('src/content/docs');
const coverage = JSON.parse(await readFile('src/data/coverage.json', 'utf8'));
const missing = [];
for (const item of [...coverage.roles, ...coverage.flows]) {
  try { await access(path.join(root, item.page)); } catch { missing.push(item.page); }
}
if (missing.length) { console.error(`Páginas del manifiesto ausentes:\n${missing.join('\n')}`); process.exitCode = 1; }
else console.log(`Sin páginas funcionales huérfanas: ${coverage.roles.length + coverage.flows.length} declaradas.`);
