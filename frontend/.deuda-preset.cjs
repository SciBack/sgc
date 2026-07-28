/**
 * ¿Qué clases del código dependen del preset de frappe-ui?
 *
 * Tailwind NO falla ante una clase inexistente: la ignora y el estilo se pierde
 * en silencio. Así que en vez de quitar el preset y "ver si se ve bien", se
 * calcula la diferencia entre el tema CON preset y SIN preset, y se busca en el
 * código quién usa esas claves. Eso da la lista exacta de la deuda.
 */
const resolveConfig = require('tailwindcss/resolveConfig')
const frappeUIPreset = require('frappe-ui/tailwind')
const { readFileSync, readdirSync, statSync } = require('node:fs')
const { join } = require('node:path')

const base = { content: [] }
const con = resolveConfig({ ...base, presets: [frappeUIPreset] }).theme
const sin = resolveConfig(base).theme

// Aplana {colors:{gray:{100:..}}} -> "gray-100"
const aplanar = (obj, pre = '') =>
  Object.entries(obj || {}).flatMap(([k, v]) => {
    const nom = k === 'DEFAULT' ? pre : pre ? `${pre}-${k}` : k
    return v && typeof v === 'object' && !Array.isArray(v) ? aplanar(v, nom) : [nom]
  })

const SECCIONES = ['colors', 'spacing', 'fontSize', 'borderRadius', 'boxShadow', 'fontFamily']
const soloConPreset = {}
for (const s of SECCIONES) {
  const a = new Set(aplanar(con[s]))
  const b = new Set(aplanar(sin[s]))
  const delta = [...a].filter((x) => !b.has(x))
  if (delta.length) soloConPreset[s] = delta
}

// Prefijos de utilidad por sección, para reconstruir la clase escrita.
const PREFIJOS = {
  colors: ['bg', 'text', 'border', 'ring', 'fill', 'stroke', 'divide', 'outline', 'from', 'to', 'via', 'shadow', 'placeholder', 'accent', 'decoration'],
  spacing: ['p', 'px', 'py', 'pt', 'pb', 'pl', 'pr', 'm', 'mx', 'my', 'mt', 'mb', 'ml', 'mr', 'gap', 'gap-x', 'gap-y', 'w', 'h', 'size', 'space-x', 'space-y', 'inset', 'top', 'bottom', 'left', 'right', 'translate-x', 'translate-y'],
  fontSize: ['text'],
  borderRadius: ['rounded', 'rounded-t', 'rounded-b', 'rounded-l', 'rounded-r', 'rounded-tl', 'rounded-tr', 'rounded-bl', 'rounded-br'],
  boxShadow: ['shadow'],
  fontFamily: ['font'],
}

// Todas las clases candidatas que SOLO existen gracias al preset.
const candidatas = new Map() // clase -> "seccion:clave"
for (const [sec, claves] of Object.entries(soloConPreset)) {
  for (const clave of claves) {
    for (const p of PREFIJOS[sec] || []) {
      candidatas.set(`${p}-${clave}`, `${sec}:${clave}`)
    }
  }
}

// Recorrer el código fuente.
const archivos = []
const andar = (dir) => {
  for (const e of readdirSync(dir)) {
    const ruta = join(dir, e)
    if (statSync(ruta).isDirectory()) andar(ruta)
    else if (/\.(vue|js|ts|jsx|tsx|html)$/.test(e)) archivos.push(ruta)
  }
}
andar(process.argv[2] || 'src')

const usos = new Map() // clase -> Set(archivo)
for (const f of archivos) {
  const txt = readFileSync(f, 'utf8')
  // Tokens tipo clase, incluyendo variantes (hover:, dark:, sm:) y negativos.
  for (const m of txt.matchAll(/[-a-zA-Z0-9:/[\]().]+/g)) {
    const tok = m[0]
    // Quitar variantes de delante: "hover:focus:bg-x" -> "bg-x"
    const base = tok.slice(tok.lastIndexOf(':') + 1).replace(/^-/, '').replace(/\/\d+$/, '')
    if (candidatas.has(base)) {
      if (!usos.has(base)) usos.set(base, new Set())
      usos.get(base).add(f)
    }
  }
}

console.log(`Claves que aporta SOLO el preset de frappe-ui:`)
for (const [s, v] of Object.entries(soloConPreset)) console.log(`  ${s.padEnd(14)} ${v.length}`)

console.log(`\nDEUDA REAL — clases usadas en el código que morirían al quitar el preset:`)
if (!usos.size) {
  console.log('  (ninguna)')
} else {
  const orden = [...usos.entries()].sort((a, b) => b[1].size - a[1].size)
  for (const [clase, fs] of orden) {
    console.log(`  ${clase.padEnd(30)} ${String(fs.size).padStart(2)} fichero(s)  [${candidatas.get(clase)}]`)
    for (const f of [...fs].sort()) console.log(`      ${f}`)
  }
  console.log(`\n  TOTAL: ${usos.size} clases distintas`)
}
