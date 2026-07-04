"""F1 scaffold — crea los 6 Module Def del SGC (uno por grupo de agente).
Ejecutar: bench --site sgc.localhost execute sgc.setup.f0_modules.run
"""
import frappe

MODULES = [
    "SGC Estructura",   # A1: estructura + config (marcos, unidades, programas, indicadores)
    "SGC Nucleo",       # A2: acreditación + mejora core (autoeval, evidencias, NC, CAPA)
    "SGC Auditoria",    # B1: auditoría interna + revisión por la dirección
    "SGC Riesgos",      # B2: riesgos/GRC + obligaciones a entes
    "SGC Gobierno",     # B3: satisfacción/grupos de interés + comités/actas/política
    "SGC Procesos",     # B4: gestión por procesos + licenciamiento/IAC
]


def run():
    for m in MODULES:
        if not frappe.db.exists("Module Def", m):
            frappe.get_doc({
                "doctype": "Module Def",
                "module_name": m,
                "app_name": "sgc",
                "custom": 0,
            }).insert(ignore_permissions=True)
    frappe.db.commit()
    print("Module Defs OK:", ", ".join(MODULES))
