---
title: No conformidades y mejora continua (CAPA)
description: Cadena Hallazgo → No Conformidad → Plan de Mejora → Acción de Mejora.
---

Cadena única de mejora continua (ISO 9001 §10): **Hallazgo → No Conformidad → Plan de
Mejora → Acción de Mejora**. Es la misma cadena sin importar si el origen es una
autoevaluación, una auditoría interna o una supervisión externa.

## Paso 1 — Generar el hallazgo

`capa.generar_hallazgo(valoracion_criterio)` crea un **Hallazgo** cuando el juicio de
una Valoracion Criterio es `No cumple` o `Cumple parcial`:

| Juicio | Tipo de Hallazgo |
|---|---|
| `No cumple` | Debilidad |
| `Cumple parcial` | Oportunidad de mejora |

Es **idempotente**: si ya existe un Hallazgo para esa misma autoevaluación + criterio,
lo devuelve en vez de duplicar.

:::tip
Un Hallazgo también puede originarse en una auditoría interna
(`Hallazgo Auditoria`, ver [módulo Auditoría](/modulos/auditoria/)) — mismo
concepto, distinto punto de entrada.
:::

## Paso 2 — Escalar a No Conformidad

`capa.escalar_a_no_conformidad(hallazgo)` crea una **No Conformidad** con origen
polimórfico (`origen_doctype`, `origen_id`, `origen_tipo`), copiando criterio,
programa/sede y unidad orgánica del hallazgo:

| Tipo de Hallazgo | Tipo de No Conformidad |
|---|---|
| Oportunidad de mejora | Oportunidad de mejora |
| Debilidad | No conformidad menor |

Marca el Hallazgo original como `escalado_a_nc=1` y lo enlaza a la NC creada. También
es idempotente: si el hallazgo ya fue escalado, devuelve la NC existente.

### Validaciones incrementales de la No Conformidad

El controlador de `No Conformidad` valida por etapa:

- Una NC **mayor** exige análisis de causa antes de avanzar.
- Pasar a verificación exige plazo comprometido + acción definida.
- Cerrar exige evidencia de cierre + verificador asignado.

## Paso 3 — Crear el Plan de Mejora

`capa.crear_plan(no_conformidad)` crea un **Plan Mejora** (también de origen
polimórfico) enlazado a la NC. Opcionalmente crea una primera **Accion Mejora** de
ejemplo (`tipo=Correctiva`) para no dejar el plan vacío.

## Paso 4 — Ejecutar y cerrar acciones

Cada **Accion Mejora** del plan lleva su propio `avance_pct`, `fecha_compromiso` y
semáforo. El avance del Plan se recalcula por rollup de sus acciones — al borrar una
acción, el plan **excluye** esa acción del recálculo (no la sigue contando).

## Vencimientos

Reglas de notificación ("Days Before") avisan por el canal interno de Frappe (sin
requerir SMTP) cuando se acerca la fecha de vencimiento de un Documento Controlado,
una Evidencia, una Acción de Mejora o un Plan de Mejora.
