---
title: No conformidad
description: Prueba funcional completa del flujo No conformidad.
---

## Quién puede ejecutarlo

Responsable de Calidad de Programa; DPGC verifica y cierra.

## Precondiciones

No conformidad abierta con causa y responsable identificables. Usa identificadores ficticios y cuentas separadas cuando intervengan aprobación o cierre.

## Pasos y resultados esperados

1. En estado **Abierta**, inicia sesión como **Responsable de Calidad de Programa** y ejecuta **Analizar causa**. Resultado esperado: el registro queda en **En analisis** y la acción aparece en su historial.
2. En estado **En analisis**, inicia sesión como **Responsable de Calidad de Programa** y ejecuta **Tratar**. Resultado esperado: el registro queda en **En tratamiento** y la acción aparece en su historial.
3. En estado **En tratamiento**, inicia sesión como **Responsable de Calidad de Programa** y ejecuta **Enviar a verificacion**. Resultado esperado: el registro queda en **En verificacion** y la acción aparece en su historial.
4. En estado **En verificacion**, inicia sesión como **DPGC** y ejecuta **Cerrar eficaz**. Resultado esperado: el registro queda en **Cerrada eficaz** y la acción aparece en su historial.
5. En estado **En verificacion**, inicia sesión como **DPGC** y ejecuta **Cerrar no eficaz**. Resultado esperado: el registro queda en **Cerrada no eficaz** y la acción aparece en su historial.
6. En estado **En verificacion**, inicia sesión como **DPGC** y ejecuta **Reabrir tratamiento**. Resultado esperado: el registro queda en **En tratamiento** y la acción aparece en su historial.

## Estados por los que pasa

**Abierta** → **En analisis** → **En tratamiento** → **En verificacion** → **Cerrada eficaz** → **Cerrada no eficaz**. Las devoluciones o reaperturas se muestran en la tabla, por lo que el recorrido no siempre es lineal.

| Desde | Acción | Hacia | Rol |
|---|---|---|---|
| Abierta | Analizar causa | En analisis | Responsable de Calidad de Programa |
| En analisis | Tratar | En tratamiento | Responsable de Calidad de Programa |
| En tratamiento | Enviar a verificacion | En verificacion | Responsable de Calidad de Programa |
| En verificacion | Cerrar eficaz | Cerrada eficaz | DPGC |
| En verificacion | Cerrar no eficaz | Cerrada no eficaz | DPGC |
| En verificacion | Reabrir tratamiento | En tratamiento | DPGC |

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

Hallazgos, planes y acciones de mejora.

## Acciones operativas o configuración adicional

El correo y las tareas periódicas requieren scheduler/servidor de correo configurados. Archivos o integraciones externas requieren sus servicios disponibles; su ausencia no debe reinterpretarse como una transición funcional válida.

## Fuente en código

La definición canónica está registrada en el manifiesto de cobertura y en sgc/setup. No se documentan estados adicionales a los definidos por el workflow actual.

