# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Carpeta documental: el árbol libre que cada institución arma para su documentación."""

import frappe
from frappe.utils.nestedset import NestedSet

# La raíz del árbol, con nombre fijo. Con una sola carpeta de primer nivel, la
# vista de árbol de Frappe la toma como raíz y la rotula con su `name`
# (`treeview.js`, get_root): una carpeta cualquiera saldría como «CD-00046».
RAIZ = "Carpetas documentales"


class CarpetaDocumental(NestedSet):
    def validate(self):
        if self.name != RAIZ and not self.parent_carpeta_documental and frappe.db.exists(self.doctype, RAIZ):
            self.parent_carpeta_documental = RAIZ


def asegurar_raiz():
    """Crea la carpeta raíz si falta. Idempotente (lo llama el despliegue)."""
    if frappe.db.exists("Carpeta Documental", RAIZ):
        return False
    frappe.get_doc({"doctype": "Carpeta Documental", "nombre": RAIZ, "is_group": 1}).insert(
        ignore_permissions=True, set_name=RAIZ
    )
    return True
