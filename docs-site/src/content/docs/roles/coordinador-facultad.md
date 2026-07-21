---
title: Coordinador de Calidad de Facultad
description: Guía funcional para probar el rol Coordinador de Calidad de Facultad.
---

## Propósito

Coordina información de calidad dentro de la facultad.

## Acceso y precondiciones

Cuenta asociada al ámbito y datos de al menos un programa de la facultad. Inicia sesión únicamente con esta cuenta y confirma en el perfil que no acumule roles adicionales.

## Acciones permitidas

Crear o actualizar autoevaluaciones, hallazgos y planes donde la matriz concede c/r/w; consultar catálogos institucionales.

## Restricciones que deben probarse

Los cierres y verificaciones finales permanecen en DPGC; la visibilidad puede depender de User Permissions.

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
