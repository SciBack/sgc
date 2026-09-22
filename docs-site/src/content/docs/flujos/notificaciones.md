---
title: Notificaciones
description: Prueba funcional del proceso Notificaciones.
---

## Quién puede ejecutarlo

Sistema/scheduler; destinatarios dependen de responsables y roles.

## Precondiciones

Correo saliente y scheduler habilitados; datos con fechas/destinatarios.

## Modo de ensayo y lista blanca

Encender el correo es empezar a escribir a personas reales, así que el envío pasa por
**Configuracion Correo** (`/desk/configuracion-correo`, solo System Manager):

- **Ensayo** (lo que trae un sitio nuevo): ninguna regla envía correo. Cada destinatario que
  se habría usado queda en **Registro Correo**, con la regla, el documento y el asunto.
- **Real con lista blanca**: solo se escribe a las direcciones de la lista. El resto queda en
  Registro Correo como *omitido*. Sirve para estrenar el correo con dos o tres personas.
- **Real sin lista blanca**: se escribe a todos los destinatarios de cada regla.

Pasar a Real y vaciar la lista blanca son **dos guardados distintos**: el formulario rechaza
hacer las dos cosas a la vez. El botón **Comprobar destinatarios** dice, para cada regla de
correo activa, a cuántas personas con correo alcanza cada rol. Un rol que no alcanza a nadie es
un aviso que nunca llegará y el sistema no fallaría: también lo señala
`bench --site DOMINIO execute sgc.verificacion.run`.

Al actualizar, un sitio que ya tenía reglas de correo activas **conserva el envío real** (lo
fija el parche `correo_conservar_envio_real`), para no cortar en silencio avisos que ya llegan.

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

sgc/setup/f7_notificaciones.py, f15_notificaciones_workflow.py y sgc/correo.py (ensayo, lista blanca y comprobación de destinatarios). El comportamiento descrito debe revisarse de nuevo si estas fuentes cambian.

