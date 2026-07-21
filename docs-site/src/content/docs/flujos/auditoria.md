---
title: Auditoría
description: Prueba funcional completa del flujo Auditoría.
---

## Quién puede ejecutarlo

Auditor Interno; DPGC cierra.

## Precondiciones

Programa aprobado/en ejecución, alcance y equipo asignados. Usa identificadores ficticios y cuentas separadas cuando intervengan aprobación o cierre.

## Pasos y resultados esperados

1. En estado **Planificada**, inicia sesión como **Auditor Interno** y ejecuta **Iniciar auditoria**. Resultado esperado: el registro queda en **En ejecucion** y la acción aparece en su historial.
2. En estado **En ejecucion**, inicia sesión como **Auditor Interno** y ejecuta **Marcar ejecutada**. Resultado esperado: el registro queda en **Ejecutada** y la acción aparece en su historial.
3. En estado **Ejecutada**, inicia sesión como **Auditor Interno** y ejecuta **Emitir informe**. Resultado esperado: el registro queda en **Informe emitido** y la acción aparece en su historial.
4. En estado **Ejecutada**, inicia sesión como **Auditor Interno** y ejecuta **Devolver a ejecucion**. Resultado esperado: el registro queda en **En ejecucion** y la acción aparece en su historial.
5. En estado **Informe emitido**, inicia sesión como **DPGC** y ejecuta **Cerrar auditoria**. Resultado esperado: el registro queda en **Cerrada** y la acción aparece en su historial.
6. En estado **Informe emitido**, inicia sesión como **DPGC** y ejecuta **Reabrir**. Resultado esperado: el registro queda en **Ejecutada** y la acción aparece en su historial.

## Estados por los que pasa

**Planificada** → **En ejecucion** → **Ejecutada** → **Informe emitido** → **Cerrada**. Las devoluciones o reaperturas se muestran en la tabla, por lo que el recorrido no siempre es lineal.

| Desde | Acción | Hacia | Rol |
|---|---|---|---|
| Planificada | Iniciar auditoria | En ejecucion | Auditor Interno |
| En ejecucion | Marcar ejecutada | Ejecutada | Auditor Interno |
| Ejecutada | Emitir informe | Informe emitido | Auditor Interno |
| Ejecutada | Devolver a ejecucion | En ejecucion | Auditor Interno |
| Informe emitido | Cerrar auditoria | Cerrada | DPGC |
| Informe emitido | Reabrir | Ejecutada | DPGC |

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

Programa, hallazgos de auditoría, informe y CAPA.

## Acciones operativas o configuración adicional

El correo y las tareas periódicas requieren scheduler/servidor de correo configurados. Archivos o integraciones externas requieren sus servicios disponibles; su ausencia no debe reinterpretarse como una transición funcional válida.

## Fuente en código

La definición canónica está registrada en el manifiesto de cobertura y en sgc/setup. No se documentan estados adicionales a los definidos por el workflow actual.

