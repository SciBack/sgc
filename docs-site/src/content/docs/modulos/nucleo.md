---
title: Módulo Núcleo (sgc_nucleo)
description: Autoevaluación, control documental, evidencias y la cadena CAPA de mejora continua.
---

El corazón operativo del sistema: la autoevaluación de acreditación, el control
documental, las evidencias y la cadena CAPA de mejora continua.

## Autoevaluación

| DocType | Rol |
|---|---|
| **Autoevaluacion** | El proceso de autoevaluación de un programa contra un marco normativo. Campos clave: `marco_normativo`, `programa_sede`, `avance_pct` (read-only, % de criterios valorados), `vigencia_propuesta` (read-only, propuesta del motor), `resultado_vigencia` (oficial, lo fija [confirmacion.py](../../manual-uso/autoevaluacion/)). |
| **Valoracion Criterio** | El juicio del comité sobre un criterio normativo puntual: `cumple` (`Cumple` / `Cumple parcial` / `No cumple` / `No aplica`) + `observacion`. Dispara el recálculo del estándar padre (`on_update`). |
| **Valoracion Estandar** | El nivel de un estándar (agregado de sus criterios) para una autoevaluación. `nivel_propuesto` lo escribe el motor (`scoring.py`); `nivel` (permlevel 1, oficial) solo lo escribe el humano vía `confirmacion.confirmar_nivel`. |

Ver el flujo completo en [Manual de uso · Autoevaluación](../../manual-uso/autoevaluacion/).

## Control documental (ISO 21001 §7.5)

| DocType | Rol |
|---|---|
| **Documento Controlado** | Un documento del SGC con ciclo de vida (código autogenerado `[PROCESO]-[SIGLA]-[NNN]`, versión, workflow de aprobación, revisión periódica). |
| **Cambio Documento** | Tabla hija: historial de cambios de versión de un Documento Controlado (motivo, versión anterior/nueva). |

Ver [Manual de uso · Control documental](../../manual-uso/control-documental/).

## Evidencias

| DocType | Rol |
|---|---|
| **Evidencia** | Repositorio real de una evidencia (archivo adjunto o URL externa), con código autogenerado `EVD-AAAA-NNNN`, metadatos autocompletados (mime/tamaño/hash) y vigencia. |
| **Evidencia Enlace** | Child table de un solo campo (Link a Evidencia) usada como picklist rápido (Table MultiSelect) en `Cumplimiento CBC` y `Hallazgo Auditoria`. Al guardar cualquiera de esos dos documentos, se auto-sincroniza con Trazabilidad (una fila por cada combinación evidencia/destino que aún no exista, marcada `origen=Auto-sincronizado`) — así lo capturado por el picklist queda igual de visible para el informe oficial que un vínculo creado a mano. |
| **Trazabilidad** | El vínculo N:M real entre una Evidencia y un criterio normativo (`Elemento Marco`) o un proceso, con `tipo_vinculo` (Cumple/Soporta/Parcial) y `origen` (Directo/Propagado por crosswalk/Auto-sincronizado). Es lo que el informe de acreditación consume para citar evidencias. |

Ver [Manual de uso · Evidencias y trazabilidad](../../manual-uso/evidencias-trazabilidad/).

## Mejora continua (CAPA)

| DocType | Rol |
|---|---|
| **Hallazgo** | Observación cualitativa (`Fortaleza` / `Debilidad` / `Oportunidad de mejora`) con origen polimórfico (Autoevaluación, Auditoría, Supervisión). |
| **No Conformidad** | No conformidad formal (`No conformidad mayor` / `menor` / `Observacion` / `Oportunidad de mejora`), con origen polimórfico (`origen_doctype` + `origen_id` + `origen_tipo`). |
| **Plan Mejora** | Plan de acciones correctivas/preventivas, también de origen polimórfico. Rollup de avance desde sus Acciones. |
| **Accion Mejora** | Una acción concreta dentro de un Plan de Mejora (`Correctiva` / `Preventiva` / `Mejora`), con `avance_pct`, `fecha_compromiso` y semáforo. |

La cadena completa Hallazgo → No Conformidad → Plan → Acción se documenta en
[Manual de uso · No conformidades y mejora](../../manual-uso/no-conformidades-mejora/).

## Otros

| DocType | Rol |
|---|---|
| **Valor Indicador** | Medición puntual de un indicador de gestión en el tiempo. |
