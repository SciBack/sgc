import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';

const config = await readFile(new URL('../astro.config.mjs', import.meta.url), 'utf8');
const index = await readFile(new URL('../src/content/docs/index.mdx', import.meta.url), 'utf8');

test('la configuración exige HTTPS y usa /manual por defecto', () => {
  assert.match(config, /DOCS_SITE es obligatorio/);
  assert.match(config, /protocol !== 'https:'/);
  assert.match(config, /DOCS_BASE \|\| '\/manual'/);
  assert.match(config, /output: 'static'/);
  assert.match(config, /pagefind: true/);
});

test('el manual no conserva publicación ni enlaces de GitHub Pages', () => {
  assert.doesNotMatch(config, /sciback\.github\.io|editLink/);
  assert.doesNotMatch(index, /\/sgc\//);
});
