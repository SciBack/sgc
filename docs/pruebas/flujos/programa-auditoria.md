---
title: Programa de auditoría
description: Prueba funcional completa del flujo Programa de auditoría.
---

## Quién puede ejecutarlo

Auditor Interno y DPGC.

## Precondiciones

Periodo, alcance y responsables de auditoría configurados. Usa identificadores ficticios y cuentas separadas cuando intervengan aprobación o cierre.

## Pasos y resultados esperados

1. En estado **Borrador**, inicia sesión como **DPGC** y ejecuta **Aprobar programa**. Resultado esperado: el registro queda en **Aprobado** y la acción aparece en su historial.
2. En estado **Aprobado**, inicia sesión como **Auditor Interno** y ejecuta **Iniciar ejecucion**. Resultado esperado: el registro queda en **En ejecucion** y la acción aparece en su historial.
3. En estado **Aprobado**, inicia sesión como **DPGC** y ejecuta **Devolver a borrador**. Resultado esperado: el registro queda en **Borrador** y la acción aparece en su historial.
4. En estado **En ejecucion**, inicia sesión como **DPGC** y ejecuta **Cerrar programa**. Resultado esperado: el registro queda en **Cerrado** y la acción aparece en su historial.

## Estados por los que pasa

**Borrador** → **Aprobado** → **En ejecucion** → **Cerrado**. Las devoluciones o reaperturas se muestran en la tabla, por lo que el recorrido no siempre es lineal.

| Desde | Acción | Hacia | Rol |
|---|---|---|---|
| Borrador | Aprobar programa | Aprobado | DPGC |
| Aprobado | Iniciar ejecucion | En ejecucion | Auditor Interno |
| Aprobado | Devolver a borrador | Borrador | DPGC |
| En ejecucion | Cerrar programa | Cerrado | DPGC |

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

Auditorías, equipo, criterios e informes.

## Acciones operativas o configuración adicional

El correo y las tareas periódicas requieren scheduler/servidor de correo configurados. Archivos o integraciones externas requieren sus servicios disponibles; su ausencia no debe reinterpretarse como una transición funcional válida.

## Fuente en código

La definición canónica está registrada en el manifiesto de cobertura y en sgc/setup. No se documentan estados adicionales a los definidos por el workflow actual.

