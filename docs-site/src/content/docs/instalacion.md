---
title: Instalación
description: Cómo instalar la app SGC en un bench Frappe.
---

## Requisitos

- Un [bench](https://github.com/frappe/bench) Frappe funcionando, con Frappe **v16**
  (branch `version-16`).
- PostgreSQL como base de datos del site (la app usa tipos/consultas compatibles con
  Postgres; no se ha validado sobre MariaDB).
- Node **24.15** y npm **11.12** para compilar la SPA (`frontend/`) y la
  documentación (`docs-site/`). Python ≥3.14 para la app.

## Instalar la app

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/SciBack/sgc --branch version-16
bench --site <tu-site> install-app sgc
```

Tras instalar, correr las migraciones si vienes de una versión anterior:

```bash
bench --site <tu-site> migrate
```

## Compilar la SPA

La SPA (`frontend/`) se compila con Vite y sus assets se sirven desde
`sgc/public/frontend/`. En un bench estándar, `bench build --app sgc` la incluye en el
pipeline normal de build de Frappe.

Antes de publicar, verificar desde la raíz de la app:

```bash
python -m unittest sgc.tests.test_login_assets
python -m compileall -q sgc
cd frontend
npm ci --ignore-scripts
npm run test:login-dom
npm run verify:login-design
npm run build
```

El build de documentación se comprueba por separado:

```bash
cd docs-site
npm ci
npm run build
```

## Portada de inicio de sesión

- Acceso normal: `/login?redirect-to=/sgc`.
- Acceso local de emergencia (*break-glass*): `/login?login_local=1`. Esta ruta
  conserva el formulario nativo de Frappe y omite la portada institucional.
- Métricas públicas: `/api/method/sgc.login_portada.metricas_portada`.
- El video `oficinas-dti.mp4` y su póster se reutilizan provisionalmente desde
  Pulso DTI; junto con el logo y las fuentes se sirven desde
  `sgc/public/media/login/` y `sgc/public/fonts/`. En despliegues Frappe quedan
  expuestos bajo `/assets/sgc/media/login/` y `/assets/sgc/fonts/`.

La validación completa del backend requiere un bench real. Antes de desplegar se
deben ejecutar en la imagen o EC2, sin marcarlas como aprobadas solo con la
verificación local:

```bash
bench --site <tu-site> run-tests --app sgc --module sgc.tests.test_login_portada
bench --site <tu-site> run-tests --app sgc
```

## Construir y desplegar el overlay Docker

`deploy/Dockerfile.overlay` añade el checkout de SGC sobre la imagen backend que
ya está activa y ejecuta `bench build --app sgc`. La imagen base se obtiene de la
configuración efectiva del servicio backend; no se supone ni se fija un tag:

```bash
docker compose config --images
docker inspect --format '{{.Config.Image}}' <contenedor-backend-activo>
docker build --build-arg BASE_IMAGE=<imagen-backend-activa> -f deploy/Dockerfile.overlay -t <imagen-overlay-nueva> .
```

Actualizar el tag del backend en el archivo Compose del entorno, validar primero
con `docker compose config` y conservar tanto el tag anterior como una copia del
Compose efectivo. **No reiniciar ni recrear servicios o contenedores críticos sin
aprobación previa.**

Para rollback, restaurar juntos el tag/Compose anterior y los assets compatibles
de `sgc/public/css/`, `sgc/public/js/` y `sgc/public/media/`; después validar el
Compose antes de solicitar la recreación del backend. No mezclar CSS o JS nuevos
con media o imagen backend antiguas.

Tras el despliegue, comprobar:

```bash
docker compose ps
curl -fsS 'https://<dominio>/api/method/sgc.login_portada.metricas_portada'
curl -fsSI 'https://<dominio>/login?redirect-to=/sgc'
curl -fsSI 'https://<dominio>/assets/sgc/media/login/oficinas-dti-poster.jpg'
```

Completar la verificación en navegador en escritorio, tableta, móvil,
`prefers-reduced-motion: reduce`, fallo de la API y modo `login_local=1`; confirmar
que no haya overflow horizontal, que el enlace SSO conserve sus parámetros y que
el formulario nativo siga disponible en *break-glass*.

## Datos de arranque

El módulo `sgc/setup/` contiene los scripts `fN_*.py` que siembran el modelo de datos
base (estructura organizacional, marco normativo, workflows, RBAC, notificaciones). Se
ejecutan una vez por site, en orden, vía `bench execute`:

```bash
bench --site <tu-site> execute sgc.setup.f1_run_all.run
bench --site <tu-site> execute sgc.setup.f2_run_all.run
# ... ver sgc/setup/ para el resto (f3b_rbac, f4_workflow_mejora, f5_workflow_documental,
# f6_informe_cbc, f7_notificaciones)
```

Cada script es **idempotente**: puede reejecutarse sin duplicar datos.

## Contribuir

La app usa `pre-commit` para formateo y linting (`ruff`, `eslint`, `prettier`,
`pyupgrade`):

```bash
cd apps/sgc
pre-commit install
```

Ver [Tests](/sgc/desarrollo/tests/) para correr la suite antes de enviar un cambio.

## Licencia

MIT.
