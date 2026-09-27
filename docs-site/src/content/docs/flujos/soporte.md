---
title: Reportar un problema
description: Prueba funcional del canal de soporte hacia el helpdesk de la institución.
---

## Qué es

**Reportar un problema** abre un ticket en el **helpdesk de la institución** sin salir del sistema. El SGC no es un sistema de tickets: el ticket, su prioridad y su procedimiento de atención viven en el helpdesk (Zammad, el helpdesk del catálogo, o un buzón de correo). El SGC pone el punto de entrada y decide qué viaja con él.

## Quién puede ejecutarlo

Cualquier usuario del sistema, desde el menú **Ayuda → Reportar un problema**. Solo aparece si TI (**System Manager**) activó el canal en **Configuración de soporte**.

## Configuración

En **Configuración de soporte**:

- **Zammad**: URL (https), token de una cuenta de servicio propia con permiso de agente en el grupo de destino, grupo que atiende al SGC y la equivalencia de las prioridades Baja/Media/Alta con las de Zammad (por defecto `1 low`, `2 normal`, `3 high`).
- **Correo**: la dirección de soporte. Pasa por el modo de ensayo y la lista blanca de *Configuración de correo*.
- **Correo de soporte**: también es la alternativa que se ofrece si el helpdesk no responde.

No se activa a medias: falta un dato o la URL no es https y no deja guardarlo activo.

## Pasos y resultados esperados

1. Abre cualquier pantalla y elige **Ayuda → Reportar un problema**.
2. Escribe asunto, prioridad y descripción, y pulsa **Revisar**. Resultado esperado: ves **exactamente** lo que se enviará: tu texto y el contexto técnico.
3. Pulsa **Enviar**. Resultado esperado: «Su reporte llegó al helpdesk con la referencia …». En Zammad el ticket queda a tu nombre, en el grupo configurado y con la prioridad elegida.

## Qué viaja

- Lo que escribe quien reporta: asunto, prioridad y descripción.
- Un contexto técnico fijo: sistema, institución, sitio, versión del SGC y de Frappe, el usuario y los roles de quien reporta, y la **pantalla sin el identificador del registro** (por ejemplo, «no-conformidad (un registro)», nunca el código).

**Nunca** el contenido del documento abierto, sus adjuntos ni datos de otras personas.

## Casos negativos

- Con el canal apagado: el menú no aparece y el servidor rechaza el envío.
- Asunto o descripción vacíos, asunto de más de 140 caracteres o una prioridad inventada: debe rechazarse.
- Helpdesk caído o que rechaza el ticket: aparece «No se pudo enviar», la alternativa por correo y tu texto listo para copiar. No un error genérico.
- Canal por correo con la lista blanca activa que no incluye la dirección de soporte: se trata como no enviado.

## Evidencia que debe capturarse

Captura de la vista previa, del mensaje final con la referencia y del ticket en el helpdesk; en el caso negativo, el diálogo con la alternativa. Oculta direcciones personales.

## Fuente en código

`sgc/soporte.py` (composición, lista blanca y proveedores), `sgc/public/js/soporte.js` (diálogo en dos pasos), `sgc/sgc_nucleo/doctype/configuracion_soporte/` (configuración) y `standard_help_items` en `sgc/hooks.py` (el menú).
