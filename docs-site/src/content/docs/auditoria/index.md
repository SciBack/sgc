---
title: Manual del módulo de Auditoría
description: Planificar el programa anual, ejecutar cada auditoría con su lista de verificación, registrar y escalar hallazgos, y aprobar y distribuir el informe.
sidebar:
  order: 1
---

Este manual es para quien audita y para quien gobierna la auditoría: los auditores internos y la
dirección de calidad. Sigue el orden de la norma ISO 19011: se aprueba el programa del año, se
ejecuta cada auditoría, se registran los hallazgos, se emite el informe y se cierra.

:::tip[La regla de oro]
**Nadie audita lo suyo ni aprueba lo suyo.** El equipo no puede incluir al responsable del proceso
auditado, y el informe no lo aprueba quien lo emitió ni nadie del equipo. El sistema lo impide,
no hace falta vigilarlo.
:::

## 1. El área de Auditoría

**Cómo entrar:** arriba a la izquierda, pulse el nombre del área en la que está (el que lleva
la flecha ⌄) → **Módulos** → **Auditoría**.

![Menú «Módulos» con Auditoría resaltado](captura:navegacion-auditoria)

Se abre la portada del área, y el menú de la izquierda muestra sus entradas:

![Portada del área de Auditoría](captura:auditoria-portada)

| Entrada | Qué es |
|---|---|
| **Portada del área** | Programas por aprobar, auditorías en ejecución, informes por aprobar y hallazgos abiertos |
| **Programas de auditoría** | El plan anual: qué se audita y cuándo |
| **Auditorías** | Cada auditoría, con su equipo, criterios y plan de actividades |
| **Listas de verificación** | Los puntos a comprobar en cada auditoría, y las plantillas reutilizables |
| **Hallazgos de auditoría** | Lo que encontró cada auditoría |
| **Informes de auditoría** | El informe de cada auditoría, con su aprobación |
| **Resultados de auditoría** | Los hallazgos de todas las auditorías, filtrables |

## 2. El programa anual

1. **Programas de auditoría → + Agregar.** Lo crea el auditor interno. Asigne un **responsable**
   del programa y enlace las auditorías del año.
2. **Aprobar programa:** lo hace la dirección de calidad, y no quien lo creó. Exige responsable.
3. **Iniciar ejecucion:** el auditor interno, cuando empiezan las auditorías.
4. **Cerrar programa:** la dirección de calidad, cuando **todas sus auditorías han concluido**. Si
   falta alguna, el sistema dice cuántas y cuáles.

El programa se imprime como **Plan Anual de Auditoría** desde el menú **Imprimir**.

## 3. La auditoría

**Crear:** **Auditorías → + Agregar**, o **Nueva auditoría** en la portada.

![Formulario de una auditoría nueva](captura:auditoria-nueva)

| Estado | Quién actúa | Botón | Qué exige |
|---|---|---|---|
| Planificada | Auditor interno | *Iniciar auditoria* | El **equipo auditor**, independiente, y los **criterios** de auditoría |
| En ejecución | Auditor interno | *Marcar ejecutada* | — |
| Ejecutada | Auditor interno | *Emitir informe* o *Devolver a ejecucion* | El **informe** vinculado, que sea de esta auditoría |
| Informe emitido | Dirección de calidad | *Cerrar auditoria* o *Reabrir* | El informe **aprobado** |

**El equipo tiene que ser independiente:** al menos un miembro debe ser ajeno al área auditada, y
el **responsable del proceso auditado no puede formar parte** del equipo. Quien cierra la
auditoría no puede ser quien la creó.

### El plan de actividades

La tabla **Plan de actividades** desglosa la auditoría: qué se hace, qué día y quién. Cada
responsable recibe **una sola tarea** en sus pendientes, que vence en su próxima actividad y la
nombra.

- Al marcar una actividad como **Realizada**, el sistema rellena **Realizada por** y **Realizada
  el**, y la tarea pasa a la siguiente actividad de esa persona.
- Cuando no le quedan actividades, su tarea se **cierra**.
- Si se quita a alguien del plan, o se cierra la auditoría con actividades sin hacer, su tarea
  se **cancela**: cerrar no convierte en hecho lo pendiente.

Cerrar la tarea desde la lista de pendientes no marca la actividad: se marca en la auditoría.

