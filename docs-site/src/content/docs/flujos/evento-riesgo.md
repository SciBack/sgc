---
title: Evento de riesgo
description: Prueba funcional completa del reporte de eventos de riesgo por cualquier colaborador.
---

## Qué es

Un **evento de riesgo** es algo que ya ocurrió: una caída de un servicio, una pérdida de datos, un plazo incumplido. Lo reporta **cualquier colaborador**, que suele ser quien lo ve primero; Calidad lo evalúa y, si lo confirma, se abre la **no conformidad** donde se hace el análisis de causas y se define el plan de acción para corregirlo.

No sustituye a **Materializar** un riesgo: el evento es una ocurrencia concreta. Si el riesgo entero se materializó, lo decide la DPGC en el flujo del [riesgo](../riesgo/).

## Quién puede ejecutarlo

- **Reportar**: cualquier usuario del sistema (rol automático **Desk User**; quien no tenga otro rol del SGC recibe el rol [Colaborador](../../roles/colaborador/)). Cada uno ve **solo lo que reportó**.
- **Evaluar, confirmar y descartar**: la **DPGC**.
- **Leer todos los reportes**: DPGC, Analista de Calidad, Dueño de Proceso, Auditor Interno y Rectorado. Un evento puede describir a personas, así que el resto de roles no los ve (Ley 29733).

## Precondiciones

Una cuenta con solo el rol Colaborador y dos cuentas DPGC distintas: quien reporta no puede decidir sobre su propio reporte. Usa identificadores ficticios.

## Pasos y resultados esperados

1. Como **Colaborador**, entra por el acceso rápido **Reportar evento de riesgo** y crea el evento con qué pasó, la fecha, el proceso, la descripción y, si los hay, las consecuencias, las acciones inmediatas y la evidencia. El proceso y la unidad orgánica se eligen de la lista, aunque el colaborador no pueda abrir sus fichas. Resultado esperado: queda en **Reportado**, con código `EVR-AAAA-NNNNN`, y el sistema sella **Reportado por** y la fecha del reporte. La DPGC recibe el aviso.
2. Como **DPGC**, ejecuta **Evaluar**. Resultado esperado: queda en **En evaluacion** y aparece la sección **Evaluación de Calidad**, donde se asigna el **riesgo del registro** al que corresponde el evento.
3. Elige el **tipo de no conformidad** (mayor por defecto) y ejecuta **Confirmar**. Resultado esperado: queda en **Confirmado**; el sistema sella **Decidido por** y la fecha, y enlaza la **no conformidad** creada con origen «Evento de riesgo». Quien reportó recibe el aviso.
4. Abre la no conformidad: trae el relato completo (descripción, consecuencias y acciones inmediatas), el proceso, la fecha del evento y exige análisis de causas. Ahí se registran las causas y las acciones de mejora.

Alternativa: en el paso 3, escribe el **motivo del descarte** y ejecuta **Descartar**. Resultado esperado: queda en **Descartado**, sin no conformidad, y quien reportó recibe el aviso con el motivo.

## Estados por los que pasa

**Reportado** → **En evaluacion** → **Confirmado** (abre la no conformidad) o **Descartado**.

| Desde | Acción | Hacia | Rol |
|---|---|---|---|
| Reportado | Evaluar | En evaluacion | DPGC |
| En evaluacion | Confirmar | Confirmado | DPGC |
| En evaluacion | Descartar | Descartado | DPGC |

## Permisos

El colaborador crea y ve solo lo suyo (**Desk User** con «solo si es el creador»). **Confirmar** y **Descartar** no admiten autoaprobación: pruébalos con una cuenta distinta de la que reportó.

## Restricciones

- **Quien reportó no decide sobre su reporte**, aunque tenga el rol DPGC. Lo impide el servidor, no solo el workflow.
- **La fecha del evento no puede ser futura.**
- **Reportado por**, **Decidido por** y sus fechas los sella el sistema; lo que llegue escrito a mano no prevalece.
- **Lo decidido no se reescribe**: tras confirmar o descartar, el relato queda como se evaluó.
- El riesgo del registro lo asigna Calidad: el colaborador no ve el registro de riesgos. Si el proceso quedó vacío, se toman el proceso y la unidad del riesgo.

## Casos negativos

- Reportar con una fecha futura: debe rechazarse.
- Evaluar, confirmar o descartar como Colaborador: debe rechazarse.
- Abrir el evento de otra persona como Colaborador: debe rechazarse.
- Confirmar o descartar con la cuenta que reportó: debe rechazarse.
- Descartar sin motivo: debe rechazarse.
- Modificar la descripción de un evento confirmado: debe rechazarse.

## Evidencia que debe capturarse

Captura del estado anterior, control ejecutado, estado final e historial; URL e identificador ficticio; rol utilizado; mensaje y respuesta HTTP de cada caso negativo. Oculta cookies y datos personales.

## Relación con otros módulos

- **No conformidad**: la confirmación la abre con origen «Evento de riesgo» y enlace en los dos sentidos; el análisis de causas y el plan de acción se hacen allí.
- **Riesgo**: el formulario del riesgo muestra en **Conexiones** los eventos reportados sobre él.
- **Mapa de procesos**: cada evento pertenece a un proceso.

## Acciones operativas o configuración adicional

Los avisos (a la DPGC al reportarse y a quien reportó al decidirse) salen según `Configuracion Correo` (modo de ensayo y lista blanca). Requieren scheduler y servidor de correo configurados.

## Fuente en código

`sgc/sgc_riesgos/doctype/evento_riesgo/` (controlador y formulario), `sgc/setup/f25_workflow_evento_riesgo.py` (workflow), `COLABORADORES` en `sgc/setup/f3b_rbac.py` (permiso del colaborador) y las reglas «SGC - Evento de riesgo …» en `sgc/setup/f15_notificaciones_workflow.py`.
