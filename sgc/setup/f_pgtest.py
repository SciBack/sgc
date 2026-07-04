"""Test de compatibilidad Postgres — corre todo el setup + E2E sobre el site pg.
bench --site sgc-pg.localhost execute sgc.setup.f_pgtest.run
"""
import frappe
from sgc.setup import f0_modules, f2_run_all, f3_informe, f3b_rbac, f2_e2e_test, f3_e2e

STEPS = [f0_modules, f2_run_all, f3_informe, f3b_rbac, f2_e2e_test, f3_e2e]


def run():
    for step in STEPS:
        nm = step.__name__.split(".")[-1]
        try:
            step.run()
            frappe.db.commit()
            print("OK_STEP:", nm)
        except Exception as e:
            import traceback
            print("FAIL_STEP:", nm, "|", type(e).__name__, "|", str(e)[:300])
            traceback.print_exc()
            return
    print("PG_ALL_GREEN")
