# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Canal de soporte (#56): a qué helpdesk van los problemas reportados desde el sistema."""

import frappe
from frappe import _
from frappe.model.document import Document


class ConfiguracionSoporte(Document):
    def validate(self):
        if self.tiempo_espera is not None and self.tiempo_espera <= 0:
            self.tiempo_espera = 10
        if not self.activo:
            return
        if self.proveedor == "Zammad":
            faltan = [e for c, e in (("zammad_url", _("URL")), ("zammad_grupo", _("grupo de destino")))
                      if not (self.get(c) or "").strip()]
            if not self.get_password("zammad_token", raise_exception=False):
                faltan.append(_("token"))
            if faltan:
                frappe.throw(_("Para activar el canal con Zammad falta: {0}.").format(", ".join(faltan)))
            if not self.zammad_url.startswith("https://"):
                frappe.throw(_("La URL de Zammad debe ser https: el token viaja en cada petición."))
        elif not self.correo_soporte:
            frappe.throw(_("Para activar el canal por correo indique el correo de soporte."))
