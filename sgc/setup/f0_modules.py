"""F1 scaffold — crea los Module Def del SGC (uno por área de trabajo).
Ejecutar: bench --site sgc.localhost execute sgc.setup.f0_modules.run
"""
import frappe

MODULES = [
    # Un módulo por ÁREA de trabajo de la DPGC (12-oct-2026, menús por área); el nombre
    # visible de cada uno está en translations/es.csv. Lo mantiene al día el parche
    # `modulos_por_area` en los sitios existentes.
    "SGC Procesos",      # Procesos
    "SGC Documental",    # Documentos
    "SGC Indicadores",   # Indicadores
    "SGC Acreditacion",  # Acreditación y licenciamiento
    "SGC Nucleo",        # Mejora continua
    "SGC Auditoria",     # Auditoría
    "SGC Riesgos",       # Riesgos
    "SGC Gobierno",      # Dirección y partes interesadas
    "SGC Estructura",    # Configuración
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
