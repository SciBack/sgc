#!/usr/bin/env node

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const archivos = process.argv.slice(2)
if (!archivos.length) {
  console.error('Uso: node verificar-capa-institucional.mjs <tema.css> [...]')
  process.exit(2)
}

const coloresPermitidos = [
  /^--color-marca-primaria(?:-|$)/,
  /^--color-marca-secundaria(?:-|$)/,
  /^--color-sobre-marca-(?:primaria|secundaria)$/,
]
const prefijosProhibidos = [
  '--font-', '--radius-', '--shadow-', '--spacing-', '--breakpoint-', '--ease-', '--animate-',
]
const errores = []

for (const archivo of archivos) {
  readFileSync(resolve(archivo), 'utf8').split(/\r?\n/).forEach((linea, indice) => {
    const match = linea.match(/^\s*(--[\w-]+)\s*:/)
    if (!match) return
    const token = match[1]
    const colorAjeno = token.startsWith('--color-') && !coloresPermitidos.some((p) => p.test(token))
    const disenoAjeno = prefijosProhibidos.some((prefijo) => token.startsWith(prefijo))
    if (colorAjeno || disenoAjeno) errores.push(`${archivo}:${indice + 1}  ${token}`)
  })
}

if (errores.length) {
  console.error('✗ La capa institucional redefine responsabilidades de SciBack Core:')
  errores.forEach((error) => console.error(`  ${error}`))
  process.exit(1)
}
console.log(`✓ ${archivos.length} tema(s) institucional(es): solo marca y activos.`)
