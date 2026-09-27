---
title: Informe de auditoría
description: Prueba funcional de la revisión, aprobación y distribución del informe de auditoría (ISO 19011 §6.5).
---

## Quién puede ejecutarlo

El **Auditor Interno** redacta el informe y lo envía a revisión. La **DPGC** lo revisa, lo aprueba o lo devuelve, y lo distribuye.

## Precondiciones

Una auditoría con su equipo auditor y sus hallazgos. Usa cuentas separadas: quien emite y quien aprueba deben ser personas distintas, y quien aprueba no puede estar en el equipo auditor.

## Pasos y resultados esperados

1. Crea el informe de la auditoría y redacta el resumen ejecutivo o las conclusiones. Resultado esperado: queda en **Borrador**, con código `IAU-AAAA-NNNN` y los contadores de hallazgos calculados solos.
2. Como **Auditor Interno**, ejecuta **Enviar a revision**. Resultado esperado: queda en **En revision** y el sistema sella **Emitido por** y la fecha.
3. Como **DPGC** ajena al equipo auditor, ejecuta **Aprobar**. Resultado esperado: queda en **Aprobado** y el sistema sella **Aprobado por** y la fecha. A partir de aquí el contenido y los contadores ya no cambian.
4. Indica los **Destinatarios** y ejecuta **Distribuir**. Resultado esperado: queda en **Distribuido**, con **Distribuido por** y la fecha.

## Estados por los que pasa

**Borrador** → **En revision** → **Aprobado** → **Distribuido**, con la devolución **En revision** → **Borrador**.

| Desde | Acción | Hacia | Rol |
|---|---|---|---|
| Borrador | Enviar a revision | En revision | Auditor Interno |
| En revision | Aprobar | Aprobado | DPGC |
| En revision | Devolver a borrador | Borrador | DPGC |
| Aprobado | Distribuir | Distribuido | DPGC |

## Permisos

El actor necesita DocPerm sobre el DocType y el rol exacto de la transición. **Aprobar** no admite autoaprobación.

## Restricciones

- **No aprueba** quien emitió el informe, quien lo creó ni nadie del equipo auditor de esa auditoría.
- **Lo aprobado es lo que se distribuye:** resumen, conclusiones, adjunto y contadores quedan congelados.
- **Un hallazgo de auditoría no se cierra hasta que el informe de su auditoría está aprobado**, y la auditoría tampoco se cierra sin él. Escalar un hallazgo a no conformidad sí se puede antes.

## Casos negativos

- Enviar a revisión un informe sin resumen ni conclusiones: debe rechazarse.
- Devolver a borrador sin observaciones: debe rechazarse.
- Aprobar con la cuenta que lo emitió, que lo creó o que está en el equipo auditor: debe rechazarse.
- Modificar las conclusiones de un informe aprobado: debe rechazarse.
- Distribuir sin destinatarios: debe rechazarse.
- Cerrar un hallazgo, o la auditoría, con el informe sin aprobar: debe rechazarse.

## Evidencia que debe capturarse

Captura del estado anterior, acción ejecutada, estado final e historial; URL e identificador ficticio; rol utilizado; mensaje de cada caso negativo. Oculta cookies y datos personales.

## Relación con otros módulos

Auditoría (el informe consolida sus hallazgos y su cierre lo exige aprobado), hallazgos de auditoría (se levantan tras la aprobación) y revisión por la dirección (**Presentado en**).

## Fuente en código

`sgc/sgc_auditoria/doctype/informe_auditoria/` (controlador) y `sgc/setup/f24_workflow_informe_auditoria.py` (workflow).
