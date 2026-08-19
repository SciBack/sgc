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
| **M03** Control documental | ✅ | ❌ | Código SGC automático, versiones, flujo de tres firmas, historial y export de la Lista Maestra. **No hay ningún documento cargado**: los de demostración se retiraron. El Requerimiento define once tipos (política, mapa, manual, fichas, procedimientos…) y falta el primero. |
| **M04** Procesos e indicadores de proceso | ✅ | 🟡 | **22 procesos oficiales cargados**, con las denominaciones del Mapa de Procesos v8.0 aprobado, y sus **22 indicadores de desempeño** con fórmula, periodicidad y meta (dato real). Falta el eslabón del medio: las **fichas de caracterización (SIPOC)**, una por proceso. Hasta que lleguen, el motor reporta cada proceso como «sin ficha» — que es el reflejo honesto de lo que falta, no un fallo. |
| **M05** No conformidades | ✅ | ❌ | Registro con validaciones incrementales por etapa y flujo hasta el cierre. **No hay ninguna no conformidad registrada**: las de demostración se retiraron y aún no se ha levantado ninguna real. |
| **M06** Auditorías internas | ✅ | ❌ | Programa anual, ejecución con equipo y criterios, hallazgos con escalamiento a No Conformidad, informe consolidado y workflow. **No hay ninguna auditoría registrada**: los datos de demostración se retiraron y aún no se ha ejecutado ninguna real. |

## Bloque C — Acreditación

| Módulo | Construido | En uso | Estado real y qué falta |
|---|---|---|---|
| **M07** Roles y comités | ✅ | 🟡 | RBAC de 14 roles sobre los 46 DocTypes de negocio (ver [RBAC](../desarrollo/rbac/)). El acotamiento de visibilidad por programa está construido y listo para activarse. **Hay una sola cuenta de persona activa** (más una cuenta de servicio para los conectores); faltan las altas del comité de calidad. |
| **M08** Autoevaluación | ✅ | ❌ | Motor que propone el nivel por estándar y la vigencia; el comité confirma el nivel oficial. **No hay ninguna autoevaluación en curso.** La que existía (`AE-ENF-LIMA-2026I`) la había generado una prueba automatizada, no el comité, y se retiró junto con el resto de datos de demostración. Ningún criterio ha sido valorado todavía por una persona. |
| **M09** Evidencias de acreditación | ✅ | ❌ | Carga de archivo o enlace, vigencia y trazabilidad N:M contra criterios y procesos. **No hay ninguna evidencia real cargada**, y por tanto ningún criterio tiene evidencia trazada. Es el principal frente abierto. |
| **M10** Indicadores de acreditación | ✅ | 🟡 | Catálogo de 93 indicadores con fichas (71 de acreditación + 22 de proceso) y tablero, más conectores automáticos hacia las fuentes institucionales. **12 indicadores tienen dato real**, alimentados a diario por el almacén de datos institucional; el resto espera fuente (ver M04 y M12). El panel que los muestra ya está desplegado. |
| **M11** Planes de mejora | ✅ | ❌ | Planes y acciones con flujo, avance acumulado y semáforo por vencimiento. **No hay ningún plan de mejora registrado**: el que existía venía de la prueba automatizada de M08 y se retiró. |
| **M12** Encuestas a grupos de interés | ✅ | ❌ | Instrumentos por periodo con tabulación, promedio ponderado y workflow de campo. Al cerrar una aplicación, **sus resultados se publican como indicadores automáticamente**. Falta registrar los instrumentos reales de la institución. |
| **M13** Tablero ejecutivo | ✅ | 🟡 | Vista institucional: cobertura de autoevaluación, niveles por estándar, semáforo de CBC, avance por programa, riesgos, auditorías y última revisión por la dirección. Refleja el dato que exista; hoy muestra los procesos, los marcos normativos y los indicadores del almacén de datos, que es lo único cargado. |
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

**En uso con dato institucional real:** 1 módulo plenamente (**M17** notificaciones), 5
parcialmente y 9 todavía sin dato real.

### Qué significa esto

La **capacidad está construida y verificada**: un ciclo completo de acreditación —del marco
normativo al informe, con trazabilidad de evidencias, planes de mejora y notificaciones— existe,
está desplegado y respaldado por pruebas automatizadas.

Lo que falta ya **no es desarrollo, es carga de información institucional**. Lo que hoy es dato real
son los 22 procesos oficiales del Mapa, los 3 marcos normativos con sus 185 elementos y los
indicadores que se alimentan solos desde las fuentes institucionales. **La cadena de acreditación
propiamente dicha todavía no ha sido ejercida por nadie.** El sistema se vació de datos de
demostración el 19 de agosto, de modo que lo que se ve es exactamente lo que hay: los módulos
esperan que las áreas dueñas del dato carguen evidencias, documentos, instrumentos de encuesta y
las fichas de caracterización de proceso.

### Hitos

| Cuándo | Qué | De qué depende |
|---|---|---|
| **Agosto 2026** | Informe de Autoevaluación de la EP de Enfermería (CONEAU) | Cargar las evidencias y vincularlas a los criterios (**M09**), y que el comité valore los criterios en el sistema (**M08**). **A la fecha no se ha iniciado**: no hay ninguna evidencia real cargada ni ninguna valoración hecha por una persona. |
| **31 de marzo de 2027** | Informe Anual de Cumplimiento (SUNEDU) | Generar el diagnóstico de las 8 CBC con dato real (**M01**) |

---

*Última actualización: 2026-08-19.*
