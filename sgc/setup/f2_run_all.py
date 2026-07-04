"""F2 runner — fields -> loader CONEAU -> workflows, en orden, con in_patch.
Ejecutar: echo 'from sgc.setup import f2_run_all; f2_run_all.run()' | bench --site sgc.localhost console
"""
import frappe
from sgc.setup import f2_fields, f2_load_coneau, f2_workflow

YAML = "/workspace/development/frappe-bench/apps/sgc/sgc/setup/coneau-programas-2025.yaml"


def run():
    frappe.flags.in_patch = True
    frappe.flags.in_fixtures = True
    try:
        f2_fields.run()
        frappe.db.commit()
        print("== f2_fields OK ==")
        f2_load_coneau.run(YAML)
        frappe.db.commit()
        print("== f2_load_coneau OK ==")
        f2_workflow.run()
        frappe.db.commit()
        print("== f2_workflow OK ==")
    finally:
        frappe.flags.in_patch = False
        frappe.flags.in_fixtures = False
    print("F2 SETUP DONE")
