---
title: Conceptos y reglas de negocio
description: Vocabulario, permisos, estados y restricciones que gobiernan SGC.
---

## Conceptos esenciales

- **DocType:** entidad persistente de Frappe, por ejemplo Autoevaluacion o Evidencia.
- **DocPerm:** capacidad create/read/write/submit/cancel por rol y nivel de campo.
- **Workflow:** estados y acciones permitidas para un DocType.
- **User Permission:** filtro de ámbito, especialmente por Programa Sede.
- **Nivel propuesto:** resultado del cálculo NL/L/LP; todavía no oficial.
- **Nivel confirmado:** decisión humana registrada con actor y justificación cuando hay override.
- **Evidencia:** soporte con origen, vigencia y trazabilidad.
- **CAPA:** cadena de corrección y acción correctiva/preventiva desde hallazgo o NC.

## Reglas verificables

1. Un rol necesita simultáneamente permiso del DocType y transición de workflow.
2. Ocultar un control en la SPA no autoriza ni deniega por sí solo; el backend decide.
3. No se debe editar el estado directamente para saltar el workflow.
4. Los cierres y verificaciones deben quedar en historial con el actor real.
5. Un cálculo automático no debe sobrescribir silenciosamente una confirmación humana.
6. Una reapertura regresa a un estado operativo explícito y debe conservar trazabilidad.
7. Los roles de lectura no deben obtener escritura por combinar menús o URLs directas.

## Códigos de permiso

La matriz usa `c` crear, `r` leer, `w` escribir, `s` enviar/submit y `x` cancelar. Los child tables
heredan permisos del documento padre; asignar DocPerm independiente a una tabla hija no tiene
efecto funcional.
