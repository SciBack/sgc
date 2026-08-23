---
title: Autoevaluación de acreditación
description: Flujo end-to-end desde la carga del marco normativo hasta la vigencia de acreditación oficial.
---

Este es el flujo central del sistema: llevar un programa académico desde la carga del
marco normativo hasta la vigencia de acreditación oficial.

## El principio: el motor propone, el humano confirma

En cada paso hay dos campos: uno que **calcula el sistema** (siempre de solo lectura,
nombrado `_propuesto`) y uno **oficial** que solo un humano autorizado puede fijar. El
motor (`scoring.py`) nunca escribe el campo oficial.

## Paso 1 — Valorar los criterios

Para cada criterio normativo de un estándar, el comité registra en **Valoracion
Criterio** su juicio (`cumple`):

- `Cumple`
- `Cumple parcial`
- `No cumple`
- `No aplica` (cuenta como criterio revisado, no resta avance)

Cada vez que se guarda una Valoracion Criterio, el sistema recalcula automáticamente
el `nivel_propuesto` del estándar al que pertenece ese criterio.

## Paso 2 — El motor propone el nivel del estándar

Regla (por estándar, sobre sus criterios hijos):

| Condición | `nivel_propuesto` |
|---|---|
| Algún criterio sin valorar | *(vacío — incompleto)* |
| Algún criterio `No cumple` | **NL** — No Logrado |
| Algún criterio `Cumple parcial` (y ninguno `No cumple`) | **L** — Logrado |
| Todos los criterios `Cumple` | **LP** — Logrado Plenamente (propuesto) |

:::note[LP no es mecánico]
Aunque todos los criterios cumplan, confirmar LP exige que el comité revise la
evolución de los indicadores asociados (±3%, 4 semestres) antes de aceptar la
propuesta — no basta con el cálculo automático.
:::

## Paso 3 — El comité confirma el nivel oficial

El comité usa `confirmar_nivel(autoevaluacion, estandar, nivel_sigla, comentario)`:

- Puede **aceptar** la propuesta tal cual, o hacer un **override** justificado (el
  sistema detecta la diferencia y registra la razón en `justificacion` si no se
  provee una explícita).
- Fija `nivel` (el campo oficial, protegido en permlevel 1) y marca `confirmado=1`.
- Es idempotente: reconfirmar el mismo valor no rompe nada.

Para cerrar rápido cuando el comité acepta todas las propuestas del motor, existe
`confirmar_todos_propuestos(autoevaluacion)`, que confirma en bloque cada estándar con
propuesta pendiente.

## Paso 4 — Cerrar la autoevaluación: promover la vigencia oficial

Una vez confirmados **todos los estándares del marco**, `finalizar_vigencia(autoevaluacion)`:

1. Verifica que estén todos confirmados (si faltan, devuelve cuántos y no toca nada).
   El total sale del marco cargado, no de una constante: son 10 en el Modelo de
   Acreditación para Programas de Estudios y 9 en el Institucional.
2. Recalcula la vigencia sobre los niveles **confirmados** (no los propuestos), según la
   Tabla 9 del modelo:

   | Condición | Vigencia |
   |---|---|
   | Algún estándar en NL | En proceso de acreditación |
   | Resto (todos L, o combinación L/LP) | Acreditado 3 años |
   | Todos los estándares en LP | Acreditado 6 años |
   | Todos en LP **y** puntaje suficiente de la Tabla 10 | Acreditado 8 años |

3. Escribe el resultado oficial en `Autoevaluacion.resultado_vigencia`.

:::caution[El tramo de 8 años no lo produce el sistema]
La Tabla 9 pide, para 8 años, todos los estándares en LP **más** el puntaje de la
Tabla 10 (criterios de excelencia): **16 puntos en el modelo de programas y 20 en el
institucional**. Hoy nadie calcula `Autoevaluacion.puntaje_excelencia` y los criterios
de la Tabla 10 no están cargados como elementos del marco, así que el techo real del
motor son **6 años**. La opción existe en el campo oficial porque la norma la
contempla, no porque el motor la proponga — ver
[Módulo Núcleo](../../modulos/nucleo/).
:::

## Paso 5 — Generar el informe

`informe.generar_pdf(autoevaluacion)` consolida la autoevaluación completa (niveles
confirmados, criterios, evidencias vinculadas vía Trazabilidad) y genera el PDF de
acreditación con el Print Format oficial, usando el motor Chrome de Frappe.

## Ver evidencias mientras se valora

Al abrir el detalle de un criterio en la SPA, el comité ve las evidencias ya
vinculadas a ese criterio (consulta inversa sobre `Trazabilidad`) sin salir de la
pantalla de valoración — ver [Evidencias y trazabilidad](../evidencias-trazabilidad/).

## Si un criterio no cumple: generar un hallazgo

Cuando `Valoracion Criterio.cumple` es `No cumple` o `Cumple parcial`, ese juicio
puede escalar a la cadena de mejora continua — ver
[No conformidades y mejora](../no-conformidades-mejora/).
