---
title: Preparación de las pruebas
description: Cuentas, datos, servicios y seguridad antes de ejecutar E2E.
---

## Entorno

Confirma URL, commit desplegado, fecha/hora, navegador y alcance. No ejecutes regresión destructiva
en producción. Usa prefijos de prueba y registra cómo limpiar los datos.

## Cuentas mínimas

- Responsable de Calidad de Programa y Miembro de Comité del mismo Programa Sede.
- Dos cuentas DPGC distintas para probar segregación.
- Analista de Calidad, Dueño de Proceso, Data Steward y Auditor Interno.
- Rectorado/VR, Decano/Director, Responsable de Sede y Autoridad Aprobadora.
- System Manager solo para preparación técnica; Lector Externo si el portal está habilitado.

Cada cuenta debe tener un solo rol funcional salvo que el caso pruebe acumulación deliberadamente.

## Datos de prueba

Prepara dos sedes/programas para aislamiento, un marco pequeño con escala NL/L/LP, un periodo,
criterios, procesos, indicadores, obligación, instrumento y auditoría. Usa nombres sintéticos; no
copies DNI, correos personales o expedientes reales.

## Servicios que debes confirmar

SSO/login local, Redis/workers/scheduler, correo de prueba, almacenamiento de archivos, motor PDF y
la integración documental si el flujo la usa. Marca **no ejecutable** cualquier caso bloqueado por
una dependencia ausente; no lo registres como PASS.

## Captura segura

Abre DevTools solo cuando sea necesario. Oculta cookies, Authorization, CSRF, nombres, correos y
archivos. Conserva el ID sintético, rol, estado, acción, respuesta y hora.
