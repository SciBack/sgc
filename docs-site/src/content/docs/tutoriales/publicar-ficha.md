---
title: Publicar una ficha de caracterización
description: Tutorial de principio a fin para llevar la ficha de un proceso desde cero hasta el portal público, sin quedarse a medio camino.
sidebar:
  order: 1
---

**Objetivo:** que la ficha de caracterización de un proceso salga publicada en el portal de
procesos.

**Quiénes intervienen:** el **dueño del proceso**, que la elabora, y la **dirección de calidad**,
que la aprueba y la publica. Son dos personas distintas: quien crea la ficha no puede aprobarla.

**Tiempo:** depende de cuánto falte; lo mecánico son unos minutos.

:::caution[Lo que más detiene una ficha]
La ficha **no pasa a revisión** si le falta cualquiera de los requisitos del paso 1. Los dos que
más se olvidan no están en la ficha sino **fuera de ella**: el **responsable del proceso** y **al
menos un riesgo** registrado del proceso. Revíselos antes de empezar.
:::

## Paso 1. Comprobar lo que la ficha va a necesitar

La norma ISO 9001 (§4.4.1) pide que la caracterización de un proceso tenga todo esto. El sistema lo
comprueba al enviarla a revisión:

| Requisito | Dónde se completa |
|---|---|
| Un **responsable** en el proceso | En el proceso: **Procesos → Mapa de procesos**, campo *Responsable (dueño de proceso)* |
| Al menos un **procedimiento** | **Procesos → Procedimientos**, con el proceso indicado. La ficha lo trae sola |
| Al menos un **riesgo** | **Riesgos → Nuevo riesgo**, con el proceso indicado. La ficha lo trae sola |
| Al menos un **indicador** | En la ficha. Debe ser un indicador de desempeño del proceso |
| El **objetivo**, el **alcance** y los **recursos** | En la ficha |
| Al menos una **entrada** y una **salida** | En la ficha |

Si falta el responsable del proceso, pídaselo a la dirección de calidad: sin él, además, los avisos
del proceso no llegan a nadie.

## Paso 2. Crear la ficha (dueño del proceso)

![Una ficha de caracterización en borrador](captura:procesos-ficha)

1. **Procesos → Fichas de caracterización → + Agregar**.
2. Elija el **proceso** y pulse **Guardar**.
3. Al guardar, la ficha **trae sola** lo que el sistema ya sabe del proceso: sus procedimientos, sus
   documentos, sus riesgos y sus subprocesos. Compruebe que aparecen; si falta alguno, es que no
   está registrado con ese proceso.

## Paso 3. Completar lo que es de la ficha

Escriba el **objetivo**, el **alcance**, los **requisitos aplicables** y los **recursos**; añada las
**entradas** y **salidas** (qué recibe el proceso y qué entrega, y a quién), los **indicadores** y
los **registros**. Guarde.

## Paso 4. Enviar a revisión (dueño del proceso)

Pulse **Enviar a revision**.

- **Si pasa:** la ficha queda *En revisión* y la dirección de calidad la ve en *Esperan mi
  decisión*.
- **Si no pasa:** el sistema dice exactamente qué falta, por ejemplo «le falta: un responsable en
  el proceso, al menos un riesgo». Vuelva al paso 1 con esa lista.

## Paso 5. Aprobar y publicar (dirección de calidad)

1. Abra la ficha y revísela.
2. Si hay que corregir algo, pulse **Devolver a borrador**: vuelve al dueño.
3. Si está bien, pulse **Aprobar** y después **Publicar**.

El sistema **sella** quién la elaboró, quién la aprobó y la fecha de emisión: no se escriben a
mano.

## Paso 6. Comprobar el resultado

- La ficha está en estado **Publicado**.
- En el menú **Imprimir** sale en PDF con el formato institucional.
- En el **portal público de procesos** aparece la ficha del proceso. Recuerde que el portal solo
  muestra los procesos **Vigentes**: si el proceso sigue en borrador, la ficha no se verá allí.

## ¿Y para cambiarla después?

Una ficha publicada no se edita encima. El dueño o la dirección de calidad pulsan **Nueva
version**: vuelve a borrador con la versión siguiente y repite los pasos 3 a 5. Más detalle en el
[manual de Procesos](../../procesos/).

:::caution[Mientras se prepara la nueva versión, no se ve en el portal]
La nueva versión es la **misma ficha** vuelta a borrador, y el portal solo muestra fichas
publicadas. Desde que se pulsa *Nueva version* hasta que se publica otra vez, **el proceso queda
sin ficha en el portal**. Prepare el cambio con todo listo para que ese hueco dure lo mínimo.
:::
