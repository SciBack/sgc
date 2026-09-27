"""F23 workflow — Workflow nativo de Salida No Conforme (ISO 9001 §8.7, #33).

Quien detecta registra; el dueño del proceso (o la DPGC) trata y decide; la DPGC
verifica y cierra. Las separaciones de funciones que importan —la concesión no
la autoriza quien detectó, y el resultado no lo verifica quien lo trató— las
impone el CONTROLADOR (`SalidaNoConforme._validar_independencia`), porque
`allow_self_approval=0` solo compara con `doc.owner` (ver f14).

Ejecutar (idempotente):
    bench --site <site> execute sgc.setup.f23_workflow_salida_no_conforme.run
"""
import frappe

from sgc.setup.f2_workflow import _ensure_role, _upsert_workflow

DPGC = "DPGC"
ANALISTA = "Analista de Calidad (DPGC)"
DUENO = "Dueño de Proceso"
AUDITOR = "Auditor Interno"
CALIDAD_PROGRAMA = "Responsable de Calidad de Programa"

ROLES = [DPGC, ANALISTA, DUENO, AUDITOR, CALIDAD_PROGRAMA]

WF_SALIDA_NO_CONFORME = {
    "name": "Salida No Conforme SGC",
    "document_type": "Salida No Conforme",
    "workflow_state_field": "estado",
    "is_active": 1,
    "send_email_alert": 0,  # el correo va por f15 (Value Change), ver f14/f15
    "states": [
        # Detectar una salida no conforme es de cualquiera que la vea: el
        # registro queda editable para todos los roles que pueden crearla.
        ("Detectada", "0", DUENO),
        ("Detectada", "0", DPGC),
        ("Detectada", "0", ANALISTA),
        ("Detectada", "0", AUDITOR),
        ("Detectada", "0", CALIDAD_PROGRAMA),
        ("En tratamiento", "0", DUENO),
        ("En tratamiento", "0", DPGC),
        ("Tratada", "0", DPGC),
        ("Verificada", "0", DPGC),
        ("Cerrada", "0", DPGC),
    ],
    "transitions": [
        # avance operativo del tratamiento -> self_approval=1. La concesión se
        # controla en el controlador, no aquí.
        ("Detectada", "Iniciar tratamiento", "En tratamiento", DUENO, 1),
        ("Detectada", "Iniciar tratamiento", "En tratamiento", DPGC, 1),
        ("En tratamiento", "Registrar tratamiento", "Tratada", DUENO, 1),
        ("En tratamiento", "Registrar tratamiento", "Tratada", DPGC, 1),
        # verificar es el control -> self_approval=0 (default).
        ("Tratada", "Verificar", "Verificada", DPGC),
        # la devolución afloja un control, no lo supera -> self_approval=1,
        # como el resto de devoluciones del producto (f2_workflow).
        ("Tratada", "Devolver a tratamiento", "En tratamiento", DPGC, 1),
        # cerrar tras verificar es administrativo: el control ya ocurrió.
        ("Verificada", "Cerrar", "Cerrada", DPGC, 1),
    ],
}


def run():
    frappe.flags.in_patch = True

    for r in ROLES:
        _ensure_role(r)

    n = _upsert_workflow(WF_SALIDA_NO_CONFORME)

    frappe.db.commit()

    print("Workflow OK:", n,
          "[Detectada -> En tratamiento -> Tratada -> Verificada -> Cerrada | "
          "Tratada -> En tratamiento (devolver)]")
