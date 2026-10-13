---
title: Dirección y partes interesadas (sgc_gobierno)
description: Los órganos de gobierno de la calidad y sus instrumentos de gestión.
sidebar:
  order: 8
---

Los órganos de gobierno de la calidad y sus instrumentos de gestión: comités,
políticas, objetivos y la escucha de grupos de interés.

| DocType | Rol |
|---|---|
| **Comite** | Un comité de calidad (institucional, de facultad o de programa). |
| **Miembro Comite** | Tabla hija/registro de pertenencia de una persona a un Comité, con rol dentro de él. |
| **Reunion** | Una sesión de un Comité. |
| **Reunion Asistente** | Tabla hija: asistentes a una Reunión. |
| **Acuerdo** | Un acuerdo tomado en una Reunión, con seguimiento de cumplimiento. |
| **Politica Calidad** | La política de calidad institucional vigente. |
| **Objetivo Calidad** | Un objetivo de calidad derivado de la política, medible vía indicadores. |
| **Grupo Interes** | Un grupo de interés (stakeholder) de la institución (estudiantes, egresados, empleadores...). |
| **Instrumento** | Un instrumento de recolección (encuesta, entrevista) aplicado a un Grupo de Interés. |
| **Aplicacion Instrumento** | Una aplicación concreta de un Instrumento (fecha, alcance). |
| **Resultado Instrumento** | Los resultados/datos recogidos en una Aplicacion Instrumento. |

## Revisión por la dirección

| DocType | Rol |
|---|---|
| **Revision Direccion** | Una sesión de revisión del SGC por la alta dirección. |
| **Entrada Revision** | Tabla hija: las entradas de la revisión (resultados de auditorías, no conformidades, estado de acciones, cambios de contexto). |
| **Salida Revision** | Tabla hija: las decisiones/salidas de la revisión (mejoras, recursos necesarios, cambios de política). |

El rol **Auditor Interno** (ver [RBAC](../../desarrollo/rbac/)) crea y gestiona
Hallazgos de auditoría, pero no valora autoevaluaciones ni cierra Planes de Mejora —
esa separación de funciones es deliberada.
