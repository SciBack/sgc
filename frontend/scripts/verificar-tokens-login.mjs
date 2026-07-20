#!/usr/bin/env node

import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const archivos = [
  new URL('../../sgc/public/css/sciback_core.css', import.meta.url),
  new URL('../../sgc/public/css/themes/upeu.css', import.meta.url),
  new URL('../../sgc/public/css/sgc_web.css', import.meta.url),
]

const fuentes = archivos.map((archivo) => ({
  archivo: fileURLToPath(archivo),
  css: readFileSync(archivo, 'utf8'),
}))
const declarados = new Set(
  fuentes.flatMap(({ css }) => [...css.matchAll(/(--color-[\w-]+)\s*:/g)].map((match) => match[1])),
)
const faltantes = new Map()

for (const { archivo, css } of fuentes) {
  for (const match of css.matchAll(/var\(\s*(--color-[\w-]+)/g)) {
    if (!declarados.has(match[1])) {
      const usos = faltantes.get(match[1]) ?? []
      usos.push(archivo)
      faltantes.set(match[1], usos)
    }
  }
}

if (faltantes.size) {
  console.error('✗ El login usa tokens de color sin declarar:')
  for (const [token, usos] of faltantes) {
    console.error(`  ${token}: ${[...new Set(usos)].join(', ')}`)
  }
  process.exit(1)
}

console.log(`✓ Tokens del login: ${declarados.size} declaraciones cubren todos los usos.`)
