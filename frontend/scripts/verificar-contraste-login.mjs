#!/usr/bin/env node

import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import postcss from 'postcss'

const rutas = {
  core: fileURLToPath(new URL('../../sgc/public/css/sciback_core.css', import.meta.url)),
  tema: fileURLToPath(new URL('../../sgc/public/css/themes/upeu.css', import.meta.url)),
  login: fileURLToPath(new URL('../../sgc/public/css/sgc_web.css', import.meta.url)),
}
const raices = {}
for (const [nombre, archivo] of Object.entries(rutas)) {
  try {
    raices[nombre] = postcss.parse(readFileSync(archivo, 'utf8'), { from: archivo })
  } catch (error) {
    console.error(`✗ No se pudo analizar ${archivo}: ${error.message}`)
    process.exit(2)
  }
}

const tokens = new Map()
for (const raiz of [raices.core, raices.tema]) {
  raiz.walkRules(':root', (regla) => regla.walkDecls(/^--color-/, (decl) => tokens.set(decl.prop, decl.value.trim())))
}
const normalizarHex = (valor) => {
  const hex = valor.toLowerCase()
  if (/^#[0-9a-f]{6}$/.test(hex)) return hex
  if (/^#[0-9a-f]{3}$/.test(hex)) return `#${[...hex.slice(1)].map((c) => c + c).join('')}`
  return null
}
const sinImportant = (valor) => valor.replace(/\s*!important\s*$/i, '').trim()
const resolver = (valor, visitados = new Set()) => {
  const limpio = sinImportant(valor)
  const hex = normalizarHex(limpio)
  if (hex) return hex
  const referencia = limpio.match(/^var\(\s*(--color-[\w-]+)\s*\)$/)
  if (!referencia || visitados.has(referencia[1]) || !tokens.has(referencia[1])) return null
  visitados.add(referencia[1])
  return resolver(tokens.get(referencia[1]), visitados)
}
const selector = (nombre, propiedad) => {
  let encontrada
  raices.login.walkRules((regla) => {
    if (!regla.selectors?.includes(nombre)) return
    regla.walkDecls(propiedad, (decl) => { encontrada = decl })
  })
  return encontrada
}
const extraerColor = (decl) => {
  if (!decl) return null
  const valor = sinImportant(decl.value)
  const valorDirecto = resolver(valor)
  if (valorDirecto) return valorDirecto
  const color = valor.match(/(var\(\s*--color-[\w-]+\s*\)|#[0-9a-fA-F]{3,6})\s*$/)?.[1]
  return color ? resolver(color) : null
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

const tarjeta = '.sgc-login-card'
const titulo = '.sgc-login-card-title'
const copia = '.sgc-login-card-copy'
const cta = '.sgc-login-cta'
const estilos = {
  fondoTarjeta: selector(tarjeta, 'background'),
  textoTarjeta: selector(tarjeta, 'color'),
  bordeTarjeta: selector(tarjeta, 'border'),
  titulo: selector(titulo, 'color'),
  copia: selector(copia, 'color'),
  fondoCta: selector(cta, 'background'),
  textoCta: selector(cta, 'color'),
}
const esperados = [
  ['fondo CTA', estilos.fondoCta, 'var(--color-marca-primaria-700)'],
  ['texto CTA', estilos.textoCta, 'var(--color-sobre-marca-primaria)'],
  ['texto de tarjeta', estilos.textoTarjeta, '#17253a'],
  ['título', estilos.titulo, '#17253a'],
  ['copy', estilos.copia, '#53657b'],
]
let fallos = 0
for (const [nombre, decl, esperado] of esperados) {
  if (!decl || sinImportant(decl.value).toLowerCase() !== esperado) {
    fallos += 1
    console.error(`✗ ${nombre}: se esperaba ${esperado}, se encontró ${decl?.value ?? 'declaración ausente'}.`)
  }
}
if (!estilos.bordeTarjeta?.value.includes('var(--color-marca-primaria-400)')) {
  fallos += 1
  console.error('✗ Borde de tarjeta: debe usar var(--color-marca-primaria-400).')
}

const fondoTarjeta = extraerColor(estilos.fondoTarjeta)
const pruebas = [
  ['CTA', extraerColor(estilos.textoCta), extraerColor(estilos.fondoCta), 4.5],
  ['título', extraerColor(estilos.titulo), fondoTarjeta, 4.5],
  ['copy', extraerColor(estilos.copia), fondoTarjeta, 4.5],
  ['cromo de borde', extraerColor(estilos.bordeTarjeta), fondoTarjeta, 3],
]
for (const [nombre, frente, fondo, minimo] of pruebas) {
  if (!frente || !fondo) {
    fallos += 1
    console.error(`✗ ${nombre}: no se pudieron resolver los colores aplicados.`)
    continue
  }
  const ratio = contraste(frente, fondo)
  if (ratio < minimo) fallos += 1
  console.log(`${ratio >= minimo ? '✓' : '✗'} ${nombre}: ${frente} / ${fondo} = ${ratio.toFixed(2)}:1 (mínimo ${minimo}:1)`)
}

const dorados = new Set([...tokens.entries()]
  .filter(([token]) => token.startsWith('--color-marca-secundaria-'))
  .map(([, valor]) => resolver(valor)))
raices.login.walkDecls('color', (decl) => {
  if (decl.value.includes('--color-marca-secundaria-') || dorados.has(resolver(decl.value))) {
    fallos += 1
    console.error(`✗ ${rutas.login}:${decl.source?.start?.line ?? 1} usa dorado como tinta normal.`)
  }
})

if (fallos) process.exit(1)
console.log('✓ Los estilos aplicados del login cumplen contraste WCAG y reservan el dorado a relleno/acento.')
