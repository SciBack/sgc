"""F2 runner — fields -> loader CONEAU -> workflows, en orden, con in_patch.
Ejecutar: echo 'from sgc.setup import f2_run_all; f2_run_all.run()' | bench --site sgc.localhost console
"""
import os

import frappe
from sgc.setup import f2_fields, f2_load_coneau, f2_workflow

# Fase 1 (2026-07-19, hallazgo en despliegue): antes era una ruta absoluta fija
# del bench de laboratorio ("/workspace/development/frappe-bench/..."), que no
# existe en producción ("/home/frappe/frappe-bench/..."). f2_load_coneau fallaba
# en producción SIEMPRE que se corría vía f_deploy_run_all/after_migrate, y como
# los 3 pasos compartían un solo try/finally, ese fallo impedía que f2_workflow.run()
# (que fija allow_self_approval en Autoevaluacion SGC y No Conformidad SGC) se
# llegara a ejecutar. Ahora la ruta se deriva del propio archivo -> funciona en
# cualquier bench, y los 3 pasos quedan aislados: uno que falla no bloquea a los demás.
YAML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coneau-programas-2025.yaml")


def run():
    frappe.flags.in_patch = True
    frappe.flags.in_fixtures = True
    fallidos = []
    try:
        for nombre, fn in [
            ("f2_fields", f2_fields.run),
            ("f2_load_coneau", lambda: f2_load_coneau.run(YAML)),
            ("f2_workflow", f2_workflow.run),
        ]:
            try:
                fn()
                frappe.db.commit()
                print(f"== {nombre} OK ==")
            except Exception:
                frappe.db.rollback()
                fallidos.append(nombre)
                frappe.log_error(title=f"f2_run_all: fallo en {nombre}")
                print(f"  [FALLO] {nombre} — ver Error Log")
    finally:
        frappe.flags.in_patch = False
        frappe.flags.in_fixtures = False
    print("F2 SETUP DONE" + (f" (fallidos: {', '.join(fallidos)})" if fallidos else ""))
    return {"fallidos": fallidos}
