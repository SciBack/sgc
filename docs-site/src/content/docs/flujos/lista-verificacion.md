---
title: Lista de verificación de auditoría
description: Prueba funcional del documento de trabajo del auditor (ISO 19011 §6.3.4) y de la generación de hallazgos.
---

## Qué es

La **lista de verificación** es el documento de trabajo del auditor: una serie de puntos a comprobar, cada uno con su resultado (conforme, no conforme, observación o no aplica) y la evidencia vista. De ahí salen los hallazgos. Una lista **sin auditoría** es una **plantilla**: guarda las preguntas que se repiten cada año.

## Quién puede ejecutarlo

El **Auditor Interno** aplica y completa la lista y genera los hallazgos. La **DPGC** y el **Analista de Calidad** mantienen las plantillas. El resto de roles la leen.

## Precondiciones

Una auditoría que no esté **Cerrada**. Para generar hallazgos, la cuenta debe poder crear hallazgos de auditoría (rol Auditor Interno).

## Pasos y resultados esperados

1. Crea una lista **sin auditoría** con título y puntos a verificar. Resultado esperado: queda como plantilla, en **Borrador**.
2. En la plantilla, pulsa **Usar en una auditoría** y elige la auditoría. Resultado esperado: se abre una lista nueva con las mismas preguntas, los resultados vacíos, el proceso y la unidad de la auditoría, y **Creada desde** apuntando a la plantilla.
3. Pasa la lista a **En ejecucion**. Resultado esperado: se fija la fecha de aplicación.
4. Marca el resultado de cada punto y anota la evidencia vista. Pasa a **Completada**. Resultado esperado: el sistema sella **Completada por** y la fecha.
5. Pulsa **Generar hallazgos**. Resultado esperado: un hallazgo de auditoría por cada punto **No conforme** (tipo no conformidad menor, que el auditor ajusta) u **Observación** (tipo observación), con el criterio, la pregunta y la evidencia vista como descripción inicial y la evidencia vinculada; cada punto queda enlazado a su hallazgo.

## Casos negativos

- Poner en ejecución una plantilla (lista sin auditoría): debe rechazarse.
- Guardar un punto sin pregunta: debe rechazarse.
- Completar con puntos sin resultado: debe rechazarse diciendo cuántos faltan y cuáles.
- Completar una lista sin puntos: debe rechazarse.
- Generar hallazgos por segunda vez: no debe duplicar; informa cuántos ya estaban generados.
- Generar hallazgos desde una plantilla: debe rechazarse.
- Con la auditoría **Cerrada**: modificar, crear o borrar su lista, o generar hallazgos, debe rechazarse.

## Evidencia que debe capturarse

Captura de la plantilla, la lista aplicada con sus resultados, el aviso de hallazgos generados y los hallazgos resultantes; rol utilizado; mensaje de cada caso negativo. Oculta cookies y datos personales.

## Relación con otros módulos

Auditoría (la lista pertenece a una), hallazgos de auditoría (se generan desde ella) y, a través de ellos, no conformidades y CAPA.

## Fuente en código

`sgc/sgc_auditoria/doctype/lista_verificacion/` (controlador y botones) e `item_verificacion/` (los puntos).
