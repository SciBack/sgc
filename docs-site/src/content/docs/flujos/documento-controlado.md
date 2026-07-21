---
title: Documento controlado
description: Prueba funcional completa del flujo Documento controlado.
---

## Quién puede ejecutarlo

Dueño de Proceso, DPGC y Autoridad Aprobadora.

## Precondiciones

Documento con código, versión, responsable y archivo/enlace documental disponible. Usa identificadores ficticios y cuentas separadas cuando intervengan aprobación o cierre.

## Pasos y resultados esperados

1. En estado **Borrador**, inicia sesión como **Dueño de Proceso** y ejecuta **Enviar a revision**. Resultado esperado: el registro queda en **En revision** y la acción aparece en su historial.
2. En estado **En revision**, inicia sesión como **DPGC** y ejecuta **Observar**. Resultado esperado: el registro queda en **Observado** y la acción aparece en su historial.
3. En estado **En revision**, inicia sesión como **DPGC** y ejecuta **Aprobar**. Resultado esperado: el registro queda en **Aprobado** y la acción aparece en su historial.
4. En estado **Observado**, inicia sesión como **Dueño de Proceso** y ejecuta **Corregir**. Resultado esperado: el registro queda en **Borrador** y la acción aparece en su historial.
5. En estado **Aprobado**, inicia sesión como **DPGC** y ejecuta **Observar**. Resultado esperado: el registro queda en **Observado** y la acción aparece en su historial.
6. En estado **Aprobado**, inicia sesión como **Autoridad Aprobadora** y ejecuta **Publicar**. Resultado esperado: el registro queda en **Publicado** y la acción aparece en su historial.
7. En estado **Publicado**, inicia sesión como **DPGC** y ejecuta **Derogar**. Resultado esperado: el registro queda en **Obsoleto** y la acción aparece en su historial.

## Estados por los que pasa

**Borrador** → **En revision** → **Observado** → **Aprobado** → **Publicado** → **Obsoleto**. Las devoluciones o reaperturas se muestran en la tabla, por lo que el recorrido no siempre es lineal.

| Desde | Acción | Hacia | Rol |
|---|---|---|---|
| Borrador | Enviar a revision | En revision | Dueño de Proceso |
| En revision | Observar | Observado | DPGC |
| En revision | Aprobar | Aprobado | DPGC |
| Observado | Corregir | Borrador | Dueño de Proceso |
| Aprobado | Observar | Observado | DPGC |
| Aprobado | Publicar | Publicado | Autoridad Aprobadora |
| Publicado | Derogar | Obsoleto | DPGC |

## Permisos

El actor necesita DocPerm sobre el DocType y el rol exacto de la transición. Las transiciones de control sin autoaprobación deben probarse con una cuenta distinta de quien creó el registro.

## Restricciones

No modifiques el campo de estado directamente. No uses System Manager para simular una decisión funcional. Si el registro está fuera del ámbito de User Permission, debe permanecer invisible o ser rechazado por backend.

## Casos negativos

- Ejecutar la transición con un rol distinto: debe estar ausente o ser rechazada.
- Repetir una acción desde un estado incompatible: el estado no debe cambiar.
- Omitir un dato obligatorio o relación requerida: el guardado debe fallar con mensaje accionable.
- Intentar autoaprobar una transición segregada: debe ser rechazada.

## Evidencia que debe capturarse

Captura del estado anterior, control ejecutado, estado final e historial; URL e identificador ficticio; rol utilizado; mensaje y respuesta HTTP de cada caso negativo. Oculta cookies y datos personales.

## Relación con otros módulos

Mayan/control documental, notificaciones y auditoría de versiones.

## Acciones operativas o configuración adicional

El correo y las tareas periódicas requieren scheduler/servidor de correo configurados. Archivos o integraciones externas requieren sus servicios disponibles; su ausencia no debe reinterpretarse como una transición funcional válida.

## Fuente en código

La definición canónica está registrada en el manifiesto de cobertura y en sgc/setup. No se documentan estados adicionales a los definidos por el workflow actual.

