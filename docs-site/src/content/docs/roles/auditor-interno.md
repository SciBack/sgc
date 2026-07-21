---
title: Auditor Interno
description: Guía funcional para probar el rol Auditor Interno.
---

## Propósito

Planifica y ejecuta auditorías y registra hallazgos independientes.

## Acceso y precondiciones

Cuenta auditora separada, alcance y equipo de auditoría configurados. Inicia sesión únicamente con esta cuenta y confirma en el perfil que no acumule roles adicionales.

## Acciones permitidas

Crear programas, auditorías, informes y hallazgos; escalar un hallazgo de auditoría a no conformidad cuando corresponda.

## Restricciones que deben probarse

No valora criterios ni cierra planes de mejora; el cierre final corresponde a DPGC.

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
