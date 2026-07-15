---
title: Módulo Estructura (sgc_estructura)
description: El marco normativo contra el que se acredita, y la estructura organizacional sobre la que se aplica.
---

El marco normativo contra el que se acredita, y la estructura organizacional sobre la
que se aplica.

## Marco normativo

| DocType | Rol |
|---|---|
| **Marco Normativo** | Un modelo de acreditación cargable (p. ej. `CONEAU-Programas-2025`): nombre, ente emisor, escala de valoración asociada. |
| **Elemento Marco** | Árbol único (DocType Tree) que representa TODO el contenido normativo de un marco: dimensiones, factores, **estándares** (depth 2), **criterios** (depth 3) y **condiciones/CBC** — el campo `tipo` distingue el nivel (`Dimension` / `Factor` / `Estandar` / `Criterio` / `Condicion` / `Componente` / `Indicador`). Criterios de acreditación y Condiciones Básicas de Calidad (CBC) son el **mismo DocType** con distinto `tipo`. |
| **Escala Valoracion** | La escala de niveles de cumplimiento de un marco (p. ej. `CONEAU-NLLP`). |
| **Nivel Escala** | Cada nivel de una escala (NL/L/LP), con `sigla`, `etiqueta` y `descripcion`. |
| **Nivel Marco** | (auxiliar del árbol normativo). |

## Indicadores

| DocType | Rol |
|---|---|
| **Indicador** | Un indicador de gestión de la calidad (código `ID#`, categoría). |
| **Ficha Indicador** | La ficha técnica de un indicador: objetivo, valor referencial/umbral, interpretación, fuente de dato, fórmula. |
| **Indicador Criterio** | Vínculo entre un Indicador y el criterio/estándar normativo que sustenta. |

## Estructura organizacional

| DocType | Rol |
|---|---|
| **Unidad Organica** | Nodo de la estructura organizacional de la institución. |
| **Programa** | Un programa académico. |
| **Programa Sede** | La instancia de un Programa en una sede específica — es la unidad real sobre la que corre una Autoevaluación. |
| **Periodo Academico** | Periodo/ciclo académico usado para acotar mediciones y autoevaluaciones. |
