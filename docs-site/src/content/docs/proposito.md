---
title: Propósito y mapa del sistema
description: Qué resuelve SGC y cómo se conectan sus módulos.
---

SGC es una aplicación Frappe con una SPA Vue para gestionar calidad universitaria: estructura,
marcos normativos, autoevaluación, evidencia, procesos, documentos, indicadores, auditoría,
riesgos, cumplimiento y mejora continua.

## Mapa funcional

1. **Estructura y marco** aportan programas, sedes, estándares, criterios y escalas.
2. **Autoevaluación** registra valoraciones; el motor propone niveles y una persona los confirma.
3. **Evidencias y trazabilidad** sustentan criterios, procesos y controles.
4. **Hallazgos, no conformidades y CAPA** convierten brechas en planes y acciones verificables.
5. **Procesos, documentos, indicadores y riesgos** operan el sistema de gestión.
6. **Auditoría, revisión por la dirección y cumplimiento** producen control y rendición de cuentas.

## Principio central

El motor propone; una persona autorizada confirma. `nivel_propuesto` no es el nivel oficial
`nivel`. Las transiciones de control usan roles específicos y, en varios casos, impiden que la
misma cuenta creadora se apruebe.

## Límites reales

- La visibilidad por Programa Sede se activa mediante User Permissions; sin ellas el mecanismo es
  opt-in y no debe suponerse aislamiento.
- Lector Externo no tiene acceso al Desk y su experiencia de portal está marcada como parcial.
- Correo, archivos, PDF, SSO y tareas periódicas requieren servicios operativos adicionales.
- La configuración institucional no forma parte de la capa canónica del producto.
