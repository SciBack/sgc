#!/usr/bin/env node

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import postcss from 'postcss'

const predeterminados = [
  new URL('../../sgc/public/css/sciback_core.css', import.meta.url),
  new URL('../../sgc/public/css/themes/upeu.css', import.meta.url),
  new URL('../../sgc/public/css/sgc_web.css', import.meta.url),
].map(fileURLToPath)
const archivos = process.argv.length > 2 ? process.argv.slice(2).map((archivo) => resolve(archivo)) : predeterminados
const fuentes = []

for (const archivo of archivos) {
  try {
    fuentes.push({ archivo, raiz: postcss.parse(readFileSync(archivo, 'utf8'), { from: archivo }) })
  } catch (error) {
    console.error(`✗ No se pudo analizar ${archivo}: ${error.message}`)
    process.exit(2)
  }
}

const declarados = new Set()
for (const { raiz } of fuentes) {
  raiz.walkDecls((declaracion) => {
    if (declaracion.prop.startsWith('--color-')) declarados.add(declaracion.prop)
  })
}

const faltantes = []
for (const { archivo, raiz } of fuentes) {
  raiz.walkDecls((declaracion) => {
    for (const match of declaracion.value.matchAll(/var\(\s*(--color-[\w-]+)/g)) {
      if (!declarados.has(match[1])) {
        faltantes.push(`${archivo}:${declaracion.source?.start?.line ?? 1}  ${match[1]}`)
      }
    }
  })
}

if (faltantes.length) {
  console.error('✗ El login usa tokens de color sin declarar:')
  for (const error of new Set(faltantes)) console.error(`  ${error}`)
  process.exit(1)
}

console.log(`✓ Tokens del login: ${declarados.size} declaraciones cubren todos los usos AST.`)
