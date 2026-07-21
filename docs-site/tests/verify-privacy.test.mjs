import assert from 'node:assert/strict';
import test from 'node:test';
import { mkdtemp, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { verifyPrivacy } from '../scripts/verify-privacy.mjs';

test('detecta DNI, correo, secreto y cookie', async () => {
  const dir = await mkdtemp(path.join(tmpdir(), 'sgc-privacy-'));
  await writeFile(path.join(dir, 'fixture.md'), '12345678 persona@correo.pe password=secreto123 sid=abc123456');
  const errors = await verifyPrivacy([dir]);
  assert.equal(errors.length, 4);
});
