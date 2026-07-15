---
title: Evidencias y trazabilidad
description: Cómo cargar evidencias y vincularlas a criterios o procesos vía Trazabilidad.
---

## Cargar una evidencia

Una **Evidencia** puede ser:

- Un **archivo** adjunto (hasta 50 MB) — el sistema autocompleta mime, tamaño y hash
  desde el `File` subido.
- Un **enlace** (`enlace_url`), cuando la evidencia vive fuera del sistema.

Se exige al menos uno de los dos (archivo o URL) para guardar. El código se genera
automáticamente (`EVD-AAAA-NNNN`).

## Vincular la evidencia a un criterio o proceso: Trazabilidad

El vínculo real entre una Evidencia y lo que sustenta (un criterio del marco
normativo, o un proceso) es el DocType **Trazabilidad** — una relación **N:M**: una
evidencia puede sustentar varios criterios, y un criterio puede tener varias
evidencias.

Cada Trazabilidad registra:

- `tipo_vinculo`: `Cumple` / `Soporta` / `Parcial`.
- `origen`: `Directo` (la evidencia aplica tal cual) o vía crosswalk (mapeo entre
  marcos normativos distintos).
- `vigencia`: una evidencia vencida se marca automáticamente.

Se crea/gestiona desde la ficha de la Evidencia (bloque de conexiones — "Document
Links" de Frappe), no como un campo de tabla hija.

## Consultar evidencias desde un criterio

Al valorar un criterio en la [autoevaluación](/sgc/manual-uso/autoevaluacion/), la interfaz muestra
las evidencias ya vinculadas a ese criterio mediante una consulta inversa sobre
Trazabilidad (código, título, badge de estado, enlace al archivo) — así el comité no
tiene que ir a buscar la evidencia en otra pantalla.

## Qué evidencia exige "Válida"

Una Evidencia solo puede marcarse como `Valida` si tiene **al menos una Trazabilidad**
— una evidencia sin ningún criterio o proceso vinculado no cuenta como válida para
efectos de acreditación.

## Consumo por el informe

El informe de acreditación (`informe.py`) lee las Trazabilidades de cada criterio para
citar sus evidencias de soporte en el PDF final — por eso toda evidencia relevante
**debe** pasar por Trazabilidad, no solo quedar cargada.
