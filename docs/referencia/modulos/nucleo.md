---
title: Mejora continua (sgc_nucleo)
description: "La cadena de mejora: hallazgos, no conformidades, salidas no conformes, planes y acciones."
sidebar:
  order: 5
---

La cadena CAPA: lo que se detecta (hallazgos, no conformidades, salidas no conformes) y cómo se
trata (planes y acciones de mejora). El módulo conserva el nombre técnico `sgc_nucleo`.

## Cadena CAPA

| DocType | Rol |
|---|---|
| **Hallazgo** | Observación cualitativa (`Fortaleza` / `Debilidad` / `Oportunidad de mejora`) con origen polimórfico (Autoevaluación, Auditoría, Supervisión). |
| **No Conformidad** | No conformidad formal (`No conformidad mayor` / `menor` / `Observacion` / `Oportunidad de mejora`), con origen polimórfico (`origen_doctype` + `origen_id` + `origen_tipo`). |
| **Salida No Conforme** | El producto o servicio concreto que salió mal (ISO 9001 §8.7); si revela un fallo del sistema, se escala a No Conformidad (workflow f23). |
| **Plan Mejora** | Plan de acciones correctivas/preventivas, también de origen polimórfico. Rollup de avance desde sus Acciones. |
| **Accion Mejora** | Una acción concreta dentro de un Plan de Mejora (`Correctiva` / `Preventiva` / `Mejora`), con `avance_pct`, `fecha_compromiso` y semáforo. |

La cadena completa Hallazgo → No Conformidad → Plan → Acción se documenta en
[Manual de uso · No conformidades y mejora](../../../docs-site/src/content/docs/mejora-continua/index.md).
