#!/usr/bin/env node

import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const verificador = fileURLToPath(new URL('./verificar-capa-institucional.mjs', import.meta.url))
const verificadorTokens = fileURLToPath(new URL('./verificar-tokens-login.mjs', import.meta.url))
const fixture = (nombre) => fileURLToPath(new URL(`./fixtures/${nombre}`, import.meta.url))
const ejecutar = (script, archivo) => spawnSync(process.execPath, [script, archivo], { encoding: 'utf8' })
const exigir = (condicion, mensaje, resultado) => {
  if (condicion) return
  process.stderr.write(resultado?.stderr ?? '')
  console.error(`✗ ${mensaje}`)
  process.exit(1)
}

const invalida = fixture('institucion-invalida-minificada.css')
const resultadoInvalido = ejecutar(verificador, invalida)
exigir(resultadoInvalido.status === 1, `El tema minificado debía terminar con código 1, obtuvo ${resultadoInvalido.status}.`, resultadoInvalido)
exigir(resultadoInvalido.stderr.includes(invalida) && resultadoInvalido.stderr.includes('--color-fondo'), 'El diagnóstico del tema minificado no identifica fixture y token.', resultadoInvalido)

const propiedad = fixture('institucion-propiedad-invalida.css')
const resultadoPropiedad = ejecutar(verificador, propiedad)
exigir(resultadoPropiedad.status === 1, 'Una propiedad CSS directa debía terminar con código 1.', resultadoPropiedad)
exigir(resultadoPropiedad.stderr.includes(propiedad) && resultadoPropiedad.stderr.includes('font-family'), 'El diagnóstico no identifica la propiedad CSS directa.', resultadoPropiedad)

const comentario = ejecutar(verificador, fixture('institucion-comentario-valido.css'))
exigir(comentario.status === 0, 'Las declaraciones aparentes dentro de comentarios deben ignorarse.', comentario)

const inexistente = fixture('institucion-no-existe.css')
const resultadoInexistente = ejecutar(verificador, inexistente)
exigir(resultadoInexistente.status === 2, `ENOENT debe clasificarse con código 2, obtuvo ${resultadoInexistente.status}.`, resultadoInexistente)

const sintaxis = fixture('institucion-sintaxis-invalida.css')
const resultadoSintaxis = ejecutar(verificador, sintaxis)
exigir(resultadoSintaxis.status === 2, `Un error de sintaxis debe clasificarse con código 2, obtuvo ${resultadoSintaxis.status}.`, resultadoSintaxis)

const tokensComentados = ejecutar(verificadorTokens, fixture('tokens-comentados-validos.css'))
exigir(tokensComentados.status === 0, 'Los tokens dentro de comentarios no deben contarse como usos reales.', tokensComentados)

const tokensFaltantesArchivo = fixture('tokens-faltantes.css')
const tokensFaltantes = ejecutar(verificadorTokens, tokensFaltantesArchivo)
exigir(tokensFaltantes.status === 1, 'Un var(--color-*) real sin declaración debía terminar con código 1.', tokensFaltantes)
exigir(tokensFaltantes.stderr.includes(tokensFaltantesArchivo) && tokensFaltantes.stderr.includes('--color-no-declarado'), 'El diagnóstico de token faltante no identifica archivo y token.', tokensFaltantes)

console.log('✓ Canaries: minificado, ENOENT, sintaxis y comentarios se clasifican correctamente.')
