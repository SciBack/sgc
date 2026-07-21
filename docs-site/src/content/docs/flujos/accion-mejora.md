---
title: Acción de mejora
description: Prueba funcional completa del flujo Acción de mejora.
---

## Quién puede ejecutarlo

Responsable de Calidad de Programa; DPGC verifica eficacia.

## Precondiciones

Acción planificada vinculada a un Plan Mejora. Usa identificadores ficticios y cuentas separadas cuando intervengan aprobación o cierre.

## Pasos y resultados esperados

1. En estado **Planificada**, inicia sesión como **Responsable de Calidad de Programa** y ejecuta **Iniciar**. Resultado esperado: el registro queda en **En ejecucion** y la acción aparece en su historial.
2. En estado **En ejecucion**, inicia sesión como **Responsable de Calidad de Programa** y ejecuta **Marcar ejecutada**. Resultado esperado: el registro queda en **Ejecutada** y la acción aparece en su historial.
3. En estado **Ejecutada**, inicia sesión como **DPGC** y ejecuta **Verificar eficaz**. Resultado esperado: el registro queda en **Verificada eficaz** y la acción aparece en su historial.
4. En estado **Ejecutada**, inicia sesión como **DPGC** y ejecuta **Verificar no eficaz**. Resultado esperado: el registro queda en **Verificada no eficaz** y la acción aparece en su historial.
5. En estado **Verificada no eficaz**, inicia sesión como **DPGC** y ejecuta **Reabrir**. Resultado esperado: el registro queda en **En ejecucion** y la acción aparece en su historial.

## Estados por los que pasa

**Planificada** → **En ejecucion** → **Ejecutada** → **Verificada eficaz** → **Verificada no eficaz**. Las devoluciones o reaperturas se muestran en la tabla, por lo que el recorrido no siempre es lineal.

| Desde | Acción | Hacia | Rol |
|---|---|---|---|
| Planificada | Iniciar | En ejecucion | Responsable de Calidad de Programa |
| En ejecucion | Marcar ejecutada | Ejecutada | Responsable de Calidad de Programa |
| Ejecutada | Verificar eficaz | Verificada eficaz | DPGC |
| Ejecutada | Verificar no eficaz | Verificada no eficaz | DPGC |
| Verificada no eficaz | Reabrir | En ejecucion | DPGC |

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

Plan de mejora, evidencia y tareas periódicas de vencimiento.

## Acciones operativas o configuración adicional

El correo y las tareas periódicas requieren scheduler/servidor de correo configurados. Archivos o integraciones externas requieren sus servicios disponibles; su ausencia no debe reinterpretarse como una transición funcional válida.

## Fuente en código

La definición canónica está registrada en el manifiesto de cobertura y en sgc/setup. No se documentan estados adicionales a los definidos por el workflow actual.

