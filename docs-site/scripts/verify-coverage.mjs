import { access, readFile } from 'node:fs/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const VALID_STATUS = new Set(['operativo', 'parcial', 'no-ejecutable']);
const VALID_KIND = new Set(['role', 'workflow', 'programmatic']);

async function exists(file) {
  try { await access(file); return true; } catch { return false; }
}

export async function validateCoverage(coverage, { repoRoot, requirePages = false } = {}) {
  const root = fileURLToPath(repoRoot ?? new URL('../../', import.meta.url));
  const errors = [];
  const ids = new Set();
  for (const [group, entries] of Object.entries({ roles: coverage.roles, flows: coverage.flows })) {
    if (!Array.isArray(entries)) { errors.push(`${group}: debe ser arreglo`); continue; }
    for (const item of entries) {
      if (!item?.id || ids.has(item.id)) errors.push(`id duplicado o vacío: ${item?.id ?? ''}`);
      ids.add(item?.id);
      if (!VALID_KIND.has(item?.kind)) errors.push(`${item?.id}: kind inválido`);
      if (!VALID_STATUS.has(item?.status)) errors.push(`${item?.id}: estado inválido`);
      if (!item?.page?.match(/^(roles|flujos)\/[a-z0-9-]+\.md$/)) errors.push(`${item?.id}: página inválida`);
      if (!Array.isArray(item?.sources) || item.sources.length === 0) errors.push(`${item?.id}: fuente ausente`);
      for (const source of item?.sources ?? []) {
        if (!(await exists(path.join(root, source)))) errors.push(`${item?.id}: fuente inexistente ${source}`);
      }
      if (requirePages && !(await exists(path.join(root, 'docs-site/src/content/docs', item.page)))) {
        errors.push(`${item?.id}: página inexistente ${item.page}`);
      }
    }
  }
  if ((coverage.roles ?? []).length !== 14) errors.push('roles: se requieren exactamente 14');
  if ((coverage.flows ?? []).filter((item) => item.kind === 'workflow').length !== 14) {
    errors.push('workflows: se requieren exactamente 14');
  }
  return errors;
}

async function main() {
  const manifest = JSON.parse(await readFile(new URL('../src/data/coverage.json', import.meta.url)));
  const errors = await validateCoverage(manifest, {
    repoRoot: new URL('../../', import.meta.url),
    requirePages: process.argv.includes('--require-pages'),
  });
  if (errors.length) {
    console.error(errors.map((error) => `- ${error}`).join('\n'));
    process.exitCode = 1;
  } else {
    console.log(`Cobertura válida: ${manifest.roles.length} roles, ${manifest.flows.length} flujos.`);
  }
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) await main();
