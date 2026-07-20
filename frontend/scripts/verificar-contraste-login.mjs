#!/usr/bin/env node

import { readFileSync } from 'node:fs'

const core = readFileSync(new URL('../../sgc/public/css/sciback_core.css', import.meta.url), 'utf8')
const tema = readFileSync(new URL('../../sgc/public/css/themes/upeu.css', import.meta.url), 'utf8')
const login = readFileSync(new URL('../../sgc/public/css/sgc_web.css', import.meta.url), 'utf8')
const css = `${core}\n${tema}`

const valorToken = (token) => {
  const match = css.match(new RegExp(`${token.replaceAll('-', '\\-')}\\s*:\\s*(#[0-9a-fA-F]{6})\\b`))
  if (!match) throw new Error(`No se encontró un valor hexadecimal real para ${token}.`)
  return match[1]
}
const luminancia = (hex) => {
  const rgb = [1, 3, 5].map((inicio) => Number.parseInt(hex.slice(inicio, inicio + 2), 16) / 255)
  const lineal = (canal) => canal <= 0.04045 ? canal / 12.92 : ((canal + 0.055) / 1.055) ** 2.4
  return 0.2126 * lineal(rgb[0]) + 0.7152 * lineal(rgb[1]) + 0.0722 * lineal(rgb[2])
}
const contraste = (a, b) => {
  const [alta, baja] = [luminancia(a), luminancia(b)].sort((x, y) => y - x)
  return (alta + 0.05) / (baja + 0.05)
}

const blanco = '#ffffff'
const pruebas = [
  ['texto blanco / primaria 700', blanco, valorToken('--color-marca-primaria-700'), 4.5],
  ['texto sobre marca secundaria / blanco', valorToken('--color-sobre-marca-secundaria'), blanco, 4.5],
  ['texto secundario / blanco', '#62748c', blanco, 4.5],
  ['cromo primaria 400 / blanco', valorToken('--color-marca-primaria-400'), blanco, 3],
]
let fallos = 0

for (const [nombre, frente, fondo, minimo] of pruebas) {
  const ratio = contraste(frente, fondo)
  const pasa = ratio >= minimo
  if (!pasa) fallos += 1
  console.log(`${pasa ? '✓' : '✗'} ${nombre}: ${ratio.toFixed(2)}:1 (mínimo ${minimo}:1)`)
}

const dorados = [...tema.matchAll(/--color-marca-secundaria-[\w-]+\s*:\s*(#[0-9a-fA-F]{6})/g)]
  .map((match) => match[1].toLowerCase())
const tintaDorada = [...login.matchAll(/(?:^|[;{])\s*color\s*:\s*([^;}]*)/gim)]
  .filter((match) => /--color-marca-secundaria/.test(match[1]) || dorados.includes(match[1].trim().toLowerCase()))

if (tintaDorada.length) {
  fallos += tintaDorada.length
  console.error('✗ El dorado institucional solo puede usarse como relleno o acento, no como texto normal.')
}

if (fallos) process.exit(1)
console.log('✓ Contraste del login y uso del dorado cumplen WCAG.')
