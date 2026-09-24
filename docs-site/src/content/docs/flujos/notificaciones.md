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

## Qué avisa el SGC y a quién

Todas las reglas son de **correo y campana** a la vez: la campana del Desk llega siempre, y el
correo según el modo de arriba.

**Vencimientos** (el scheduler, una vez al día; cada documento coincide un solo día):

| Documento | Cuándo | A quién |
|---|---|---|
| Documento Controlado | 15 días antes de la próxima revisión | quien lo elaboró y DPGC |
| Evidencia | 15 días antes de que venza | quien la cargó y DPGC |
| Acción de Mejora | 7 días antes de la fecha de compromiso | su responsable y DPGC |
| Plan de Mejora | 7 días antes de la fecha de compromiso | su responsable y DPGC |
| Reunión | al convocarla | los asistentes |

**Transiciones de estado**: un correo por cada cambio real de estado, nunca por guardar sin
cambiarlo. Va a quien tiene que actuar ahora. Si el documento no nombra a esa persona, va al rol
que actúa en ese paso (entre paréntesis):

| Documento | Estado al que llega → a quién |
|---|---|
| Documento Controlado | En revisión → revisor (DPGC) · Observado → quien lo elaboró (Dueño de Proceso) · Aprobado → aprobador (Autoridad Aprobadora) · Obsoleto → quien lo elaboró |
| Documento Controlado | **Publicado** → quien lo elaboró, revisó y aprobó, y DPGC, **con el archivo adjunto** |
| No Conformidad | En análisis / En tratamiento → responsable (Responsable de Calidad de Programa) · En verificación → verificador (DPGC) · Cerrada → responsable |
| Acción de Mejora | En ejecución → responsable (Responsable de Calidad de Programa) · Ejecutada → verificador (DPGC) · Verificada → responsable |
| Auditoría | En ejecución / Ejecutada / Cerrada → equipo auditor (Auditor Interno) · Informe emitido → DPGC |
| Hallazgo de Auditoría | Escalado a NC → DPGC · Abierto / Cerrado → Auditor Interno |
| Informe de Cumplimiento | Aprobado → Autoridad Aprobadora · Presentado a SUNEDU → DPGC |

Si el envío falla (SMTP caído, cuenta sin configurar), el documento se guarda igual y el fallo
queda en el registro de errores y en la cola de correo.

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

Los workflows tienen `send_email_alert` deshabilitado: dispara en cualquier guardado con una transición pendiente, no solo en la transición real. Los avisos de transición van por las reglas de arriba; no activarlo como arreglo rápido.

Las reglas se reescriben en cada `bench migrate` desde `f7`/`f15`: un cambio hecho a mano en el Desk (días de antelación, destinatarios, texto) se pierde en la siguiente actualización, y una regla desactivada a mano vuelve a activarse. Solo
se respeta el canal. Para dejar de escribir a alguien, usar el modo de ensayo o la lista blanca.

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

