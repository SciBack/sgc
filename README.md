### SGC UPeU

Sistema de Gestion de la Calidad - UPeU (SciBack)

### Documentación

Manuales de uso, referencia de módulos y guía de arquitectura en `docs/`
(MkDocs Material):

```bash
pip install -r docs/requirements.txt
mkdocs serve
```

Abre `http://127.0.0.1:8000`.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch version-16
bench install-app sgc
```

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
