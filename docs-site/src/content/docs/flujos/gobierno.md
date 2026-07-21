---
title: Gobierno institucional
description: Prueba funcional del proceso Gobierno institucional.
---

## Quién puede ejecutarlo

DPGC administra; alta dirección consulta/decide donde el workflow lo indica.

## Precondiciones

Política, objetivos, reuniones y responsables definidos.

## Pasos y resultados esperados

1. Registra o actualiza un elemento de gobierno permitido. Resultado: queda versionado/auditable.
2. Convoca o registra reunión. Resultado: asistentes/acuerdos persisten.
3. Consulta desde alta dirección. Resultado: lectura disponible sin edición operativa.
4. Verifica acuerdos en revisión por dirección. Resultado: relaciones coherentes.

## Estados por los que pasa

Borrador/registro → seguimiento → decisión. Este proceso no añade estados distintos a los que persisten sus DocTypes o sesión.

## Permisos

Verifica permisos de lectura/escritura sobre cada DocType y la autorización del método backend. La visibilidad de interfaz no reemplaza el control del servidor.

## Restricciones

Separar administración técnica de decisiones de gobierno; respetar roles de lectura.

## Casos negativos

- Repetir el método para comprobar idempotencia o rechazo consistente.
- Ejecutar con rol o ámbito no autorizado.
- Omitir una precondición y conservar el mensaje exacto.
- Confirmar que el fallo no deja cambios parciales.

## Evidencia que debe capturarse

Estado o valores antes/después, identificador ficticio, rol, URL/método, respuesta y logs correlacionables sin cookies, tokens ni datos personales.

## Relación con otros módulos

Reuniones, política, objetivos, revisión y reportes.

## Acciones operativas o configuración adicional

Correo de convocatoria requiere configuración SMTP/scheduler.

## Fuente en código

sgc/setup/f1_gobierno.py. El comportamiento descrito debe revisarse de nuevo si estas fuentes cambian.

