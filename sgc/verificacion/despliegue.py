"""Chequeos de lo que aplica el despliegue: permisos y flujos de aprobación (#50).

El orquestador (`f_deploy_run_all`) los aplica en cada `migrate`, y aun así hubo
un periodo en el que los sitios quedaban sin RBAC ni workflows y nadie se daba
cuenta: el migrate terminaba, el sitio respondía, y nadie salvo el System Manager
podía hacer nada. Aquí se mira el RESULTADO, no si el paso corrió.

Sin permisos de ningún rol del SGC la instancia no le sirve a nadie: BLOQUEANTE.
Si solo faltan en algunos DocTypes, alguien concreto no puede trabajar: AVISO.
Igual con los workflows.
"""

import importlib
import pathlib

import frappe

from sgc.setup.f3b_rbac import MATRIZ
from sgc.verificacion import AVISO, BLOQUEANTE, Hallazgo

REMEDIO_MIGRATE = "Volver a migrar (`bench --site <sitio> migrate`): el despliegue los aplica."


def permisos_aplicados():
    """Cada DocType de la matriz tiene al menos un Custom DocPerm de los roles que la matriz le da."""
    existentes = [dt for dt in MATRIZ if frappe.db.exists("DocType", dt)]
    sin_permisos = [
        dt for dt in existentes
        if not frappe.db.count("Custom DocPerm", {"parent": dt, "role": ["in", list(MATRIZ[dt])]})
    ]
    if not sin_permisos:
        return []
    if len(sin_permisos) == len(existentes):
        return [
            Hallazgo(
                BLOQUEANTE,
                "rbac-no-aplicado",
                "La matriz de permisos del SGC no está aplicada: ningún rol del SGC tiene permisos.",
                detalle=[f"{len(existentes)} DocType(s) de la matriz sin permisos de sus roles"],
                remedio=REMEDIO_MIGRATE + " Por separado: `bench --site <sitio> execute sgc.setup.f3b_rbac.run`.",
            )
        ]
    return [
        Hallazgo(
            AVISO,
            "rbac-incompleto",
            f"{len(sin_permisos)} DocType(s) de la matriz no tienen los permisos de sus roles.",
            detalle=sorted(sin_permisos),
            remedio=REMEDIO_MIGRATE + " Por separado: `bench --site <sitio> execute sgc.setup.f3b_rbac.run`.",
        )
    ]


def _workflows_declarados():
    """Los workflows que declaran los pasos `f*_workflow*` del despliegue.

    Se leen de los propios módulos (las especificaciones que pasan a
    `_upsert_workflow`), no de una lista aparte: una lista aparte se queda vieja
    el día que alguien añade un workflow y no se acuerda de ella.
    """
    carpeta = pathlib.Path(importlib.import_module("sgc.setup").__file__).parent
    specs = []
    for ruta in sorted(carpeta.glob("f*_workflow*.py")):
        modulo = importlib.import_module(f"sgc.setup.{ruta.stem}")
        for valor in vars(modulo).values():
            if isinstance(valor, dict) and {"name", "document_type", "states", "transitions"} <= valor.keys():
                specs.append(valor)
    return specs


def workflows_aplicados():
    declarados = [s for s in _workflows_declarados() if frappe.db.exists("DocType", s["document_type"])]
    faltan, inactivos = [], []
    for spec in declarados:
        activo = frappe.db.get_value("Workflow", spec["name"], "is_active")
        if activo is None:
            faltan.append(f"{spec['name']} ({spec['document_type']}) — no existe")
        elif spec.get("is_active", 1) and not int(activo):
            inactivos.append(f"{spec['name']} ({spec['document_type']}) — desactivado")
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


CHEQUEOS = [permisos_aplicados, workflows_aplicados]
