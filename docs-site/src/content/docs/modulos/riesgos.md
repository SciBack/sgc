---
title: Módulo Riesgos (sgc_riesgos)
description: Gestión de riesgos institucionales y de las obligaciones con entes externos.
---

Gestión de riesgos institucionales y de las obligaciones con entes externos
(reguladores, acreditadores).

| DocType | Rol |
|---|---|
| **Riesgo** | Un riesgo identificado (descripción, categoría). |
| **Matriz Riesgo** | La matriz de riesgos (probabilidad × impacto) de la institución o un proceso. |
| **Evaluacion Riesgo** | Una evaluación puntual de un Riesgo dentro de una Matriz. |
| **Tratamiento Riesgo** | El plan de tratamiento/mitigación de un Riesgo evaluado. |
| **Riesgo Enlace** | Vínculo genérico de un Riesgo con otras entidades del sistema (proceso, criterio). |
| **Ente Externo** | Un organismo externo con el que la institución tiene obligaciones (SUNEDU, CONCYTEC, acreditadoras). |
| **Obligacion Ente** | Una obligación concreta (reporte, trámite, plazo) frente a un Ente Externo. |
| **Entrega Obligacion** | El registro de cumplimiento/entrega de una Obligación. |

Este módulo conecta con `sgc_procesos` vía **Riesgo Proceso** (el riesgo puede
asociarse a un proceso específico del mapa institucional).
