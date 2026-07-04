"""F1 runner — ejecuta los 6 scripts de creación de DocTypes en orden de dependencia.
Activa frappe.flags.in_patch para permitir Links hacia adelante/circulares
(el guard check_link_table_options se salta con in_patch/in_fixtures).
Ejecutar:  echo 'from sgc.setup import f1_run_all; f1_run_all.run()' | bench --site sgc.localhost console
"""
import frappe
from sgc.setup import (
    f1_estructura, f1_nucleo, f1_auditoria,
    f1_riesgos, f1_gobierno, f1_procesos,
)

ORDER = [f1_estructura, f1_nucleo, f1_auditoria, f1_riesgos, f1_gobierno, f1_procesos]


def run():
    frappe.flags.in_patch = True
    frappe.flags.in_fixtures = True
    created = []
    try:
        for mod in ORDER:
            before = frappe.db.count("DocType", {"custom": 0})
            mod.run()
            frappe.db.commit()
            after = frappe.db.count("DocType", {"custom": 0})
            created.append((mod.__name__.split(".")[-1], after - before))
            print("  ->", mod.__name__.split(".")[-1], "(+%d DocTypes)" % (after - before))
    finally:
        frappe.flags.in_patch = False
        frappe.flags.in_fixtures = False
    frappe.db.commit()
    total = frappe.db.count("DocType", {"module": ["like", "SGC%"]})
    print("F1 ALL DONE — DocTypes en módulos SGC:", total)
    return created
