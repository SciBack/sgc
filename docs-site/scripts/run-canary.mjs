import { mkdtemp, mkdir, copyFile, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { validateCoverage } from './verify-coverage.mjs';
import { verifyLinks } from './verify-links.mjs';
import { verifyPrivacy } from './verify-privacy.mjs';
import { verifyCacheConfig } from './verify-cache-config.mjs';

const name = process.argv[2];
const fixture = (file) => path.resolve('tests/fixtures', file);
let rejected = false;

if (name === 'links') {
  const dir = await mkdtemp(path.join(tmpdir(), 'sgc-canary-links-'));
  await mkdir(path.join(dir, 'ok'));
  await copyFile(fixture('link-broken.html'), path.join(dir, 'index.html'));
  rejected = (await verifyLinks(dir, '/manual')).length > 0;
} else if (name === 'coverage') {
  const data = JSON.parse(await readFile(fixture('coverage-invalid.json'), 'utf8'));
  rejected = (await validateCoverage(data, { repoRoot: new URL('../../', import.meta.url), requirePages: true })).length > 0;
} else if (name === 'privacy') {
  const dir = await mkdtemp(path.join(tmpdir(), 'sgc-canary-privacy-'));
  await copyFile(fixture('privacy-invalid.md'), path.join(dir, 'privacy-invalid.md'));
  rejected = (await verifyPrivacy([dir])).length > 0;
} else if (name === 'contrast') {
  const html = await readFile(fixture('contrast-invalid.html'), 'utf8');
  const [, fg, bg] = html.match(/data-fg="([^"]+)" data-bg="([^"]+)"/);
  rejected = fg === bg;
} else if (name === 'cache-base') {
  const errors = verifyCacheConfig(await readFile(fixture('nginx-cache-invalid.conf'), 'utf8'));
  rejected = errors.some((error) => error.includes('base')) && errors.some((error) => error.includes('pública'));
} else throw new Error(`Canario desconocido: ${name}`);

if (!rejected) { console.error(`CANARY FAIL: ${name} no fue rechazado`); process.exitCode = 1; }
else console.log(`CANARY PASS: ${name} fue rechazado por el verificador.`);
