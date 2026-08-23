"""F16 workflow — Workflow nativo del Hallazgo de auditoría (M06).

Detectado recorriendo el flujo en producción el 20-ago-2026: `Hallazgo
Auditoria` era el único documento de la cadena de auditoría con su ciclo de vida
en un Select suelto, y eso permitía dos cosas que el resto de la cadena impide:

1. **El mismo auditor que abre el hallazgo lo cerraba**, sin que nadie
   verificase. Su gemelo de autoevaluación (`Hallazgo`, f12) y `No Conformidad`
   exigen otra persona desde Fase 2; este se quedó atrás — la misma asimetría
   injustificada que motivó crear f12.
2. **Se podía marcar «Escalado a NC» con el campo `no_conformidad` vacío**, o
   sea declarar en falso el enlace M05↔M06 que pide RF-B05 del Requerimiento.
   Eso lo cierra el guard del controlador, no este workflow.

Reparto de responsabilidades, el mismo que ya rige el resto de M06 (f8): el
**Auditor Interno** detecta y escala lo que encuentra —es avance operativo de su
propio trabajo, `self_approval=1`—; la **DPGC** cierra, y no puede cerrar lo que
ella misma levantó (`self_approval=0`, por defecto).

El escalamiento se ejecuta por `HallazgoAuditoria.escalar_a_no_conformidad()`,
que crea la No Conformidad real y mueve el estado por el motor. Existe como
transición aquí para que ese movimiento sea una transición de verdad y quede en
el historial, no una escritura suelta.

Ejecutar (idempotente):
    bench --site <site> execute sgc.setup.f16_workflow_hallazgo_auditoria.run
"""
import frappe

from sgc.setup.f2_workflow import _ensure_role, _upsert_workflow

ROLES = ["Auditor Interno", "DPGC"]

WF_HALLAZGO_AUDITORIA = {
    "name": "Hallazgo Auditoria SGC",
    "document_type": "Hallazgo Auditoria",
    "workflow_state_field": "estado",
    "is_active": 1,
    "send_email_alert": 0,
    "states": [
        ("Abierto", "0", "Auditor Interno"),
        ("Escalado a NC", "0", "DPGC"),
        ("Cerrado", "0", "DPGC"),
    ],
    "transitions": [
        # escalar es avance operativo de quien detectó el hallazgo -> self_approval=1.
        # Lo dispara `escalar_a_no_conformidad()`, que además crea la NC.
        ("Abierto", "Escalar a NC", "Escalado a NC", "Auditor Interno", 1),
        # cerrar es el control: no lo hace quien levantó el hallazgo -> self_approval=0
        # (por defecto). Un hallazgo cerrado por su propio autor no es una auditoría.
        ("Abierto", "Cerrar", "Cerrado", "DPGC"),
        ("Escalado a NC", "Cerrar", "Cerrado", "DPGC"),
        # y puede devolverse si el cierre fue prematuro (la NC sigue abierta, el
        # área no implementó): mismo criterio que "Reabrir" en f8/f12.
        #
        # Son DOS acciones porque un hallazgo cerrado vuelve a donde estaba, y eso
        # depende de si llegó a escalar. Con una sola, el caso que el comentario
        # de arriba describe —"la NC sigue abierta"— era justamente el que NO
        # funcionaba: el controlador fuerza "Escalado a NC" mientras haya NC
        # ligada, así que reabrir a "Abierto" chocaba con el propio workflow.
        # Devolver un hallazgo escalado a "Abierto" además mentiría: diría que no
        # escaló, con la No Conformidad ahí delante.
        ("Cerrado", "Reabrir", "Abierto", "DPGC", 1),
        ("Cerrado", "Reabrir escalado", "Escalado a NC", "DPGC", 1),
    ],
}


def run():
    frappe.flags.in_patch = True

    for r in ROLES:
        _ensure_role(r)

    n_ha = _upsert_workflow(WF_HALLAZGO_AUDITORIA)

    frappe.db.commit()

    print("Workflow OK:", n_ha,
          "[Abierto -> Escalado a NC | Cerrado (cierra la DPGC, no quien lo abrió)]")
