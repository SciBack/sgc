---
title: Manual del módulo de Indicadores
description: Definir indicadores y sus fichas, registrar mediciones con su análisis, leer el semáforo, atender alertas y consultar los informes.
sidebar:
  order: 1
---

Este manual es para quien define y mide indicadores: la dirección de calidad, los responsables de
cada indicador y quienes administran los datos. Sigue el orden en que se trabaja: se define el
indicador, se le hace su ficha, se mide cada periodo, se analiza el resultado y se atiende lo que
sale mal.

:::tip[La regla de oro]
Un indicador sin **meta** no se puede juzgar: se puede registrar su valor, pero no decir si está
bien o mal. Por eso el semáforo queda **vacío** mientras la ficha no declare su meta. Un verde
falso es peor que un hueco.
:::

## 1. El área de Indicadores

**Cómo entrar:** arriba a la izquierda, pulse el nombre del área en la que está (el que lleva
la flecha ⌄) → **Módulos** → **Indicadores**.

![Menú «Módulos» con Indicadores resaltado](captura:navegacion-indicadores)

Se abre la portada del área, y el menú de la izquierda muestra sus entradas:

![Portada del área de Indicadores](captura:indicadores-portada)

| Entrada | Qué es |
|---|---|
| **Portada del área** | Lo que toca medir, las alertas abiertas y las mediciones en rojo |
| **Indicadores** | El catálogo: qué se mide |
| **Fichas de indicador** | Cómo se mide cada uno: fórmula, meta, frecuencia y responsable |
| **Mediciones** | Cada valor registrado, por periodo |
| **Tableros de indicadores** | Grupos de indicadores pensados para un público concreto |
| **Alertas de indicador** | Avisos sobre mediciones que necesitan atención |
| **Indicadores de acreditación** | Los indicadores de un marco normativo y su cumplimiento |
| **Indicadores agrupados** | El estado agrupado por categoría, marco o proceso |

## 2. El indicador

**Indicadores → + Agregar.** Lleva **código** y **nombre** (obligatorios), la **categoría**
(acreditación, gestión, proceso, satisfacción u otra), el **marco normativo** y el **proceso** al
que pertenece, y los **criterios** del marco a los que tributa. Lo crean la dirección de calidad,
su analista y quien administra los datos.

## 3. La ficha del indicador

La ficha dice **cómo** se mide. **Fichas de indicador → + Agregar**, y complete:

![Ficha de un indicador](captura:indicadores-ficha)

| Grupo | Campos |
|---|---|
| **Qué mide** | Indicador, objetivo, alcance (institucional, campus, facultad, escuela, área o proceso) |
| **Cómo se calcula** | Tipo de valor, fórmula, numerador, denominador, variables y unidad |
| **Contra qué se compara** | Línea base, **valor referencial** (la meta), margen de error, sentido y modo de evaluación |
| **Cuándo y quién** | Frecuencia, **responsable**, próxima medición y días de aviso |
| **De dónde sale el dato** | Fuente de dato y fuente autoritativa |

### La meta y el semáforo

El color de cada medición se calcula solo, a partir de la ficha:

- **Sentido:** si *mayor es mejor* (una tasa de graduación) o *menor es mejor* (una tasa de
  deserción). Sin declararlo, el color saldría al revés.
- **Modo de evaluación:**
  - **Umbral fijo:** se compara con el **valor referencial**.
  - **Evolución respecto al periodo anterior:** basta con mejorar frente al periodo anterior.
- **Margen de error:** un porcentaje de la meta. Quedar dentro del margen no es cumplir, pero
  tampoco es fallar: es **ámbar**. Sin margen no hay ámbar, solo verde o rojo.

Si falta la ficha, la meta o el periodo anterior para comparar, el semáforo queda vacío.

### Participación de las áreas

Si el indicador depende de varias áreas, la tabla **Participación de las áreas** dice cuánto aporta
cada una. Cada área aparece una vez y los pesos tienen que sumar **100 %**; si no, el sistema no
deja guardar y dice cuánto suman.

## 4. Registrar una medición

