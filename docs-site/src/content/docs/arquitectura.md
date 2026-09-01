---
title: Arquitectura
description: Stack técnico, capas del código y relación entre el dominio SGC y Frappe.
---

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Frappe Framework v16.32.0, Python 3.14 o posterior, PostgreSQL |
| Interfaz | Desk nativo de Frappe v16 y Workspace SGC |
| Reportes PDF | Motor Chrome de Frappe v16 sobre Print Formats Jinja |
| Tests | Suite de integración Frappe con factories reutilizables |

El repositorio es una app Frappe estándar. El dominio de negocio vive en DocTypes definidos
en JSON, sus controladores Python y módulos transversales bajo sgc.

## Módulos de dominio

~~~text
sgc/
├── sgc_nucleo/       corazón operativo: autoevaluación, documentos, evidencias y CAPA
├── sgc_estructura/   marcos normativos y estructura organizacional
├── sgc_gobierno/     comités, políticas, objetivos e instrumentos
├── sgc_procesos/     mapa de procesos, CBC e informes de cumplimiento
├── sgc_riesgos/      riesgos y obligaciones con entes externos
└── sgc_auditoria/    auditoría interna y revisión por la dirección
~~~

## Lógica transversal

| Módulo | Responsabilidad |
|---|---|
| marcos.py | Alcance de cada marco y guards que impiden cruzarlos |
| scoring.py | Motor de scoring: propone, nunca confirma |
| confirmacion.py | Confirmación humana del nivel oficial y vigencia |
| capa.py | Cadena CAPA: Hallazgo, No Conformidad y Plan de Mejora |
| informe.py | Consolidación y PDF de acreditación |
| lista_maestra.py | Exportación Excel de la Lista Maestra |
| api.py | Endpoints whitelisted de propósito general |

## Interfaz: Desk y Workspace SGC

La interfaz vigente es el **Desk nativo de Frappe v16**, con un Workspace SGC generado por
f18_workspace.py. Frappe resuelve formularios, listas, tablas hijas, acciones de workflow y
permisos desde los metadatos de los DocTypes; existe una sola fuente de verdad entre
interfaz, reglas de negocio y seguridad.

## Reportes PDF

Los informes de acreditación y CBC usan Print Formats Jinja sobre el motor Chrome de
Frappe v16. La consolidación de datos es Python puro; el Print Format solo maqueta.

## Separación canónico / institución

Este repositorio es la capa canónica del producto. Dominio, SSO, branding, credenciales e
integraciones de una institución viven en su capa de cliente, nunca al revés.

Ver [Biblioteca Frappe v16](../referencias/frappe/) para la referencia externa fijada.
