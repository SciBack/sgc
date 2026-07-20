#!/usr/bin/env node

import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const verificador = fileURLToPath(new URL('./verificar-capa-institucional.mjs', import.meta.url))
const fixture = fileURLToPath(new URL('./fixtures/institucion-invalida.css', import.meta.url))
const resultado = spawnSync(process.execPath, [verificador, fixture], { encoding: 'utf8' })

if (resultado.status !== 1) {
  process.stderr.write(resultado.stderr)
  console.error(`✗ Canary inválido: se esperaba código 1 y terminó con ${resultado.status ?? 'sin código'}.`)
  process.exit(1)
}

console.log('✓ Canary institucional: el verificador rechaza tokens ajenos a la marca.')
