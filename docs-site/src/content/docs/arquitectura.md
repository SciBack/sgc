---
title: Arquitectura
description: Stack técnico, capas del código y cómo se relacionan backend y frontend en el producto canónico SGC.
---

## Stack

| Capa | Tecnología |
|---|---|
| Backend | [Frappe Framework](https://frappeframework.com/) v16 (Python ≥3.14), PostgreSQL |
| Frontend (SPA) | Vue 3 + [frappe-ui](https://github.com/frappe/frappe-ui) + Vite + Tailwind CSS |
| Frontend (legado/Desk) | Desk nativo de Frappe (formularios auto-generados por DocType) |
| Reportes PDF | Motor Chrome de Frappe v16 (`pdf_generator="chrome"`) sobre Print Formats Jinja |
| Tests | Suite de integración Frappe (`bench run-tests`), factories reutilizables |

El repositorio es una **app Frappe estándar** (`bench get-app` / `bench install-app`).
Todo el dominio de negocio vive en DocTypes (definidos en `.json`) + controladores
Python (`.py`) junto a cada DocType, más módulos de lógica transversal en la raíz de
`sgc/`.

## Módulos de dominio

El código se organiza en **6 módulos Frappe**, cada uno con sus propios DocTypes bajo
`sgc/<modulo>/doctype/`:

```
sgc/
├── sgc_nucleo/       ← el corazón operativo: autoevaluación, documentos, evidencias, CAPA
├── sgc_estructura/   ← el marco normativo y la estructura organizacional
├── sgc_gobierno/     ← comités, políticas, objetivos, instrumentos de gestión
├── sgc_procesos/     ← mapa de procesos, CBC, informes de cumplimiento
├── sgc_riesgos/      ← gestión de riesgos y obligaciones con entes externos
└── sgc_auditoria/    ← auditoría interna y revisión por la dirección
```

Ver el detalle de DocTypes de cada uno en [Módulos](/sgc/modulos/nucleo/).

## Lógica transversal (fuera de los DocTypes)

Módulos Python en la raíz de `sgc/` que implementan la lógica que no pertenece a un
único DocType:

| Módulo | Responsabilidad |
|---|---|
| `scoring.py` | Motor de scoring de la autoevaluación (NL/L/LP) — **propone**, nunca confirma |
| `confirmacion.py` | Acción humana que confirma el nivel oficial y promueve la vigencia |
| `capa.py` | Cadena CAPA: genera Hallazgo → escala a No Conformidad → crea Plan de Mejora |
| `informe.py` | Consolida la autoevaluación y genera el informe PDF de acreditación |
| `lista_maestra.py` | Exporta a Excel la Lista Maestra de documentos controlados |
| `api.py` | Endpoints whitelisted de propósito general (login M365, catálogos) |
| `www/*.py` | Contextos de las páginas server-rendered de la SPA (`get_context`) |

## Frontend: SPA propia sobre frappe-ui

Frappe sirve dos interfaces sobre los mismos DocTypes:

1. **Desk** (nativo de Frappe): formularios auto-generados, siempre disponibles, usado
   para lo que la SPA todavía no cubre (p. ej. tablas hijas complejas en algunos
   informes).
2. **SPA propia** (`frontend/`, Vue 3 + frappe-ui): la interfaz pensada para el comité
   de calidad — más simple, en español, sin el ruido de campos técnicos del Desk.
   Se sirve bajo la ruta `/sgc/*` (catch-all definido en `hooks.py` vía
   `website_route_rules`, enrutado real por `vue-router` en el cliente).

La SPA es **genérica sobre el meta de cada DocType** (no hay un formulario hardcodeado
por tipo de documento): lee la definición del DocType vía `useDoctypeMeta` y renderiza
campos, tablas hijas y conexiones (Document Links) dinámicamente. Ver
[Frontend SPA](/sgc/desarrollo/frontend-spa/) para el detalle de componentes.

## Reportes PDF

Los informes (acreditación, diagnóstico CBC) se generan con Print Formats Jinja
usando el motor **Chrome** de Frappe v16 (soporta flexbox y colores CSS reales, a
diferencia del motor wkhtmltopdf legado). La consolidación de datos (`informe.py`,
`sgc_procesos/doctype/informe_cumplimiento/informe_cumplimiento.py`) es Python puro;
el Print Format solo maqueta.

## Separación agnóstico / institución (ADR-054)

Este repositorio es la **capa canónica** del producto: agnóstico a cualquier
universidad. Lo específico de una institución (dominio, SSO, branding, credenciales de
base de datos, integraciones locales) vive en una capa separada
(`instituciones/<cliente>/`) que overlaya esta base — nunca al revés. Cualquier
necesidad de un cliente se resuelve primero como un toggle genérico aquí; el overlay
institucional es el último recurso.
