---
title: Biblioteca Frappe v16
description: Referencia oficial indexada para la versión de Frappe fijada por SGC.
---

SGC corre sobre **Frappe v16.32.0**. La versión se fija explícitamente para que producción,
CI y recuperación ante desastres usen el mismo framework; no se toma de la rama móvil
version-16.

## Fuente de verdad

- [Release v16.32.0](https://github.com/frappe/frappe/releases/tag/v16.32.0)
- [Introducción oficial de Framework](https://docs.frappe.io/framework/user/en/introduction)
- [Documentación oficial completa](https://docs.frappe.io/)
- [Repositorio de Frappe](https://github.com/frappe/frappe)

La biblioteca central versionada se encuentra en
[sciback/biblioteca/frappe](https://github.com/SciBack/biblioteca/tree/main/frappe).
Contiene una ficha curada, manifiesto de colección, espejo offline greppable de la documentación
oficial y el índice de navegación completo. SGC la consume por enlace: no mantiene una copia.

## Rutas prioritarias para SGC

| Necesidad | Fuente oficial |
|---|---|
| DocTypes, permisos y controladores | [Basics / DocTypes](https://docs.frappe.io/framework/user/en/basics/doctypes) |
| Eventos, hooks y jobs | [Hooks](https://docs.frappe.io/framework/user/en/python-api/hooks) · [Background Jobs](https://docs.frappe.io/framework/user/en/api/background_jobs) |
| Desk, Workspace y scripts | [Workspace](https://docs.frappe.io/framework/user/en/desk/workspace) · [Client Script](https://docs.frappe.io/framework/user/en/desk/scripting/client-script) |
| API e integraciones | [REST API](https://docs.frappe.io/framework/user/en/api/rest) · [OIDC social login](https://docs.frappe.io/framework/user/en/guides/integration/openid_connect_and_frappe_social_login) |
| Migración y operación | [bench migrate](https://docs.frappe.io/framework/user/en/bench/reference/migrate) · [Production](https://docs.frappe.io/framework/user/en/production-setup) |
| PostgreSQL, copias y recuperación | [PostgreSQL](https://docs.frappe.io/framework/user/en/guides/database-settings/postgres-database-setup) · [backup](https://docs.frappe.io/framework/user/en/bench/reference/backup) · [restore](https://docs.frappe.io/framework/user/en/bench/reference/restore) |
| Pruebas | [Testing](https://docs.frappe.io/framework/user/en/testing) |

Las páginas oficiales pueden avanzar antes que SGC. Para implementar una característica,
verifica primero que exista en el tag v16.32.0.
