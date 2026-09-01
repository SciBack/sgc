### SGC UPeU

Sistema de Gestion de la Calidad - UPeU (SciBack)

### Diseño

La SPA de SGC adopta **SciBack Design System 2.0.0**: núcleo visual canónico
en `frontend/src/styles/sciback-core.css` y capa de marca UPeU en
`frontend/src/styles/themes/upeu.css`. Los activos institucionales se toman de
la fuente autorizada `~/proyectos/upeu/branding/`.

### Documentación

Manuales de uso, referencia de módulos y guía de arquitectura en `docs-site/`
(Astro + Starlight), publicada en <https://sciback.github.io/sgc/>.

```bash
cd docs-site
npm install
npm run dev
```

Abre `http://localhost:4321/sgc`.

### Entorno de desarrollo

Para levantar el SGC completo en tu máquina (Frappe 16 + PostgreSQL + Redis,
en Docker) sigue la guía paso a paso:
**[`docs/desarrollo/entorno-local.md`](docs/desarrollo/entorno-local.md)**.
Cubre x86_64 y ARM64, y termina con el flujo de contribución.

Si ya tienes un bench funcionando, basta con instalar la app en él:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/SciBack/sgc --branch main
bench install-app sgc
```

La rama de la app es `main`. `version-16` es la rama del *framework* Frappe, no
la de esta app.

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/sgc
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
