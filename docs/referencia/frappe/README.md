# Biblioteca técnica — Frappe Framework v16

## Propósito

Esta carpeta registra la documentación externa que gobierna las decisiones técnicas de
SGC. No replica páginas oficiales: conserva la fuente, la versión aplicable, el alcance
y el vínculo con el código. Así se evita que una copia local quede desactualizada o
mezcle contenido de una versión distinta.

## Versión de plataforma

| Campo | Valor |
|---|---|
| Framework fijado para SGC | [Frappe v16.32.0](https://github.com/frappe/frappe/releases/tag/v16.32.0) |
| Tag de código upstream | v16.32.0 (5cba016) |
| Fecha de release | 26-ago-2026 |
| Fuente de verdad local | ../../deploy/frappe.version |
| CI | ../../.github/workflows/tests.yml |

La release incorpora cambios relevantes para SGC: notificación de cambios confirmados en
formularios y tablas hijas, controles de pestañas de formulario, resultados personalizados
en la búsqueda global, galería de adjuntos y validación del método HTTP en la API de
documentos. Antes de usar una capacidad nueva, validar contra el tag fijado, no contra la
rama móvil version-16.

## Catálogo indexado

[catalogo-framework-v16.txt](catalogo-framework-v16.txt) contiene 216 URLs
extraídas de la navegación pública oficial el 2026-09-01. Es un índice navegable y
versionado; el contenido permanece en su fuente oficial.

Las familias prioritarias para SGC son:

1. Modelo y datos: DocTypes, controladores, naming, tablas hijas, permisos, auditoría,
   API Document/Database y Query Builder.
2. Desk y operación: Workspace, scripts de cliente/servidor, reportes, impresión,
   adjuntos, notificaciones y búsqueda.
3. Despliegue: Bench, migrate, backup/restore, PostgreSQL, scheduler, workers,
   servicios de fondo, producción y rate limiting.
4. Seguridad e integración: OAuth/OIDC, Social Login Key, REST API, webhooks,
   autenticación por token, LDAP y seguridad.
5. Calidad: tests unitarios/integración/UI, logging, profiling y debugging.

## Cómo usar la fuente correcta

- Para comportamiento de Frappe instalado: consultar primero el código del tag v16.32.0
  o el runtime de producción.
- Para conceptos y guía operativa: usar el enlace del catálogo, anotando fecha de consulta.
- Para una decisión que dependa de framework: citar la URL oficial y registrar la sección
  relevante en docs/decisiones.
- No usar el repositorio frappe/frappe_docs: está archivado y su README declara que el flujo
  de documentación actual vive fuera de ese repositorio.

## Actualización

El catálogo es un snapshot de navegación, no una promesa de compatibilidad. Para
actualizarlo, revisar el menú oficial, regenerar el catálogo y revisar el diff. La página de
documentación puede describir una versión más reciente que la que SGC tiene fijada.

## Fuentes oficiales

- [Introducción y navegación de Frappe Framework](https://docs.frappe.io/framework/user/en/introduction)
- [Documentación oficial de Frappe](https://docs.frappe.io/)
- [Release v16.32.0](https://github.com/frappe/frappe/releases/tag/v16.32.0)
- [Repositorio de Frappe](https://github.com/frappe/frappe)
