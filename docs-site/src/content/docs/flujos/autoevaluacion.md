---
title: Autoevaluación
description: Prueba funcional completa del flujo Autoevaluación.
---

## Quién puede ejecutarlo

Responsable de Calidad de Programa; DPGC para consolidar/cerrar.

## Precondiciones

Marco Normativo, Programa Sede y periodo configurados; dos cuentas separadas para segregación. Usa identificadores ficticios y cuentas separadas cuando intervengan aprobación o cierre.

## Pasos y resultados esperados

1. En estado **Planificada**, inicia sesión como **Responsable de Calidad de Programa** y ejecuta **Iniciar evaluacion**. Resultado esperado: el registro queda en **En curso** y la acción aparece en su historial.
2. En estado **En curso**, inicia sesión como **Responsable de Calidad de Programa** y ejecuta **Enviar a revision**. Resultado esperado: el registro queda en **En revision** y la acción aparece en su historial.
3. En estado **En revision**, inicia sesión como **DPGC** y ejecuta **Devolver a evaluacion**. Resultado esperado: el registro queda en **En curso** y la acción aparece en su historial.
4. En estado **En revision**, inicia sesión como **DPGC** y ejecuta **Consolidar**. Resultado esperado: el registro queda en **Consolidada** y la acción aparece en su historial.
5. En estado **Consolidada**, inicia sesión como **DPGC** y ejecuta **Cerrar**. Resultado esperado: el registro queda en **Cerrada** y la acción aparece en su historial.

## Estados por los que pasa

**Planificada** → **En curso** → **En revision** → **Consolidada** → **Cerrada**. Las devoluciones o reaperturas se muestran en la tabla, por lo que el recorrido no siempre es lineal.

| Desde | Acción | Hacia | Rol |
|---|---|---|---|
| Planificada | Iniciar evaluacion | En curso | Responsable de Calidad de Programa |
| En curso | Enviar a revision | En revision | Responsable de Calidad de Programa |
| En revision | Devolver a evaluacion | En curso | DPGC |
| En revision | Consolidar | Consolidada | DPGC |
| Consolidada | Cerrar | Cerrada | DPGC |

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

Valoraciones, evidencias, scoring y confirmación de niveles.

## Acciones operativas o configuración adicional

El correo y las tareas periódicas requieren scheduler/servidor de correo configurados. Archivos o integraciones externas requieren sus servicios disponibles; su ausencia no debe reinterpretarse como una transición funcional válida.

## Fuente en código

La definición canónica está registrada en el manifiesto de cobertura y en sgc/setup. No se documentan estados adicionales a los definidos por el workflow actual.

