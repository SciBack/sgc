---
title: Obligaciones regulatorias
description: Prueba funcional del proceso Obligaciones regulatorias.
---

## Quién puede ejecutarlo

DPGC prepara; Autoridad Aprobadora formaliza presentación.

## Precondiciones

Obligación, periodo, evidencias y responsable registrados.

## Pasos y resultados esperados

1. Registra obligación y seguimiento. Resultado: plazo/estado persisten.
2. Prepara Informe Cumplimiento. Resultado: expediente enlaza evidencias.
3. Revisa y aprueba con cuentas separadas. Resultado: historial conserva actores.
4. Presenta a SUNEDU. Resultado: estado cambia solo por Autoridad Aprobadora.

## Estados por los que pasa

Pendiente/seguimiento → informe → aprobado → presentado. Este proceso no añade estados distintos a los que persisten sus DocTypes o sesión.

## Permisos

Verifica permisos de lectura/escritura sobre cada DocType y la autorización del método backend. La visibilidad de interfaz no reemplaza el control del servidor.

## Restricciones

No marcar presentado sin soporte operacional; las alertas no sustituyen la presentación externa.

## Casos negativos

- Repetir el método para comprobar idempotencia o rechazo consistente.
- Ejecutar con rol o ámbito no autorizado.
- Omitir una precondición y conservar el mensaje exacto.
- Confirmar que el fallo no deja cambios parciales.

## Evidencia que debe capturarse

Estado o valores antes/después, identificador ficticio, rol, URL/método, respuesta y logs correlacionables sin cookies, tokens ni datos personales.

## Relación con otros módulos

Informe Cumplimiento, evidencias, notificaciones y reportes.

## Acciones operativas o configuración adicional

La presentación externa y el acuse requieren acción/dato operacional adicional.

## Fuente en código

sgc/setup/f11_workflow_cumplimiento.py. El comportamiento descrito debe revisarse de nuevo si estas fuentes cambian.

