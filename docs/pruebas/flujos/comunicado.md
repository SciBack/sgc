---
title: Comunicado
description: Prueba funcional de los comunicados de nuevas funcionalidades y mantenimientos programados.
---

## Qué es

Un **comunicado** avisa por correo a los usuarios de los roles elegidos: de una **nueva funcionalidad**, de un **mantenimiento programado** o de un aviso general.

## Quién puede ejecutarlo

La **DPGC**, su analista y TI (**System Manager**, que es quien programa los mantenimientos). El resto de roles lo lee.

## Pasos y resultados esperados

1. Crea el comunicado con asunto, tipo, mensaje y los roles destinatarios. Resultado esperado: queda en **Borrador**.
2. Si es un **mantenimiento programado**, indica su inicio y, si lo sabes, su fin.
3. Pulsa **Enviar comunicado** y confirma. Resultado esperado: queda en **Enviado**, con quién lo envió, cuándo, a cuántos se envió y cuántos retuvo la configuración del correo.

## Restricciones

- Un mantenimiento se avisa **con al menos 24 horas de antelación**: si el inicio es más próximo, no se envía.
- El fin del mantenimiento va después del inicio.
- **Un comunicado enviado no se reenvía ni se modifica.**
- Solo llega a usuarios activos con correo; nunca a las cuentas técnicas.
- Pasa por el modo de ensayo y la lista blanca del correo: lo retenido consta en *Registro Correo*.

## Casos negativos

- Enviar un mantenimiento que empieza en menos de 24 horas: debe rechazarse.
- Poner el fin antes del inicio: debe rechazarse.
- Enviar a roles sin usuarios activos: debe rechazarse.
- Enviar dos veces o editar un comunicado enviado: debe rechazarse.

## Evidencia que debe capturarse

Captura del comunicado antes y después del envío, del recuento de enviados y retenidos y de *Registro Correo*; rol utilizado. Oculta direcciones personales.

## Fuente en código

`sgc/sgc_gobierno/doctype/comunicado/` y `sgc/correo.py` (`enviar`).
