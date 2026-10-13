"""F2 runner — fields -> workflows, en orden, con in_patch.
Ejecutar: echo 'from sgc.setup import f2_run_all; f2_run_all.run()' | bench --site sgc.localhost console

Hasta #47 cargaba aquí también el marco CONEAU, en toda instancia nueva. Ahora lo
carga `marcos_normativos` solo si la instancia lo declara en `sgc_marcos`.
"""
import frappe

from sgc.setup import f2_fields, f2_workflow

# Los pasos quedan aislados: uno que falla no bloquea a los demás (hallazgo del
# 2026-07-19: un fallo de la carga del marco impedía que f2_workflow corriera).


def run():
    frappe.flags.in_patch = True
    frappe.flags.in_fixtures = True
    fallidos = []
    try:
        for nombre, fn in [
            ("f2_fields", f2_fields.run),
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
