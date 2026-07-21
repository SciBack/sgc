---
title: Checklist de regresión
description: Cobertura completa antes de aprobar una versión de SGC.
---

## Acceso y seguridad

- [ ] Login local y SSO; logout invalida la sesión.
- [ ] Menús por cada rol y rechazo por URL/API directa.
- [ ] Aislamiento entre dos Programa Sede con User Permissions.
- [ ] Sin secretos ni datos personales en logs, reportes o capturas.

## Flujos

- [ ] Los 14 workflows recorren sus transiciones positivas.
- [ ] Devoluciones, reaperturas y autoaprobación se prueban.
- [ ] Scoring distingue propuesta de confirmación.
- [ ] Evidencia, trazabilidad y CAPA permanecen relacionadas.
- [ ] Procesos, documentos, indicadores, riesgos y obligaciones funcionan.
- [ ] Notificaciones y tareas periódicas son idempotentes o quedan bloqueadas explícitamente.

## Salidas y auditoría

- [ ] PDF/Excel abre y coincide con datos fuente.
- [ ] Historial conserva actor, fecha y estado.
- [ ] Cuentas de lectura no escriben.
- [ ] 404 y errores no caen en una pantalla engañosa de la SPA.

## Interfaz

- [ ] Escritorio y móvil; claro y oscuro.
- [ ] Teclado/foco, contraste y búsqueda.
- [ ] Sin desbordamiento horizontal.
- [ ] Mensajes de validación comprensibles y sin datos internos.

Adjunta al cierre la versión, ambiente, ejecutor, totales PASS/FAIL/BLOCKED y enlaces a hallazgos.
