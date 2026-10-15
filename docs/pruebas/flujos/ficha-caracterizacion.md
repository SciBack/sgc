---
title: Ficha de caracterización
description: Prueba funcional de la elaboración, aprobación y publicación de la ficha de un proceso (ISO 9001 §4.4 y §7.5).
---

## Quién puede ejecutarlo

El **Dueño de Proceso** elabora la ficha y la envía a revisión. La **DPGC** la revisa, la aprueba o la devuelve, y la publica.

## Precondiciones

Un proceso del mapa con **responsable** asignado. Usa cuentas separadas: quien crea la ficha no la aprueba.

## Pasos y resultados esperados

1. Crea la ficha del proceso. Resultado esperado: queda en **Borrador** y recoge sola lo que el sistema ya sabe del proceso: sus procedimientos, documentos, riesgos y subprocesos.
2. Completa objetivo, alcance, recursos, entradas, salidas, indicadores y riesgos, y ejecuta **Enviar a revision**. Resultado esperado: queda en **En revisión** y el sistema sella **Elaborado por**.
3. Como **DPGC**, ejecuta **Aprobar**. Resultado esperado: queda en **Aprobado** y el sistema sella **Aprobado por**.
4. Ejecuta **Publicar**. Resultado esperado: queda en **Publicado**, con fecha de emisión; el PDF se genera y la ficha sale en el portal público de procesos.
5. Para cambiarla, ejecuta **Nueva version**: vuelve a **Borrador** y pasa otra vez por revisión y aprobación.

## Estados por los que pasa

**Borrador** → **En revisión** → **Aprobado** → **Publicado** → **Obsoleto**, con las devoluciones a **Borrador**.

| Desde | Acción | Hacia | Rol |
|---|---|---|---|
| Borrador | Enviar a revision | En revisión | Dueño de Proceso |
| En revisión | Aprobar | Aprobado | DPGC |
| En revisión | Devolver a borrador | Borrador | DPGC |
| Aprobado | Publicar | Publicado | DPGC |
| Aprobado | Devolver a borrador | Borrador | DPGC |
| Publicado | Nueva version | Borrador | Dueño de Proceso, DPGC |
| Publicado | Derogar | Obsoleto | DPGC |

## Permisos

El actor necesita DocPerm sobre el DocType y el rol exacto de la transición. **Aprobar** no admite autoaprobación.

## Restricciones

- **No pasa a revisión, ni se aprueba ni se publica incompleta** (ISO 9001 §4.4.1): exige objetivo, alcance, recursos, responsable del proceso, al menos una entrada, una salida, una actividad o procedimiento, un indicador y un riesgo. El mensaje dice qué falta.
- **El estado lo cambia el flujo** (menú Acciones), no el formulario.
- Las filas que la ficha recoge del sistema no se borran a mano: para que algo deje de salir, se cambia en su origen.

## Casos negativos

- Enviar a revisión una ficha sin indicador o sin responsable del proceso: debe rechazarse y nombrar lo que falta.
- Aprobar con la cuenta que creó la ficha: debe rechazarse.
- Publicar como Dueño de Proceso: la acción no está disponible.

## Evidencia que debe capturarse

Captura del estado anterior, acción ejecutada, estado final e historial; rol utilizado; mensaje de cada caso negativo; el PDF generado. Oculta cookies y datos personales.

## Relación con otros módulos

Mapa de procesos (el proceso y su responsable), procedimientos, indicadores (la ficha los declara), documentos y riesgos del proceso, y el portal público de procesos.

## Fuente en código

`sgc/fixtures/workflow.json` («Ficha Caracterizacion SGC») y el controlador `sgc/sgc_procesos/doctype/ficha_caracterizacion_proceso/`.
