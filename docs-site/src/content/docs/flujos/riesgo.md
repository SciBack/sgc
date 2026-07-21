---
title: Riesgo
description: Prueba funcional completa del flujo Riesgo.
---

## Quién puede ejecutarlo

Dueño de Proceso; DPGC cierra o materializa.

## Precondiciones

Proceso, contexto, probabilidad e impacto definidos. Usa identificadores ficticios y cuentas separadas cuando intervengan aprobación o cierre.

## Pasos y resultados esperados

1. En estado **Identificado**, inicia sesión como **Dueño de Proceso** y ejecuta **Evaluar**. Resultado esperado: el registro queda en **Evaluado** y la acción aparece en su historial.
2. En estado **Evaluado**, inicia sesión como **Dueño de Proceso** y ejecuta **Iniciar tratamiento**. Resultado esperado: el registro queda en **En tratamiento** y la acción aparece en su historial.
3. En estado **En tratamiento**, inicia sesión como **Dueño de Proceso** y ejecuta **Monitorear**. Resultado esperado: el registro queda en **Monitoreado** y la acción aparece en su historial.
4. En estado **Monitoreado**, inicia sesión como **DPGC** y ejecuta **Cerrar**. Resultado esperado: el registro queda en **Cerrado** y la acción aparece en su historial.
5. En estado **Monitoreado**, inicia sesión como **DPGC** y ejecuta **Materializar**. Resultado esperado: el registro queda en **Materializado** y la acción aparece en su historial.
6. En estado **Materializado**, inicia sesión como **DPGC** y ejecuta **Cerrar**. Resultado esperado: el registro queda en **Cerrado** y la acción aparece en su historial.

## Estados por los que pasa

**Identificado** → **Evaluado** → **En tratamiento** → **Monitoreado** → **Cerrado** → **Materializado**. Las devoluciones o reaperturas se muestran en la tabla, por lo que el recorrido no siempre es lineal.

| Desde | Acción | Hacia | Rol |
|---|---|---|---|
| Identificado | Evaluar | Evaluado | Dueño de Proceso |
| Evaluado | Iniciar tratamiento | En tratamiento | Dueño de Proceso |
| En tratamiento | Monitorear | Monitoreado | Dueño de Proceso |
| Monitoreado | Cerrar | Cerrado | DPGC |
| Monitoreado | Materializar | Materializado | DPGC |
| Materializado | Cerrar | Cerrado | DPGC |

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

Tratamientos, procesos, indicadores y revisión por dirección.

## Acciones operativas o configuración adicional

El correo y las tareas periódicas requieren scheduler/servidor de correo configurados. Archivos o integraciones externas requieren sus servicios disponibles; su ausencia no debe reinterpretarse como una transición funcional válida.

## Fuente en código

La definición canónica está registrada en el manifiesto de cobertura y en sgc/setup. No se documentan estados adicionales a los definidos por el workflow actual.

