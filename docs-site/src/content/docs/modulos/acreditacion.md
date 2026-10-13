---
title: Acreditación y licenciamiento (sgc_acreditacion)
description: Autoevaluación y evidencias, marcos normativos, diagnóstico CBC de SUNEDU y obligaciones ante entes externos.
sidebar:
  order: 4
---

Todo lo que la institución presenta ante quien la evalúa: la autoevaluación con fines de
acreditación y sus evidencias, los marcos normativos contra los que se mide, el diagnóstico
anual de condiciones básicas de calidad de la SUNEDU y las obligaciones con cada ente externo.

## Autoevaluación

| DocType | Rol |
|---|---|
| **Autoevaluacion** | El proceso de autoevaluación de un programa contra un marco normativo de acreditación (abrirla con un marco de licenciamiento se rechaza — ver `sgc/marcos.py`). Campos clave: `marco_normativo`, `programa_sede`, `avance_pct` (read-only, % de criterios valorados), `vigencia_propuesta` (read-only, propuesta del motor), `resultado_vigencia` (oficial, lo fija [confirmacion.py](../../manual-uso/autoevaluacion/)). |
| **Valoracion Criterio** | El juicio del comité sobre un criterio normativo puntual: `cumple` (`Cumple` / `Cumple parcial` / `No cumple` / `No aplica`) + `observacion`. Dispara el recálculo del estándar padre (`on_update`). |
| **Valoracion Estandar** | El nivel de un estándar (agregado de sus criterios) para una autoevaluación. `nivel_propuesto` lo escribe el motor (`scoring.py`); `nivel` (permlevel 1, oficial) solo lo escribe el humano vía `confirmacion.confirmar_nivel`. |

Ver el flujo completo en [Manual de uso · Autoevaluación](../../manual-uso/autoevaluacion/).

:::note[Vigencia: cuatro tramos en la norma, tres en el sistema]
`resultado_vigencia` aplica la Tabla 9 de los modelos de acreditación del Coneau
(Consejo de Evaluación, Acreditación y Certificación de la Calidad de la Educación
Universitaria), idéntica en el modelo de programas y en el institucional salvo el
último umbral:

| Niveles confirmados | Vigencia |
|---|---|
| Uno o más estándares en NL | En proceso de acreditación |
| Todos en L, o combinación L/LP | 3 años |
| Todos en LP | 6 años |
| Todos en LP **y** puntaje de la Tabla 10 | 8 años — 16 puntos en programas, 20 en institucional |

El cuarto tramo **no está implementado**: la opción existe en el campo y hay un
`puntaje_excelencia`, pero nadie lo calcula y los criterios de excelencia de la Tabla
10 no están cargados como elementos del marco, así que el techo real del motor son 6
años.
:::

## Evidencias

| DocType | Rol |
|---|---|
| **Evidencia** | Repositorio real de una evidencia (archivo adjunto o URL externa), con código autogenerado `EVD-AAAA-NNNN`, metadatos autocompletados (mime/tamaño/hash) y vigencia. |
| **Evidencia Enlace** | Child table de un solo campo (Link a Evidencia) usada como picklist rápido (Table MultiSelect) en `Cumplimiento CBC` y `Hallazgo Auditoria`. Al guardar cualquiera de esos dos documentos, se auto-sincroniza con Trazabilidad (una fila por cada combinación evidencia/destino que aún no exista, marcada `origen=Auto-sincronizado`) — así lo capturado por el picklist queda igual de visible para el informe oficial que un vínculo creado a mano. |
| **Trazabilidad** | El vínculo N:M real entre una Evidencia y un criterio normativo (`Elemento Marco`) o un proceso, con `tipo_vinculo` (Cumple/Soporta/Parcial) y `origen` (Directo/Propagado por crosswalk/Auto-sincronizado). Es lo que el informe de acreditación consume para citar evidencias. |

Ver [Manual de uso · Evidencias y trazabilidad](../../manual-uso/evidencias-trazabilidad/).

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

## Diagnóstico CBC (SUNEDU)

Las 8 CBC son las del Modelo de Licenciamiento Institucional (Resolución del Consejo
Directivo N.° 006-2015-SUNEDU/CD), no las de un modelo de acreditación: el
licenciamiento es obligatorio y se cumple o no se cumple. Que el informe sea **anual**
responde al artículo 13.5 de la Ley Universitaria —párrafo incorporado por la Ley
32105—, que incluye el «informe anual de cumplimiento» entre las herramientas de la
SUNEDU para verificar el cumplimiento continuo de las condiciones.

| DocType | Rol |
|---|---|
| **Cumplimiento CBC** | Tabla hija: el juicio de cumplimiento de UNA Condición Básica de Calidad (child de `Informe Cumplimiento`). |
| **Informe Cumplimiento** | El diagnóstico anual de las 8 CBC (`IAC-{año}`, autoname único por año). Al guardarse, auto-puebla las 8 condiciones si la tabla está vacía; consolida conteos y **semáforo** (Rojo si alguna no cumple / Ámbar si parcial / Verde si todas cumplen); exige justificación en toda CBC parcial o no cumplida; bloquea el estado "Presentado a SUNEDU" si queda alguna CBC sin evaluar. Genera el informe PDF (`Diagnostico CBC SUNEDU`). |

Ver [Manual de uso · Diagnóstico CBC](../../manual-uso/diagnostico-cbc/).

## Obligaciones ante entes externos

Los dos tipos de ente no juegan el mismo papel: el **regulador** —la Superintendencia Nacional
de Educación Superior Universitaria (SUNEDU)— vigila el licenciamiento, que es
obligatorio; las **acreditadoras** —el Sineace y su órgano operador, el Coneau— otorgan
un sello voluntario. Una obligación frente a cada uno tiene consecuencias distintas si
se incumple.

| DocType | Rol |
|---|---|
| **Ente Externo** | Un organismo externo con el que la institución tiene obligaciones: SUNEDU, Concytec (Consejo Nacional de Ciencia, Tecnología e Innovación Tecnológica), acreditadoras. |
| **Obligacion Ente** | Una obligación concreta (reporte, trámite, plazo) frente a un Ente Externo. |
| **Entrega Obligacion** | El registro de cumplimiento/entrega de una Obligación. |

Las obligaciones frente a la SUNEDU son recurrentes por diseño: desde la Ley 32105
(*El Peruano*, 5 de agosto de 2024) la licencia es de carácter permanente **condicionada
al cumplimiento continuo** de las condiciones básicas de calidad (art. 13.4 de la Ley
Universitaria), con evaluaciones periódicas inopinadas. No hay un trámite de renovación
que cierre el ciclo y libere de seguimiento.
