import assert from 'node:assert/strict';
import test from 'node:test';
import { mkdtemp, mkdir, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { verifyLinks } from '../scripts/verify-links.mjs';

test('detecta página y ancla rotas', async () => {
  const dir = await mkdtemp(path.join(tmpdir(), 'sgc-links-'));
  await mkdir(path.join(dir, 'ok'));
  await writeFile(path.join(dir, 'index.html'), '<a href="/manual/falta/">x</a><a href="/manual/ok/#no">y</a>');
  await writeFile(path.join(dir, 'ok/index.html'), '<h1 id="si">ok</h1>');
  const errors = await verifyLinks(dir, '/manual');
  assert.equal(errors.length, 2);
});
