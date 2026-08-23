---
title: Módulo Estructura (sgc_estructura)
description: Los marcos normativos contra los que se evalúa la institución, y la estructura organizacional sobre la que se aplican.
---

Los marcos normativos contra los que se evalúa la institución —tanto el
**licenciamiento** obligatorio como la **acreditación** voluntaria— y la estructura
organizacional sobre la que se aplican.

## Marco normativo

| DocType | Rol |
|---|---|
| **Marco Normativo** | Un modelo cargable (p. ej. `CONEAU-Programas-2025`, `CONEAU-Institucional-2026` o `CBC-SUNEDU-2026`): nombre, ente emisor, `alcance` y escala de valoración asociada. El **`alcance`** (`Licenciamiento` / `Acreditación de programa` / `Acreditación institucional` / `Gestión interna`) es lo que separa los tres mundos normativos: `sgc/marcos.py` lo consulta para que una autoevaluación rechace un marco de licenciamiento y un informe de cumplimiento rechace uno de acreditación. |
| **Elemento Marco** | Árbol único (DocType Tree) que representa TODO el contenido normativo de un marco: dimensiones, factores, **estándares** (depth 2), **criterios** (depth 3) y **condiciones/CBC** — el campo `tipo` distingue el nivel (`Dimension` / `Factor` / `Estandar` / `Criterio` / `Condicion` / `Componente` / `Indicador`). Criterios de acreditación y Condiciones Básicas de Calidad (CBC) son el **mismo DocType** con distinto `tipo`. |
| **Escala Valoracion** | La escala de niveles de cumplimiento de un marco (p. ej. `CONEAU-NLLP`). |
| **Nivel Escala** | Cada nivel de una escala (NL/L/LP), con `sigla`, `etiqueta` y `descripcion`. |
| **Nivel Marco** | (auxiliar del árbol normativo). |

:::note[`reglas_vigencia` existe pero todavía nadie la lee]
`Marco Normativo` tiene un campo `reglas_vigencia` (JSON) para que cada marco declare
su propia regla de vigencia. Hoy no lo consulta nadie: la regla vive fija en
`sgc/scoring.py`, igual para los dos modelos de acreditación del Coneau (Consejo de
Evaluación, Acreditación y Certificación de la Calidad de la Educación Universitaria).
Hoy funciona porque sus tres primeros tramos coinciden, pero el umbral del tramo de 8
años **sí difiere** entre ellos: 16 puntos de la Tabla 10 en el modelo de programas y
20 en el institucional. Al implementar ese tramo hay que leer el campo, no ampliar el
código.
:::

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