![Una medición con su semáforo calculado](captura:indicadores-medicion)

1. **Mediciones → + Agregar**, o **Registrar medición** en la portada.
2. Indique el **indicador**, el **periodo académico** y, si aplica, el programa y sede o la unidad.
3. Escriba el **valor** (numérico o en texto) y la **fecha**.
4. Si la ficha lo exige, escriba el **análisis**: qué explica el resultado y qué se hará.
5. **Guardar.** El semáforo se calcula solo.

**Quién registra:** el **responsable de la ficha** del indicador, la dirección de calidad o quien
administra los datos. Otra persona no puede registrar mediciones de ese indicador.

**Lo que no se puede tocar:**

- una medición de un **periodo cerrado**;
- una medición que llegó **por la integración con el almacén de datos**: la administra esa
  integración.

En los dos casos sí se puede escribir el **análisis**, porque no cambia el valor.

### El análisis de cada periodo

Si la ficha marca **Exigir el análisis de cada medición**:

- una medición tecleada **no se guarda sin análisis**;
- una medición que llega del almacén de datos se guarda y deja al responsable una **tarea de
  análisis**, que se cierra sola al escribirlo.

**Analizado por** y la fecha del análisis los **sella el sistema**.

## 5. Avisos de medición

- **Antes de la fecha:** los **días de aviso** de la ficha (7 por defecto) antes de la próxima
  medición, el responsable recibe un correo.
- **Al registrar:** la próxima medición **avanza sola** un periodo según la frecuencia (mensual,
  trimestral, semestral o anual). Para la frecuencia *por promoción* se fija a mano.
- **Si se pasa la fecha:** el día siguiente sin valor nuevo, se avisa al responsable y a la
  dirección de calidad de que la **medición está vencida**.

## 6. Alertas de indicador

Una alerta es un aviso sobre una medición que necesita atención. Las crea el sistema cuando una
medición que llega del almacén de datos **incumple una regla de validación**, y la dirección de
calidad puede registrarlas a mano en los demás casos (meta no alcanzada, sin medición en el
periodo, medición vencida).

Cada alerta nueva avisa por correo a su **responsable** o, si no tiene, a la dirección de calidad.

| Estado | Qué significa |
|---|---|
| Abierta | Nadie la ha atendido todavía |
| En atención | Alguien está trabajando en ella |
| Resuelta | Se atendió; puede enlazar la **acción de mejora** que la resolvió |
| Descartada | No requería acción. **Exige justificarlo** |

## 7. Tableros

Un tablero agrupa indicadores para un público concreto. Lleva nombre, **rol destinatario**,
**ámbito** (institucional, una unidad o un programa y sede), los **indicadores** que incluye y el
periodo por defecto. Pasa de *Borrador* a *Publicado* cuando está listo, y a *Archivado* cuando ya
no se usa. Los crea la dirección de calidad.

## 8. Los informes

- **Indicadores de acreditación:** cada medición con su valor, la meta y si cumple, por programa y
  sede y periodo, con el total de los que cumplen y no cumplen. Se filtra por fuente, periodo,
  programa e indicador, y puede mostrar **solo los incumplidos**.
- **Indicadores agrupados:** agrupa por **categoría**, **marco normativo** o **proceso**. Para
  cada grupo dice cuántos indicadores tiene, cuántos tienen medición, cómo está la última (verde,
  ámbar o rojo) y el porcentaje en verde, con un gráfico. Se puede limitar a un periodo
  académico.

## Quién puede qué

| Acción | Dirección de calidad | Administra los datos | Responsable del indicador | Dueño de proceso |
|---|---|---|---|---|
| Crear indicadores y fichas | Sí | Sí | — | — |
| Registrar mediciones | Sí | Sí | Sí, de sus indicadores | Sí, si es el responsable |
| Escribir el análisis | Sí | Sí | Sí | Sí, si es el responsable |
| Crear y atender alertas | Sí | — | Recibe el aviso | — |
| Crear tableros | Sí | — | — | — |

Los demás roles consultan los indicadores, las mediciones y los informes.
