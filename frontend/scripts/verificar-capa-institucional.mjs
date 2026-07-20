#!/usr/bin/env node

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import postcss from 'postcss'

const archivos = process.argv.slice(2).map((archivo) => resolve(archivo))
if (!archivos.length) {
  console.error('Uso: node verificar-capa-institucional.mjs <tema.css> [...]')
  process.exit(2)
}

const coloresPermitidos = [
  /^--color-marca-primaria(?:-|$)/,
  /^--color-marca-secundaria(?:-|$)/,
  /^--color-sobre-marca-(?:primaria|secundaria)$/,
]
const errores = []
const ubicacion = (archivo, nodo) => `${archivo}:${nodo.source?.start?.line ?? 1}`

for (const archivo of archivos) {
  let raiz
  try {
    raiz = postcss.parse(readFileSync(archivo, 'utf8'), { from: archivo })
  } catch (error) {
    console.error(`✗ No se pudo analizar ${archivo}: ${error.message}`)
    process.exit(2)
  }

  const reglas = raiz.nodes.filter((nodo) => nodo.type === 'rule')
  if (reglas.length !== 1) errores.push(`${archivo}:1  se exige exactamente una regla :root`)

  for (const nodo of raiz.nodes) {
    if (nodo.type === 'comment') continue
    if (nodo.type !== 'rule') {
      errores.push(`${ubicacion(archivo, nodo)}  nodo @${nodo.name ?? nodo.type} no permitido`)
      continue
    }
    if (nodo.selector !== ':root') {
      errores.push(`${ubicacion(archivo, nodo)}  selector ${nodo.selector} no permitido; use :root`)
      continue
    }
    for (const hijo of nodo.nodes) {
      if (hijo.type === 'comment') continue
      if (hijo.type !== 'decl') {
        errores.push(`${ubicacion(archivo, hijo)}  nodo ${hijo.type} no permitido dentro de :root`)
        continue
      }
      if (!coloresPermitidos.some((patron) => patron.test(hijo.prop))) {
        errores.push(`${ubicacion(archivo, hijo)}  ${hijo.prop}`)
      }
    }
  }
}

if (errores.length) {
  console.error('✗ La capa institucional redefine responsabilidades de SciBack Core:')
  errores.forEach((error) => console.error(`  ${error}`))
  process.exit(1)
}
console.log(`✓ ${archivos.length} tema(s) institucional(es): una regla :root con solo tokens de marca.`)
