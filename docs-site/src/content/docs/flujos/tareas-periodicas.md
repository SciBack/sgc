---
title: Tareas periódicas
description: Prueba funcional del proceso Tareas periódicas.
---

## Quién puede ejecutarlo

Scheduler y workers; revisión por administrador/DPGC.

## Precondiciones

Scheduler activo, zona horaria y datos con fechas controladas.

## Pasos y resultados esperados

1. Identifica la tarea declarada en hooks. Resultado: frecuencia conocida.
2. Prepara un registro vencido/próximo a vencer. Resultado: canario elegible.
3. Ejecuta la función en entorno de prueba. Resultado: actualiza/notifica según código.
4. Ejecuta otra vez. Resultado: conserva idempotencia y no duplica efectos.
5. Revisa logs y estado. Resultado: existe trazabilidad sin secretos.

## Estados por los que pasa

Programada → ejecutada → efecto o error registrado. Este proceso no añade estados distintos a los que persisten sus DocTypes o sesión.

## Permisos

Verifica permisos de lectura/escritura sobre cada DocType y la autorización del método backend. La visibilidad de interfaz no reemplaza el control del servidor.

## Restricciones

No probar alterando reloj de producción; distinguir scheduler detenido de regla funcional defectuosa.

## Casos negativos

- Repetir el método para comprobar idempotencia o rechazo consistente.
- Ejecutar con rol o ámbito no autorizado.
- Omitir una precondición y conservar el mensaje exacto.
- Confirmar que el fallo no deja cambios parciales.

## Evidencia que debe capturarse

Estado o valores antes/después, identificador ficticio, rol, URL/método, respuesta y logs correlacionables sin cookies, tokens ni datos personales.

## Relación con otros módulos

Evidencias, acciones, planes y notificaciones.

## Acciones operativas o configuración adicional

Requiere scheduler, workers, Redis y correo cuando la tarea envía alertas.

## Fuente en código

sgc/tasks.py y sgc/hooks.py. El comportamiento descrito debe revisarse de nuevo si estas fuentes cambian.

