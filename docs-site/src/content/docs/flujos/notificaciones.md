---
title: Notificaciones
description: Prueba funcional del proceso Notificaciones.
---

## Quién puede ejecutarlo

Sistema/scheduler; destinatarios dependen de responsables y roles.

## Precondiciones

Correo saliente y scheduler habilitados; datos con fechas/destinatarios.

## Pasos y resultados esperados

1. Crea un caso próximo a vencer o una transición notificada. Resultado: queda elegible.
2. Ejecuta la tarea/espera scheduler en prueba. Resultado: se genera una notificación.
3. Revisa destinatario y contenido sin datos sensibles. Resultado: coincide con configuración.
4. Repite ejecución idempotente. Resultado: no hay inundación inesperada.

## Estados por los que pasa

Elegible → encolada/enviada o error operacional. Este proceso no añade estados distintos a los que persisten sus DocTypes o sesión.

## Permisos

Verifica permisos de lectura/escritura sobre cada DocType y la autorización del método backend. La visibilidad de interfaz no reemplaza el control del servidor.

## Restricciones

Los workflows tienen send_email_alert deshabilitado en varios casos para evitar correos en cada save; no activarlo como arreglo rápido.

## Casos negativos

- Repetir el método para comprobar idempotencia o rechazo consistente.
- Ejecutar con rol o ámbito no autorizado.
- Omitir una precondición y conservar el mensaje exacto.
- Confirmar que el fallo no deja cambios parciales.

## Evidencia que debe capturarse

Estado o valores antes/después, identificador ficticio, rol, URL/método, respuesta y logs correlacionables sin cookies, tokens ni datos personales.

## Relación con otros módulos

Documentos, evidencias, mejoras, reuniones y cumplimiento.

## Acciones operativas o configuración adicional

SMTP, workers y scheduler son obligatorios; usar buzones de prueba.

## Fuente en código

sgc/setup/f7_notificaciones.py y f15_notificaciones_workflow.py. El comportamiento descrito debe revisarse de nuevo si estas fuentes cambian.

