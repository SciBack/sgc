---
title: Módulo Procesos (sgc_procesos)
description: El mapa de procesos institucional (ISO 21001) y el diagnóstico de Condiciones Básicas de Calidad (CBC) del licenciamiento.
---

El mapa de procesos institucional (ISO 21001) y el diagnóstico de las Condiciones
Básicas de Calidad (CBC) del licenciamiento institucional, que otorga la
Superintendencia Nacional de Educación Superior Universitaria (SUNEDU).

## Mapa de procesos

| DocType | Rol |
|---|---|
| **Proceso** | Un proceso institucional (código, tipo: estratégico/misional/soporte). |
| **Ficha Caracterizacion Proceso** | La ficha de caracterización de un Proceso: objetivo, alcance, responsable. |
| **Cambio Ficha** | Historial de cambios de una Ficha de Caracterización. |
| **Entrada Proceso** / **Salida Proceso** | Entradas y salidas documentadas de un Proceso. |
| **Actividad Proceso** | Las actividades que componen un Proceso. |
| **Interaccion Proceso** | Interacciones/dependencias entre procesos (mapa de procesos). |
| **Procedimiento** | Un procedimiento documentado asociado a un Proceso. |
| **Registro Proceso** | Registros de operación de un Proceso. |
| **Doc Proceso Link** | Vínculo entre un Proceso y un `Documento Controlado`. |
| **Indicador Proceso Link** | Vínculo entre un Proceso y un `Indicador` de gestión. |
| **Riesgo Proceso** | Vínculo entre un Proceso y un `Riesgo` (módulo Riesgos) que lo afecta. |

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
