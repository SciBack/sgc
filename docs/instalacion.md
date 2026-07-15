# Instalación

## Requisitos

- Un [bench](https://github.com/frappe/bench) Frappe funcionando, con Frappe **v16**
  (branch `version-16`).
- PostgreSQL como base de datos del site (la app usa tipos/consultas compatibles con
  Postgres; no se ha validado sobre MariaDB).
- Node ≥20 y Python ≥3.14 para compilar la SPA (`frontend/`).

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

Ver [Tests](desarrollo/tests.md) para correr la suite antes de enviar un cambio.

## Licencia

MIT.
