---
title: Estado del producto
description: Los 18 módulos del SGC organizados en 4 bloques, con su estado de construcción real.
---

El SGC se organiza en **18 módulos** agrupados en 4 bloques. Esta página es el mapa del producto
y su estado real de construcción.

**Leyenda**

| | Significado |
|---|---|
| ✅ **Operativo** | Tiene lógica de negocio real (no solo el modelo de datos), está desplegado y verificado. |
| 🟡 **Parcial** | Funciona en parte, o depende de un dato/configuración externa para completarse. |
| 🔴 **Pendiente** | Existe el modelo de datos, pero aún sin lógica propia. |

:::note
"Operativo" significa que el módulo hace su trabajo, no que esté terminado para siempre: se sigue
puliendo con el uso. Un módulo 🔴 no está vacío — su modelo de datos ya existe y es usable como
registro; lo que falta es la lógica que lo automatiza.
:::

## Bloque A — Condiciones Básicas y transparencia

| Módulo | Estado | Detalle |
|---|---|---|
| **M01** Condiciones Básicas de Calidad | ✅ Operativo | Diagnóstico de las 8 CBC con semáforo, informe anual de cumplimiento y su PDF. |
| **M02** Portal de transparencia | 🟡 Parcial | Datos abiertos (CKAN) desplegado; la publicación/cosecha por el portal nacional queda para una fase posterior. |

## Bloque B — Gestión por procesos y documental

| Módulo | Estado | Detalle |
|---|---|---|
| **M03** Control documental | ✅ Operativo | Código SGC automático, versiones, flujo de tres firmas, historial de cambios y export de la Lista Maestra a Excel. |
| **M04** Procesos e indicadores de proceso | 🟡 Parcial | Los indicadores operan; las fichas de proceso esperan la carga del mapa de procesos institucional (es un dato, no código). |
| **M05** No conformidades | ✅ Operativo | Registro con validaciones incrementales por etapa y flujo hasta el cierre. |
| **M06** Auditorías internas | ✅ Operativo | Programa anual, ejecución de auditorías (equipo, criterios), hallazgos con escalamiento a No Conformidad e informe consolidado, con workflow. |

## Bloque C — Acreditación

| Módulo | Estado | Detalle |
|---|---|---|
| **M07** Roles y comités | 🟡 Parcial | RBAC con 13 roles y comités operando; falta acotar la visibilidad por programa. |
| **M08** Autoevaluación | ✅ Operativo | Motor que propone el nivel por estándar y la vigencia; el comité confirma el nivel oficial. |
| **M09** Evidencias de acreditación | ✅ Operativo | Carga de archivo o enlace, vigencia y trazabilidad N:M contra criterios y procesos. |
| **M10** Indicadores de acreditación | ✅ Operativo | Catálogo de indicadores con fichas y tablero. |
| **M11** Planes de mejora | ✅ Operativo | Planes y acciones con flujo, avance acumulado y semáforo por vencimiento. |
| **M12** Encuestas a grupos de interés | ✅ Operativo | Instrumentos aplicados a grupos de interés por periodo, con tabulación y agregación de resultados y workflow de campo. |
| **M13** Tablero ejecutivo | ✅ Operativo | Vista institucional: cobertura de autoevaluación, distribución de estándares por nivel, semáforo de CBC, riesgos abiertos y avance por programa. |
| **M14** Acreditación internacional | 🔴 Pendiente | Fase posterior. |
| **M15** Reportería BI | 🔴 Pendiente | Fase posterior. |

## Bloque D — Servicios transversales

| Módulo | Estado | Detalle |
|---|---|---|
| **M16** Seguridad, usuarios y roles | 🟡 Parcial | Autenticación por SSO y RBAC aplicados; falta segundo factor para administradores. |
| **M17** Notificaciones y alertas | 🟡 Parcial | Reglas de vencimiento activas (documentos, evidencias, planes y acciones), notificando en el sistema; el envío por correo requiere configurar la cuenta de correo saliente. |
| **M18** API de integración | 🔴 Pendiente | Interoperabilidad con sistemas académicos y entes externos. Fase posterior. |

## Resumen

**10 operativos** · **5 parciales** · **3 pendientes**.

El núcleo de un ciclo de acreditación completo — **M01 + M03 + M08 + M09**, con **M11** para la
mejora — está operativo: permite llevar un programa desde el marco normativo hasta el informe de
autoevaluación con sus evidencias trazadas.

---

*Última actualización: 2026-07-15.*
