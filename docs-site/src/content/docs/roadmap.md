---
title: Estado del producto
description: Los 18 módulos del SGC en dos ejes — lo construido y lo que está realmente en uso con dato institucional.
---

El SGC se organiza en **18 módulos** agrupados en 4 bloques. Esta página los mide en **dos ejes
distintos**, porque confundirlos da una idea equivocada del avance:

| Eje | Qué responde | Quién lo mueve |
|---|---|---|
| **Construido** | ¿La funcionalidad existe, está desplegada y verificada? | Desarrollo |
| **En uso** | ¿Está operando con **dato institucional real**? | Calidad, DPGC y las áreas dueñas del dato |

Un módulo puede estar **construido ✅ y en uso ❌** a la vez: la herramienta funciona, pero todavía
nadie la alimenta con datos reales. Hoy ese es el caso de buena parte del sistema, y decirlo es
deliberado: mezclar ambos ejes en una sola cifra sobreestima el avance.

**Leyenda de cada eje**

| | Construido | En uso |
|---|---|---|
| ✅ | Lógica de negocio real, desplegada y verificada | Operando con dato institucional real |
| 🟡 | Funciona en parte o depende de configuración externa | Con dato real, pero por debajo de lo comprometido |
| ❌ 🔴 | Solo el modelo de datos, sin lógica propia | Sin dato real (vacío o solo datos de demostración) |

:::caution[Cómo leer esta página]
Los datos de **demostración** (identificados con `[DEMO]`) no cuentan como uso: existen para que el
sistema pueda recorrerse y evaluarse, y se retiran cuando llega el dato real. Un módulo que solo
tiene datos demo aparece como **en uso ❌**.
:::

## Bloque A — Condiciones Básicas y transparencia

| Módulo | Construido | En uso | Estado real y qué falta |
|---|---|---|---|
| **M01** Condiciones Básicas de Calidad | ✅ | ❌ | Las 8 CBC cargadas (43 elementos), diagnóstico con semáforo e informe en PDF. **Aún no se ha generado ningún informe** con datos reales. |
| **M02** Portal de transparencia | 🟡 | ❌ | Datos abiertos (CKAN) desplegado; la publicación y cosecha por el portal nacional queda para fase posterior. |

## Bloque B — Gestión por procesos y documental

| Módulo | Construido | En uso | Estado real y qué falta |
|---|---|---|---|
| **M03** Control documental | ✅ | ❌ | Código SGC automático, versiones, flujo de tres firmas, historial y export de la Lista Maestra. **Los 5 documentos existentes son de demostración**; faltan los documentos reales del SGC. |
| **M04** Procesos e indicadores de proceso | ✅ | 🟡 | **22 procesos oficiales cargados** (dato real). El motor de indicadores por proceso está desplegado, pero espera las **fichas de caracterización (SIPOC)** del Mapa de Procesos: hoy hay una sola, de demostración. |
| **M05** No conformidades | ✅ | 🟡 | Registro con validaciones incrementales por etapa y flujo hasta el cierre. **1 no conformidad real** en curso. |
| **M06** Auditorías internas | ✅ | ❌ | Programa anual, ejecución con equipo y criterios, hallazgos con escalamiento a No Conformidad, informe consolidado y workflow. **Todo el dato existente es de demostración**: aún no se ha ejecutado una auditoría real en el sistema. |

## Bloque C — Acreditación

| Módulo | Construido | En uso | Estado real y qué falta |
|---|---|---|---|
| **M07** Roles y comités | ✅ | 🟡 | RBAC de 14 roles sobre los 46 DocTypes de negocio (ver [RBAC](../desarrollo/rbac/)). El acotamiento de visibilidad por programa está construido y listo para activarse. **3 usuarios operando.** |
| **M08** Autoevaluación | ✅ | ✅ | Motor que propone el nivel por estándar y la vigencia; el comité confirma el nivel oficial. **En uso real: la autoevaluación de la EP de Enfermería, con sus 53 criterios valorados y 10 estándares con nivel confirmado.** |
| **M09** Evidencias de acreditación | ✅ | ❌ | Carga de archivo o enlace, vigencia y trazabilidad N:M contra criterios y procesos. **No hay ninguna evidencia real cargada**, y por tanto ningún criterio tiene evidencia trazada. Es el principal frente abierto. |
| **M10** Indicadores de acreditación | ✅ | 🟡 | Catálogo de 66 indicadores con fichas y tablero, más conectores automáticos hacia las fuentes institucionales. **7 indicadores (10.6%) tienen dato real**; el resto espera fuente (ver M04 y M12). |
| **M11** Planes de mejora | ✅ | 🟡 | Planes y acciones con flujo, avance acumulado y semáforo por vencimiento. **1 plan de mejora real** en curso. |
| **M12** Encuestas a grupos de interés | ✅ | ❌ | Instrumentos por periodo con tabulación, promedio ponderado y workflow de campo. Al cerrar una aplicación, **sus resultados se publican como indicadores automáticamente**. Falta registrar los instrumentos reales de la institución. |
| **M13** Tablero ejecutivo | ✅ | 🟡 | Vista institucional: cobertura de autoevaluación, niveles por estándar, semáforo de CBC, avance por programa, riesgos, auditorías y última revisión por la dirección. Refleja el dato que exista. |
| **M14** Acreditación internacional | 🔴 | — | Fase posterior. |
| **M15** Reportería BI | 🔴 | — | Fase posterior. Vinculada a la iniciativa de **Data Mart institucional**, hoy en evaluación. |

## Bloque D — Servicios transversales

| Módulo | Construido | En uso | Estado real y qué falta |
|---|---|---|---|
| **M16** Seguridad, usuarios y roles | 🟡 | 🟡 | Autenticación por SSO institucional y RBAC aplicados. **Falta el segundo factor (MFA)** para cuentas administrativas. |
| **M17** Notificaciones y alertas | ✅ | ✅ | Reglas de vencimiento (documentos, evidencias, planes y acciones) **notificando por correo real** al responsable de calidad y a quien tiene el registro a cargo. |
| **M18** API de integración | 🔴 | — | Interoperabilidad con sistemas académicos y entes externos. Fase posterior. |

## Resumen

**Construido:** 13 operativos · 2 parciales · 3 pendientes. Los 3 pendientes son de fase posterior,
fuera del alcance comprometido para esta etapa.

**En uso con dato institucional real:** 2 módulos plenamente (**M08** autoevaluación y **M17**
notificaciones), 7 parcialmente y 6 todavía sin dato real.

### Qué significa esto

La **capacidad está construida y verificada**: un ciclo completo de acreditación —del marco
normativo al informe, con trazabilidad de evidencias, planes de mejora y notificaciones— existe,
está desplegado y respaldado por pruebas automatizadas.

Lo que falta ya **no es desarrollo, es carga de información institucional**. El sistema tiene hoy
una autoevaluación real en curso (Enfermería), los 22 procesos oficiales del Mapa y los indicadores
que se alimentan solos desde las fuentes institucionales. Los demás módulos esperan que las áreas
dueñas del dato carguen evidencias, documentos, instrumentos de encuesta y fichas de proceso.

### Hitos

| Cuándo | Qué | De qué depende |
|---|---|---|
| **Agosto 2026** | Informe de Autoevaluación de la EP de Enfermería (CONEAU) | Cargar las evidencias y vincularlas a los criterios (**M09**) |
| **31 de marzo de 2027** | Informe Anual de Cumplimiento (SUNEDU) | Generar el diagnóstico de las 8 CBC con dato real (**M01**) |

---

*Última actualización: 2026-07-27.*