## 4. La lista de verificación

Es el documento de trabajo del auditor: una serie de puntos a comprobar, cada uno con su
**resultado** (conforme, no conforme, observación o no aplica) y la **evidencia** vista.

- **Una lista sin auditoría es una plantilla:** guarda las preguntas que se repiten cada año. La
  dirección de calidad y su analista las mantienen.
- **Usar una plantilla:** ábrala y pulse **Usar en una auditoría**. Se crea una copia con los
  mismos puntos, enlazada a la auditoría que elija y con los resultados en blanco.
- **Completarla:** cada punto necesita su pregunta y su resultado. Si falta alguno, el sistema dice
  qué filas. Al completarla, el sistema sella quién lo hizo y cuándo.
- **Generar hallazgos:** crea un hallazgo de auditoría por cada punto *no conforme* u
  *observación*, una sola vez por punto. Un punto no conforme nace como **no conformidad menor**:
  la gravedad la ajusta el auditor en el hallazgo, porque la lista solo sabe que no se cumple.

Cuando la auditoría se cierra, su lista queda bloqueada.

## 5. Los hallazgos de auditoría

Se crean con **Generar hallazgos** desde la lista, o a mano en **Hallazgos de auditoría → + Agregar**.
Cada uno pertenece a una auditoría y tiene un **tipo**: no conformidad mayor o menor, observación,
oportunidad de mejora, conformidad o fortaleza.

| Estado | Quién actúa | Botón |
|---|---|---|
| Abierto | Auditor interno | *Escalar a NC* |
| Abierto o Escalado a NC | Dirección de calidad | *Cerrar* |
| Cerrado | Dirección de calidad | *Reabrir* o *Reabrir escalado* |

**Escalar a NC** crea la no conformidad con la descripción, el criterio, la unidad, el proceso y el
programa del hallazgo, y deja los dos enlazados. A partir de ahí se trata en el [módulo de Mejora
continua](../mejora-continua/). Una conformidad o una fortaleza no escalan.

**Para cerrar un hallazgo:**

- si es una **no conformidad** (mayor o menor), tiene que haber **escalado** antes: la reacción
  vive en la no conformidad;
- el **informe** de su auditoría tiene que estar **aprobado**;
- no lo cierra quien lo registró.

**Para reabrir:** un hallazgo que escaló se reabre con **Reabrir escalado**, que lo devuelve a
*Escalado a NC*. *Reabrir* es para los que nunca escalaron.

## 6. El informe de auditoría

| Estado | Quién actúa | Botón | Qué exige |
|---|---|---|---|
| Borrador | Auditor interno | *Enviar a revision* | El resumen ejecutivo o las conclusiones |
| En revisión | Dirección de calidad | *Aprobar* o *Devolver a borrador* | Para devolver: explicar en las observaciones qué corregir |
| Aprobado | Dirección de calidad | *Distribuir* | Indicar a quién se distribuye |

- **No lo aprueba** quien lo emitió, quien lo creó ni nadie del equipo auditor de esa auditoría.
- **Lo aprobado es lo que se distribuye:** al aprobarse, el resumen, las conclusiones, el adjunto y
  los contadores quedan **congelados**.

## 7. Resultados de auditoría

El informe **Resultados de auditoría** reúne los hallazgos de todas las auditorías. Se filtra por
auditoría, tipo de hallazgo y proceso, y con **Solo no conformidades sin escalar** muestra las que
todavía no pasaron a mejora continua: lo primero que revisar antes de cerrar.

## Quién puede qué

| Acción | Dirección de calidad | Auditor interno |
|---|---|---|
| Crear el programa | — | Sí |
| Aprobar el programa | Sí, si no lo creó | — |
| Iniciar la ejecución del programa | — | Sí |
| Crear, iniciar y ejecutar una auditoría | — | Sí |
| Cerrar la auditoría y el programa | Sí, si no los creó | — |
| Mantener plantillas de listas | Sí | — |
| Completar listas y generar hallazgos | — | Sí |
| Escalar un hallazgo a no conformidad | — | Sí |
| Cerrar y reabrir hallazgos | Sí | — |
| Redactar y enviar el informe | — | Sí |
| Aprobar y distribuir el informe | Sí, si no está en el equipo | — |

Los demás roles consultan las auditorías, los hallazgos y los informes.
