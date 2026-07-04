"""Borra TODOS los datos operativos/demo del SGC en los 6 módulos, dejando
intactos los frameworks normativos y la estructura.

Auto-descubre los DocTypes operativos: todos los de la app `sgc` MENOS la
lista blanca (marcos, elementos, indicadores-definición, programas, unidades,
periodos). En producción real esos operativos están en 0 hasta que llegan
datos reales, así que borrarlos = eliminar exactamente el demo.

Ejecutar: bench --site calidad.upeu.edu.pe execute sgc.setup.demo_cleanup.run
"""

import frappe

# Se CONSERVAN (frameworks normativos + estructura institucional).
_KEEP = {
    "Marco Normativo", "Elemento Marco", "Escala Valoracion", "Nivel Escala", "Nivel Marco",
    "Indicador", "Ficha Indicador", "Indicador Criterio",
    "Programa", "Programa Sede", "Unidad Organica", "Periodo Academico",
}


def run():
    mods = frappe.get_all("Module Def", {"app_name": "sgc"}, pluck="name")
    dts = frappe.get_all("DocType", {"module": ["in", mods], "istable": 0}, pluck="name")
    operativos = [d for d in dts if d not in _KEEP]

    total = 0
    # Varias pasadas para respetar dependencias por Link.
    for _ in range(5):
        remaining = 0
        for dt in operativos:
            if not frappe.db.table_exists(dt):
                continue
            for name in frappe.get_all(dt, pluck="name"):
                try:
                    frappe.delete_doc(dt, name, force=1, ignore_permissions=True, delete_permanently=True)
                    total += 1
                except Exception:
                    remaining += 1
        frappe.db.commit()
        if remaining == 0:
            break

    print("DEMO_CLEANUP: %d registros operativos eliminados en %d DocTypes. "
          "Frameworks normativos y estructura intactos." % (total, len(operativos)))
