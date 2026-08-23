"""Creación idempotente de DocTypes para los scripts de instalación.

Esta función vivía copiada BYTE POR BYTE en los seis `f1_*.py` (estructura,
núcleo, procesos, gobierno, riesgos y auditoría). Lo único que cambiaba entre
ellos era la constante `MODULE` que cada script define, y que la copia leía de
su propio ámbito global.

Cada `f1_*` conserva su `_dt` como envoltura de dos líneas: así las 72 llamadas
existentes no cambian y cada script sigue declarando a qué módulo pertenecen sus
DocTypes, que es la única diferencia real entre ellos.
"""

import frappe


def crear_doctype(name, module, fields, istable=0, is_tree=0, autoname=None,
                  title_field=None, search_fields=None, track_changes=1):
    """Crea el DocType si no existe. Idempotente: si ya está, no lo toca.

    Nunca actualiza uno existente, y es a propósito: un DocType ya creado puede
    llevar encima campos y permisos ajustados en el sitio, y reescribirlo desde
    el script los perdería. Añadir un campo a un DocType vivo se hace por el
    camino de `f2_fields.py`, no volviendo a declararlo aquí.
    """
    if frappe.db.exists("DocType", name):
        return
    doc = {
        "doctype": "DocType", "name": name, "module": module, "custom": 0,
        "istable": istable, "is_tree": is_tree,
        "editable_grid": 1 if istable else 0,
        "track_changes": 0 if istable else track_changes,
        "fields": fields,
        "permissions": [] if istable else [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1}
        ],
    }
    if autoname:
        doc["autoname"] = autoname
    if title_field:
        doc["title_field"] = title_field
    if search_fields:
        doc["search_fields"] = search_fields
    frappe.get_doc(doc).insert(ignore_permissions=True)
