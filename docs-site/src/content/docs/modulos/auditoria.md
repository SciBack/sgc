---
title: Módulo Auditoría (sgc_auditoria)
description: Auditoría interna del sistema de gestión y revisión periódica por la dirección.
---

Auditoría interna del sistema de gestión y revisión periódica por la dirección
(ISO 9001 §9.2 / §9.3).

## Auditoría interna

| DocType | Rol |
|---|---|
| **Programa Auditoria** | El plan anual/periódico de auditorías internas. |
| **Auditoria** | Una auditoría concreta dentro del Programa (alcance, fechas, proceso auditado). |
| **Equipo Auditoria** | El equipo asignado a una Auditoría (auditor líder + auditores). |
| **Criterio Auditoria** | Los criterios normativos/documentales contra los que se audita. |
| **Hallazgo Auditoria** | Un hallazgo detectado durante la Auditoría — puede escalar al mismo flujo CAPA que un Hallazgo de autoevaluación (ver [módulo Núcleo](/sgc/modulos/nucleo/)). |
| **Informe Auditoria** | El informe consolidado de una Auditoría. |

## Revisión por la dirección

| DocType | Rol |
|---|---|
| **Revision Direccion** | Una sesión de revisión del SGC por la alta dirección. |
| **Entrada Revision** | Tabla hija: las entradas de la revisión (resultados de auditorías, no conformidades, estado de acciones, cambios de contexto). |
| **Salida Revision** | Tabla hija: las decisiones/salidas de la revisión (mejoras, recursos necesarios, cambios de política). |

El rol **Auditor Interno** (ver [RBAC](/sgc/desarrollo/rbac/)) crea y gestiona
Hallazgos de auditoría, pero no valora autoevaluaciones ni cierra Planes de Mejora —
esa separación de funciones es deliberada.
