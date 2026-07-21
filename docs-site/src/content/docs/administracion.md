---
title: Administración y configuración
description: Preparación técnica sin sustituir decisiones funcionales.
---

## Responsabilidades de System Manager

Gestionar usuarios/roles, DocPerm, User Permissions, estructura sincronizada, maestros de workflow,
catálogos técnicos y disponibilidad de servicios. Los scripts de `sgc/setup/` son idempotentes y
deben ejecutarse según el flujo de despliegue del proyecto.

## Configuración funcional

Antes de probar carga marco/escala, estructura, periodos, procesos, indicadores, instrumentos y
obligaciones. Asigna Programa Sede a cuentas acotadas y limpia caché de permisos tras cambios.

## Servicios operativos

Supervisa frontend/backend, Redis, workers, scheduler, almacenamiento, correo, PDF, Mayan y SSO.
Un servicio caído debe registrarse como bloqueo operacional, con canario, no corregirse cambiando
reglas funcionales.

## Restricciones

- No otorgues System Manager para resolver un permiso funcional.
- No actives `send_email_alert` masivamente: el código documenta riesgo de adjuntos y flood.
- No modifiques estados directamente ni borres historial para repetir pruebas.
- Respaldar y verificar antes de cambios de permisos o configuración productiva.
