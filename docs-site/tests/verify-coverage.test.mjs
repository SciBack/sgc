import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';

import { validateCoverage } from '../scripts/verify-coverage.mjs';

test('acepta el manifiesto canónico completo', async () => {
  const coverage = JSON.parse(await readFile(new URL('../src/data/coverage.json', import.meta.url)));
  const errors = await validateCoverage(coverage, { repoRoot: new URL('../../', import.meta.url) });
  assert.deepEqual(errors, []);
  assert.equal(coverage.roles.length, 14);
  assert.equal(coverage.flows.filter((flow) => flow.kind === 'workflow').length, 14);
});

test('rechaza ids, estados, páginas y fuentes inválidas', async () => {
  const fixture = JSON.parse(await readFile(new URL('./fixtures/coverage-invalid.json', import.meta.url)));
  const errors = await validateCoverage(fixture, { repoRoot: new URL('../../', import.meta.url), requirePages: true });
  assert.ok(errors.some((error) => error.includes('duplicado')));
  assert.ok(errors.some((error) => error.includes('estado')));
  assert.ok(errors.some((error) => error.includes('página')));
  assert.ok(errors.some((error) => error.includes('fuente')));
});
