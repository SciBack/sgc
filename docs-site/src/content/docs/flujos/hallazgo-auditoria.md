---
title: Hallazgo de auditoría
description: Prueba funcional completa del flujo Hallazgo de auditoría.
---

## Quién puede ejecutarlo

Auditor Interno detecta y escala; DPGC cierra y reabre.

## Precondiciones

Auditoría registrada y hallazgo creado desde ella, con tipo (no conformidad mayor o menor, observación, oportunidad de mejora, conformidad o fortaleza) y descripción. Usa identificadores ficticios y cuentas separadas: quien abre el hallazgo no puede cerrarlo.

## Pasos y resultados esperados

1. En estado **Abierto**, inicia sesión como **Auditor Interno** y usa **Escalar a no conformidad**. Resultado esperado: se crea la No Conformidad enlazada, el hallazgo queda en **Escalado a NC** y la acción aparece en su historial.
2. Con el informe de la auditoría todavía sin aprobar, inicia sesión como **DPGC** y ejecuta **Cerrar**. Resultado esperado: el cierre se rechaza con el mensaje «Informe sin aprobar».
3. Aprueba el informe de la auditoría (flujo [Informe de auditoría](../informe-auditoria/)) y repite **Cerrar** como **DPGC**. Resultado esperado: el registro queda en **Cerrado**.
4. En estado **Cerrado**, ejecuta **Reabrir escalado** como **DPGC**. Resultado esperado: vuelve a **Escalado a NC**, porque la No Conformidad sigue enlazada.
5. Con un hallazgo de tipo observación sin escalar, ejecuta **Cerrar** y después **Reabrir** como **DPGC**. Resultado esperado: **Cerrado** y de vuelta a **Abierto**.

## Estados por los que pasa

**Abierto** → **Escalado a NC** → **Cerrado**. Un hallazgo que no escala puede cerrarse desde **Abierto**; las reaperturas devuelven al estado del que vino.

| Desde | Acción | Hacia | Rol |
|---|---|---|---|
| Abierto | Escalar a NC | Escalado a NC | Auditor Interno |
| Abierto | Cerrar | Cerrado | DPGC |
| Escalado a NC | Cerrar | Cerrado | DPGC |
| Cerrado | Reabrir | Abierto | DPGC |
| Cerrado | Reabrir escalado | Escalado a NC | DPGC |

## Permisos

El actor necesita DocPerm sobre el DocType y el rol exacto de la transición. **Cerrar** no admite autoaprobación: pruébalo con una cuenta distinta de quien creó el hallazgo.

## Restricciones

No modifiques el campo de estado directamente: **Escalado a NC** sin No Conformidad enlazada se rechaza. Un hallazgo de tipo no conformidad (mayor o menor) no se cierra sin haber escalado. Ningún hallazgo se cierra antes de aprobar el informe de su auditoría.

## Casos negativos

- Cerrar con la misma cuenta que abrió el hallazgo: debe ser rechazado.
- Cerrar antes de aprobar el informe de la auditoría: debe ser rechazado.
- Cerrar una no conformidad mayor o menor sin escalar: debe ser rechazado.
- Fijar **Escalado a NC** sin No Conformidad: debe ser rechazado.

## Evidencia que debe capturarse

Captura del estado anterior, control ejecutado, estado final e historial; identificador ficticio de la No Conformidad creada; rol utilizado; mensaje de cada caso negativo. Oculta cookies y datos personales.

## Relación con otros módulos

Auditoría, informe de auditoría, no conformidad y CAPA.

## Acciones operativas o configuración adicional

Los avisos de cambio de estado requieren scheduler y servidor de correo configurados.

## Fuente en código

`sgc/setup/f16_workflow_hallazgo_auditoria.py` y el controlador `HallazgoAuditoria`. No se documentan estados adicionales a los definidos por el workflow actual.
