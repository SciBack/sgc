---
title: Módulo Riesgos (sgc_riesgos)
description: Gestión de riesgos institucionales y de las obligaciones con entes externos.
---

Gestión de riesgos institucionales y de las obligaciones con entes externos. Los dos
tipos de ente no juegan el mismo papel: el **regulador** —la Superintendencia Nacional
de Educación Superior Universitaria (SUNEDU)— vigila el licenciamiento, que es
obligatorio; las **acreditadoras** —el Sineace y su órgano operador, el Coneau— otorgan
un sello voluntario. Una obligación frente a cada uno tiene consecuencias distintas si
se incumple.

| DocType | Rol |
|---|---|
| **Riesgo** | Un riesgo identificado (descripción, categoría). |
| **Matriz Riesgo** | La matriz de riesgos (probabilidad × impacto) de la institución o un proceso. |
| **Evaluacion Riesgo** | Una evaluación puntual de un Riesgo dentro de una Matriz. |
| **Tratamiento Riesgo** | El plan de tratamiento/mitigación de un Riesgo evaluado. |
| **Riesgo Enlace** | Vínculo genérico de un Riesgo con otras entidades del sistema (proceso, criterio). |
| **Ente Externo** | Un organismo externo con el que la institución tiene obligaciones: SUNEDU, Concytec (Consejo Nacional de Ciencia, Tecnología e Innovación Tecnológica), acreditadoras. |
| **Obligacion Ente** | Una obligación concreta (reporte, trámite, plazo) frente a un Ente Externo. |
| **Entrega Obligacion** | El registro de cumplimiento/entrega de una Obligación. |

Este módulo conecta con `sgc_procesos` vía **Riesgo Proceso** (el riesgo puede
asociarse a un proceso específico del mapa institucional).

Las obligaciones frente a la SUNEDU son recurrentes por diseño: desde la Ley 32105
(*El Peruano*, 5 de agosto de 2024) la licencia es de carácter permanente **condicionada
al cumplimiento continuo** de las condiciones básicas de calidad (art. 13.4 de la Ley
Universitaria), con evaluaciones periódicas inopinadas. No hay un trámite de renovación
que cierre el ciclo y libere de seguimiento.
