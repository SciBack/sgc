---
title: Colaborador
description: Guía funcional para probar el rol Colaborador.
---

## Propósito

Cualquier trabajador de la institución que no tiene un cargo en el SGC. El rol no concede permisos por sí mismo: sirve para que la persona sea usuaria del Desk y reciba el rol automático de Frappe **Desk User**, que es lo que le permite **reportar eventos de riesgo**. Sin ningún rol con acceso al Desk, Frappe la trataría como usuario del portal y no podría reportar.

## Acceso y precondiciones

Dos cuentas con **solo** el rol Colaborador, para probar que cada una ve únicamente lo suyo. Inicia sesión únicamente con esa cuenta y confirma en el perfil que no acumule roles adicionales.

## Acciones permitidas

- Crear un **evento de riesgo** desde el acceso rápido «Reportar evento de riesgo» o desde el área de Riesgos.
- Ver y completar sus propios reportes mientras siguen en **Reportado**.
- Recibir el aviso de lo que Calidad decidió sobre su reporte.

Esto lo tiene también cualquier otro usuario del sistema, tenga el rol que tenga: el permiso es de **Desk User** con «solo si es el creador».

## Restricciones que deben probarse

- No ve los eventos que reportaron otras personas.
- No toma en evaluación, no confirma y no descarta ningún evento, tampoco los suyos.
- No modifica su reporte una vez que Calidad lo tomó en evaluación.
- No ve riesgos, no conformidades ni el resto de registros del SGC. Puede **elegir** un proceso o una unidad orgánica en el reporte, pero no abrir sus fichas.

## Recorrido de prueba

1. Inicia sesión y registra la URL inicial y los módulos visibles.
2. Reporta un evento de riesgo con datos ficticios; confirma que queda en **Reportado** y con tu cuenta en **Reportado por**.
3. Con la segunda cuenta, reporta otro; vuelve a la primera y confirma que en la lista solo aparece el tuyo.
4. Intenta abrir por URL el evento de la otra cuenta; espera el rechazo del servidor.
5. Busca los botones del workflow en tu propio evento; no debe haber ninguno.

## Evidencia mínima

- Captura de la navegación visible, sin datos personales.
- Identificador ficticio del registro y estado antes/después.
- Respuesta HTTP o mensaje exacto del caso denegado.
- Rol, entorno, fecha/hora y pasos reproducibles.

## Fuente verificable

Catálogo de roles y `COLABORADORES` en `sgc/setup/f3b_rbac.py`; el flujo en [Evento de riesgo](../../flujos/evento-riesgo/).
