---
title: Procedimiento
description: Prueba funcional de la elaboración, aprobación y publicación de un procedimiento y su diagrama (ISO 9001 §7.5).
---

## Quién puede ejecutarlo

El **Dueño de Proceso** elabora el procedimiento y lo envía a revisión. La **DPGC** lo revisa, lo aprueba o lo devuelve, y lo publica.

## Precondiciones

El proceso al que pertenece y, si existe, su diagrama BPMN. Usa cuentas separadas: quien crea el procedimiento no lo aprueba.

## Pasos y resultados esperados

1. Crea el procedimiento y adjunta su diagrama. Resultado esperado: queda en **Borrador**.
2. Ejecuta **Enviar a revision**. Resultado esperado: queda en **En revisión**.
3. Como **DPGC**, ejecuta **Aprobar** y luego **Publicar**. Resultado esperado: queda en **Publicado** y aparece en la ficha de su proceso y en el portal público.
4. Para cambiarlo, ejecuta **Nueva version**: vuelve a **Borrador** y pasa otra vez por revisión y aprobación.

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

- **El estado lo cambia el flujo** (menú Acciones), no el formulario.
- Las tareas que salen en el documento y en el PDF de la ficha se leen del diagrama BPMN del procedimiento: no hay una lista aparte que mantener.

## Casos negativos

- Aprobar con la cuenta que creó el procedimiento: debe rechazarse.
- Publicar como Dueño de Proceso: la acción no está disponible.

## Evidencia que debe capturarse

Captura del estado anterior, acción ejecutada, estado final e historial; rol utilizado; mensaje de cada caso negativo. Oculta cookies y datos personales.

## Relación con otros módulos

Ficha de caracterización (lo recoge sola), mapa de procesos, editor y visor BPMN, y el portal público de procesos.

## Fuente en código

`sgc/fixtures/workflow.json` («Procedimiento SGC») y el DocType `sgc/sgc_procesos/doctype/procedimiento/`.
