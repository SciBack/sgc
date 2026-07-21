---
title: Responsable de Calidad de Programa
description: Guía funcional para probar el rol Responsable de Calidad de Programa.
---

## Propósito

Ejecuta la autoevaluación y la mejora del programa.

## Acceso y precondiciones

Cuenta acotada a Programa Sede, marco cargado y periodo de prueba. Inicia sesión únicamente con esta cuenta y confirma en el perfil que no acumule roles adicionales.

## Acciones permitidas

Crear y valorar criterios, cargar evidencias, iniciar y remitir autoevaluaciones, tratar hallazgos/NC y ejecutar acciones.

## Restricciones que deben probarse

No consolida ni cierra controles DPGC; la visibilidad por Programa Sede es opt-in mediante User Permission.

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
