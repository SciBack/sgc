"""F3 E2E — completa la autoevaluación demo, confirma niveles, finaliza vigencia
y genera el Informe SINEACE en PDF.
Ejecutar: echo 'from sgc.setup import f3_e2e; f3_e2e.run()' | bench --site sgc.localhost console
"""
import frappe
from sgc import confirmacion, informe

AE = "AE-ENF-LIMA-2026I"


def _criterios(est):
    return frappe.get_all("Elemento Marco",
                          {"parent_elemento_marco": est, "es_valorable": 1}, pluck="name")


def run():
    frappe.flags.in_patch = True
    frappe.local.lang = "es"
    # E1=LP, E2=NL, E3=L ya valorados; valorar E4..E10 como "Cumple" (-> LP)
    for n in range(4, 11):
        est = f"CONEAU-E{n}"
        for cr in _criterios(est):
            if frappe.db.exists("Valoracion Criterio", {"autoevaluacion": AE, "criterio": cr}):
                continue
            vc = frappe.get_doc({"doctype": "Valoracion Criterio", "autoevaluacion": AE,
                                 "criterio": cr, "cumple": "Cumple"})
            vc.flags.ignore_permissions = True
            vc.insert()
    frappe.db.commit()

    r1 = confirmacion.confirmar_todos_propuestos(AE)
    frappe.db.commit()
    print("confirmar_todos:", r1)

    r2 = confirmacion.finalizar_vigencia(AE)
    frappe.db.commit()
    print("finalizar_vigencia:", r2)

    pdf = informe.generar_pdf(AE, adjuntar=True)
    print("INFORME_PDF bytes:", len(pdf) if pdf else 0)
    frappe.db.commit()
    print("F3 E2E DONE")
