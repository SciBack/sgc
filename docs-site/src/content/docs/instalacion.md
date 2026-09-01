---
title: Instalación
description: Cómo instalar y operar la app SGC sobre el framework fijado.
---

## Requisitos

- Bench funcional con **Frappe v16.32.0**. La fuente de verdad del tag es
  deploy/frappe.version; no usar la rama móvil version-16.
- PostgreSQL para el site. SGC se valida sobre PostgreSQL, no sobre MariaDB.
- Python 3.14 o posterior y Node 24 para assets y documentación.

## Instalar la app

~~~bash
cd RUTA_DEL_BENCH
bench get-app https://github.com/SciBack/sgc --branch main
bench --site TU_SITE install-app sgc
bench --site TU_SITE migrate
~~~

El hook de migración aplica de forma idempotente los DocTypes, workflows, RBAC,
notificaciones y Workspace SGC.

## Assets y documentación

SGC usa el **Desk nativo de Frappe v16** y el Workspace SGC. Desde la raíz de la app:

~~~bash
python -m compileall -q sgc
bench build --app sgc
cd docs-site && npm ci && npm run build
~~~

## Validar antes de producción

Usa siempre un site aislado y desechable. La suite de integración modifica datos durante
la prueba aunque termine con rollback. No se ejecuta contra el site productivo.

~~~bash
bench --site SITE_DESCARTABLE run-tests --app sgc
~~~

La versión de Frappe, el CI y la biblioteca de referencia se consultan en
[Biblioteca Frappe v16](../referencias/frappe/).

## Construir el overlay Docker

El Dockerfile overlay añade SGC sobre la imagen Frappe base y ejecuta el build de assets.
Antes de cambiar cualquier servicio, identifica la imagen activa y valida el Compose:

~~~bash
docker compose config --images
docker inspect --format '{{.Config.Image}}' CONTENEDOR_BACKEND
docker build --build-arg BASE_IMAGE=IMAGEN_ACTIVA -f deploy/Dockerfile.overlay -t IMAGEN_NUEVA .
docker compose config
~~~

El overlay aborta si el manifiesto de assets queda vacío. Conserva el tag anterior y pide
aprobación antes de recrear servicios críticos.

Después del despliegue, comprobar:

~~~bash
docker compose ps
curl -fsSI https://DOMINIO/desk
curl -fsSI https://DOMINIO/api/method/ping
~~~

## Contribuir

La app usa pre-commit con Ruff, ESLint, Prettier y pyupgrade:

~~~bash
cd apps/sgc
pre-commit install
~~~

Ver [Tests](../desarrollo/tests/) antes de enviar un cambio.
