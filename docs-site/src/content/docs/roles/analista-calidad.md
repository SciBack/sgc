---
title: Analista de Calidad (DPGC)
description: Guía funcional para probar el rol Analista de Calidad (DPGC).
---

## Propósito

Opera el control de calidad y revisa información antes de las decisiones de gobierno.

## Acceso y precondiciones

Cuenta con el rol; evidencias pendientes y registros del ámbito de prueba. Inicia sesión únicamente con esta cuenta y confirma en el perfil que no acumule roles adicionales.

## Acciones permitidas

Leer y actualizar múltiples registros; validar u observar evidencias; apoyar control documental y seguimiento.

## Restricciones que deben probarse

No ejecuta cierres reservados a DPGC o Autoridad Aprobadora; sus permisos no equivalen a administración técnica.

## Recorrido de prueba

1. Inicia sesión y registra la URL inicial y los módulos visibles.
2. Abre un registro existente del ámbito asignado; confirma que la lectura funciona.
3. Ejecuta una acción permitida de la lista anterior y captura el estado antes/después.
4. Intenta una acción reservada a otro rol; espera ausencia del control o rechazo del servidor.
5. Cierra sesión, vuelve a entrar y confirma que el resultado persistió sin ampliar permisos.

## Evidencia mínima

- Captura de la navegación visible, sin datos personales.
- Identificador ficticio del registro y estado antes/después.
- Respuesta HTTP o mensaje exacto del caso denegado.
- Rol, entorno, fecha/hora y pasos reproducibles.

## Fuente verificable

Catálogo y matriz RBAC en sgc/setup/f3b_rbac.py; las transiciones específicas se detallan en las páginas de [flujos](../../flujos/).
