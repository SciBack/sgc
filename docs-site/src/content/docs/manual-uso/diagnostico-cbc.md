---
title: Diagnóstico de Condiciones Básicas de Calidad (CBC)
description: Cómo se evalúan y consolidan las 8 CBC exigidas por SUNEDU.
---

Las **8 Condiciones Básicas de Calidad** exigidas por SUNEDU son, en el modelo de
datos, un `Elemento Marco` de tipo `Estandar` dentro del marco normativo
`CBC-SUNEDU-2026` (8 condiciones `CBC-I`..`CBC-VIII` + sus componentes/criterios).
Es el **mismo árbol normativo** que usa la autoevaluación de acreditación — solo
cambia qué marco se referencia.

## Paso 1 — Crear el Informe Cumplimiento del año

El DocType **Informe Cumplimiento** tiene autoname `IAC-{año}` — **uno por año**. Al
guardarlo por primera vez:

- Si la tabla hija `condiciones` (child `Cumplimiento CBC`) está vacía, el sistema la
  **auto-puebla** con las 8 CBC del marco.

## Paso 2 — Evaluar cada condición

Para cada una de las 8 filas de `Cumplimiento CBC`, se registra si la institución
**cumple**, **cumple parcialmente** o **no cumple**, con su justificación. **Toda CBC
parcial o no cumplida exige justificación** — el sistema la bloquea si falta.

## Paso 3 — Semáforo consolidado

El informe consolida automáticamente los conteos (`n_cumple`, `n_parcial`,
`n_no_cumple`) y calcula un **semáforo** (campo read-only `semaforo`):

| Condición | Semáforo |
|---|---|
| Alguna condición No cumple | 🔴 Rojo |
| Ninguna No cumple, pero alguna Parcial | 🟡 Ámbar |
| Todas Cumple | 🟢 Verde |

## Paso 4 — Presentar a SUNEDU

El estado "Presentado a SUNEDU" está **bloqueado** mientras quede alguna CBC sin
evaluar — evita presentar un diagnóstico incompleto.

## Paso 5 — Generar el informe PDF

El informe (`Diagnostico CBC SUNEDU`) se genera con el mismo motor Chrome que el
informe de acreditación: portada institucional, semáforo global, resumen por conteo
de color, tabla de las 8 condiciones con su badge de estado y justificación, y firma
de la autoridad correspondiente.

## Relación con el resto del sistema

Una condición marcada No cumple o Parcial es candidata a generar un
[Hallazgo](../no-conformidades-mejora/) igual que un criterio de autoevaluación —
ambos comparten el mismo árbol `Elemento Marco` y el mismo flujo CAPA.
