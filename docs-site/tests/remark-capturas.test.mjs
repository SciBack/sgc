import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import remarkCapturas from '../src/plugins/remark-capturas.mjs';

const imagen = (url, alt = 'Texto') => ({ type: 'image', url, alt });
const parrafo = (...children) => ({ type: 'paragraph', children });

function procesar(arbol, dir) {
  remarkCapturas({ dir, base: '/manual' })(arbol);
  return arbol;
}

test('con la imagen presente, la referencia apunta al fichero bajo la base', () => {
  const dir = mkdtempSync(path.join(tmpdir(), 'capturas-'));
  writeFileSync(path.join(dir, 'procesos-arbol.png'), '');
  const arbol = procesar({ type: 'root', children: [parrafo(imagen('captura:procesos-arbol'))] }, dir);
  assert.equal(arbol.children[0].children[0].url, '/manual/capturas/procesos-arbol.png');
});

test('sin la imagen, desaparece la referencia y el párrafo que la contenía', () => {
  const dir = mkdtempSync(path.join(tmpdir(), 'capturas-'));
  const arbol = procesar({ type: 'root', children: [
    parrafo(imagen('captura:no-esta')),
    parrafo({ type: 'text', value: 'Se queda.' }),
  ] }, dir);
  assert.equal(arbol.children.length, 1);
  assert.equal(arbol.children[0].children[0].value, 'Se queda.');
});

test('las imágenes normales no se tocan', () => {
  const dir = mkdtempSync(path.join(tmpdir(), 'capturas-'));
  const arbol = procesar({ type: 'root', children: [parrafo(imagen('/manual/otra.png'))] }, dir);
  assert.equal(arbol.children[0].children[0].url, '/manual/otra.png');
});

test('una captura sin texto alternativo o con id raro no compila', () => {
  const dir = mkdtempSync(path.join(tmpdir(), 'capturas-'));
  assert.throws(() => procesar({ type: 'root', children: [parrafo(imagen('captura:sin-alt', ''))] }, dir), /texto alternativo/);
  assert.throws(() => procesar({ type: 'root', children: [parrafo(imagen('captura:Mal_Id'))] }, dir), /id no válido/);
});
