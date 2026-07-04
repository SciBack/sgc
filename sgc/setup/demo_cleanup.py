"""Borra TODOS los datos operativos/demo del SGC, dejando intactos los
frameworks normativos (Marco/Elemento Marco/Indicador) y la estructura
(Programa, Unidad Orgánica, Periodo).

En producción real estos DocTypes están en 0 hasta que llegan datos reales,
así que borrar todos sus registros = eliminar exactamente el demo.

Ejecutar: bench --site calidad.upeu.edu.pe execute sgc.setup.demo_cleanup.run
"""

import frappe

# Orden: dependientes primero (Links).
_OPERATIVOS = [
    "Accion Mejora",
    "Plan Mejora",
    "No Conformidad",
    "Hallazgo",
    "Evidencia Enlace",
    "Evidencia",
    "Valor Indicador",
    "Trazabilidad",
    "Valoracion Criterio",
    "Valoracion Estandar",
    "Autoevaluacion",
]


def run():
    total = 0
    for dt in _OPERATIVOS:
        if not frappe.db.exists("DocType", dt) or not frappe.db.table_exists(dt):
            continue
        for name in frappe.get_all(dt, pluck="name"):
            try:
                frappe.delete_doc(dt, name, force=1, ignore_permissions=True, delete_permanently=True)
                total += 1
            except Exception as e:
                print("  no se pudo borrar %s %s: %s" % (dt, name, str(e)[:80]))
        frappe.db.commit()
    print("DEMO_CLEANUP: %d registros operativos eliminados. "
          "Frameworks normativos y estructura intactos." % total)
