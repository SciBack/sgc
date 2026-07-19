"""F10 workflow — Workflow nativo de la Revisión por la Dirección (rama 4, §9.3).

Mismo patrón que f8_workflow_auditoria.py (reutiliza los helpers de f2_workflow.py).
Los estados son los valores REALES del Select `estado` de Revision Direccion
(verificados en el .json): Planificada / Realizada / Cerrada.

DPGC PREPARA y REALIZA la revisión (recopila entradas §9.3.2, la ejecuta); el
CIERRE ("Cerrar revision") lo ejecuta "Rectorado/VR (lectura)" -- ver hallazgo
normativo 2026-07-19 (escalamiento del plan de acción, investigación de ISO
9001:2015 §9.3.1/§5.1.1): la norma no exige literalmente un segundo aprobador,
pero SÍ asigna la revisión del SGC a la "alta dirección" de forma NO delegable
(ISO 9001:2015 eliminó a propósito el "representante de la dirección" delegable
que sí existía en la versión 2008 -- ver §5.1.1). La propia matriz RBAC del SGC
(f3b_rbac.py) ya distingue "Rectorado/VR (lectura)" como esa alta dirección,
separada de DPGC ("gobierno operativo") -- promoverla de solo-lectura a
co-aprobador activo de ESTE workflow (y únicamente este) resuelve el riesgo
residual antes aceptado ("DPGC se autoaprueba de principio a fin") sin
necesitar saber todavía qué persona real ocupa el rol -- eso es un paso
posterior (crear el User real y asignarle el rol), independiente de esta
estructura.

Las validaciones por etapa (entradas §9.3.2 al realizarla, salidas §9.3.3 +
acta al cerrarla) las aplica el controlador (revision_direccion.py); el
workflow solo gobierna las transiciones.

Ejecutar (idempotente):
    bench --site <site> execute sgc.setup.f10_workflow_revision.run
"""
import frappe

from sgc.setup.f2_workflow import _ensure_role, _upsert_workflow

ROLES = ["DPGC", "Rectorado/VR (lectura)"]

# --- Workflow: Revision Direccion (estados = Select real de Revision Direccion.estado) ---
WF_REVISION = {
    "name": "Revision Direccion SGC",
    "document_type": "Revision Direccion",
    "workflow_state_field": "estado",
    "is_active": 1,
    "send_email_alert": 0,  # revertido 2026-07-19: dispara attach_print (PDF) por email en CUALQUIER save con transicion pendiente, no solo en transiciones reales -- rompio 70 tests y arriesga flood de correos en prod. Necesita diseno propio (Fase 2, item aparte), no un toggle de 1 linea.
    # state, doc_status, allow_edit (rol que puede editar el doc en ese estado)
    "states": [
        ("Planificada", "0", "DPGC"),
        ("Realizada", "0", "DPGC"),
        ("Cerrada", "0", "DPGC"),
    ],
    # state (desde), action (boton), next_state (hacia), allowed (rol)
    "transitions": [
        # avance operativo de la propia preparación/ejecución -> self_approval=1
        ("Planificada", "Realizar revision", "Realizada", "DPGC", 1),
        ("Realizada", "Devolver a planificada", "Planificada", "DPGC", 1),
        # el CIERRE es el acto formal de la alta dirección (ver docstring del
        # módulo) -- ya no lo ejecuta DPGC sobre su propio trabajo. Ejecutado
        # por "Rectorado/VR (lectura)", que no es quien creó/preparó el
        # documento -> self_approval=0 (default) es correcto y suficiente,
        # no hace falta marcarlo explícito.
        ("Realizada", "Cerrar revision", "Cerrada", "Rectorado/VR (lectura)"),
        # reabrir (para corregir) sigue siendo trabajo operativo de DPGC.
        ("Cerrada", "Reabrir revision", "Realizada", "DPGC", 1),
    ],
}


def run():
    frappe.flags.in_patch = True

    for r in ROLES:
        _ensure_role(r)

    n_rev = _upsert_workflow(WF_REVISION)

    frappe.db.commit()

    print("Workflow OK:", n_rev,
          "[Planificada -> Realizada -> Cerrada]  "
          "(DPGC prepara/realiza, Rectorado/VR cierra)")
