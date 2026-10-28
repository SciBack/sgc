"""Chequeos de lo que trae el SGC: permisos y flujos de aprobación (#50).

Desde la 1.2.0 los permisos son los estándar de cada DocType y los workflows son fixtures:
Frappe los aplica en cada `migrate`. Aun así se mira el RESULTADO en el sitio, no si el
migrate corrió: hubo un periodo en el que los sitios quedaban sin RBAC ni workflows y nadie se
daba cuenta, porque el sitio respondía y solo el System Manager podía hacer algo.

Sin permisos de ningún rol del SGC la instancia no le sirve a nadie: BLOQUEANTE. Si solo faltan
en algunos DocTypes, alguien concreto no puede trabajar: AVISO. Igual con los workflows.
"""

import frappe

from sgc import estandar
from sgc.verificacion import AVISO, BLOQUEANTE, INFO, Hallazgo

REMEDIO_MIGRATE = "Volver a migrar (`bench --site <sitio> migrate`): Frappe los aplica desde la app."


def permisos_aplicados():
    """Cada DocType del SGC da en este sitio permisos a los roles del SGC que trae de serie.

    Lo efectivo es lo que Frappe aplica: los Custom DocPerm si los hay, si no los estándar. Una
    institución puede haber cambiado permisos (Role Permission Manager); lo que se señala es que
    un rol que el SGC trae para un DocType se haya quedado sin ninguno.
    """
    del_sgc = set(estandar.roles())
    esperados = {
        dt: {p["role"] for p in filas if p.get("role") in del_sgc}
        for dt, filas in estandar.permisos().items()
        if frappe.db.exists("DocType", dt)
    }
    faltan = {dt: sorted(roles - estandar.roles_efectivos(dt)) for dt, roles in esperados.items()}
    faltan = {dt: r for dt, r in faltan.items() if r}
    if not faltan:
        return []
    if len(faltan) == len(esperados) and all(set(r) == esperados[dt] for dt, r in faltan.items()):
        return [
            Hallazgo(
                BLOQUEANTE,
                "rbac-no-aplicado",
                "Los permisos del SGC no están aplicados: ningún rol del SGC tiene permisos.",
                detalle=[f"{len(esperados)} DocType(s) sin permisos de sus roles"],
                remedio=REMEDIO_MIGRATE,
            )
        ]
    return [
        Hallazgo(
            AVISO,
            "rbac-incompleto",
            f"{len(faltan)} DocType(s) del SGC no dan permisos a roles que el SGC trae para ellos.",
            detalle=[f"{dt}: {', '.join(r)}" for dt, r in sorted(faltan.items())],
            remedio=REMEDIO_MIGRATE + " Si los quitó alguien en el Role Permission Manager, fue a propósito o no.",
        )
    ]


def workflows_aplicados():
    declarados = [w for w in estandar.workflows().values() if frappe.db.exists("DocType", w["document_type"])]
    faltan, inactivos = [], []
    for wf in declarados:
        activo = frappe.db.get_value("Workflow", wf["name"], "is_active")
        if activo is None:
            faltan.append(f"{wf['name']} ({wf['document_type']}) — no existe")
        elif wf.get("is_active", 1) and not int(activo):
            inactivos.append(f"{wf['name']} ({wf['document_type']}) — desactivado")
    problemas = faltan + inactivos
    if not problemas:
        return []
    if declarados and len(faltan) == len(declarados):
        return [
            Hallazgo(
                BLOQUEANTE,
                "workflows-no-aplicados",
                "No hay ningún flujo de aprobación del SGC: nada se puede revisar, aprobar ni publicar.",
                detalle=[f"{len(declarados)} workflow(s) declarados, ninguno creado"],
                remedio=REMEDIO_MIGRATE,
            )
        ]
    return [
        Hallazgo(
            AVISO,
            "workflows-incompletos",
            f"{len(problemas)} flujo(s) de aprobación del SGC faltan o están desactivados.",
            detalle=sorted(problemas),
            remedio=REMEDIO_MIGRATE + " Un workflow desactivado a mano deja el documento sin circuito de aprobación.",
        )
    ]


def guias_de_arranque_visibles():
    """Las guías de arranque de cada área (1.7.8) solo se ven con `enable_onboarding`.

    Frappe lo pone a 1 en el asistente de instalación (`setup_wizard.py`); un sitio creado sin
    asistente lo tiene a 0 y la guía no sale en ninguna portada (`desktop.py`, `get_onboarding_doc`).
    """
    if frappe.db.get_single_value("System Settings", "enable_onboarding"):
        return []
    return [
        Hallazgo(
            INFO,
            "guias-de-arranque-ocultas",
            "Las guías de arranque de las áreas no se muestran.",
            remedio="Activar «Habilitar incorporación» en System Settings (`enable_onboarding`).",
        )
    ]


CHEQUEOS = [permisos_aplicados, workflows_aplicados, guias_de_arranque_visibles]
