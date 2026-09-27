# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Comunicado a los usuarios: nuevas funcionalidades y mantenimientos (#92).

Dos cosas que un servicio promete y que hasta #92 se hacían fuera del sistema:
comunicar lo nuevo a los usuarios responsables y avisar **con antelación** de un
mantenimiento programado.

Reglas:

1. Se envía a los usuarios activos que tengan alguno de los roles elegidos.
2. Un mantenimiento se avisa con al menos `ANTELACION_HORAS` de antelación, y su
   fin (si se indica) va después de su inicio.
3. Enviar lo sella el sistema (quién, cuándo, a cuántos) y el comunicado queda
   cerrado: no se reenvía ni se reescribe lo que ya salió.
4. Pasa por `sgc.correo.enviar`: modo de ensayo, lista blanca y registro.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, get_datetime, now_datetime

from sgc.correo import enviar

MANTENIMIENTO = "Mantenimiento programado"
ANTELACION_HORAS = 24
CUENTAS_TECNICAS = {"Administrator", "Guest"}

# Lo que ya no cambia una vez enviado.
CONTENIDO = ("asunto", "tipo", "mensaje", "inicio_mantenimiento", "fin_mantenimiento")


def destinatarios_de_roles(roles):
    """Correos de los usuarios activos con alguno de `roles`, sin cuentas técnicas."""
    if not roles:
        return []
    usuarios = frappe.get_all(
        "Has Role", filters={"role": ["in", list(roles)], "parenttype": "User"},
        pluck="parent", distinct=True,
    )
    correos = []
    for u in sorted(set(usuarios) - CUENTAS_TECNICAS):
        correo, activo = frappe.db.get_value("User", u, ["email", "enabled"]) or (None, 0)
        if activo and correo and correo not in correos:
            correos.append(correo)
    return correos


class Comunicado(Document):
    def validate(self):
        anterior = self.get_doc_before_save()
        if anterior and anterior.estado == "Enviado":
            cambiados = [c for c in CONTENIDO if self.get(c) != anterior.get(c)]
            if cambiados or self._roles() != {r.rol for r in anterior.roles}:
                frappe.throw(_("El comunicado ya se envió: no se modifica lo que salió."),
                             title=_("Comunicado enviado"))
        if self.tipo == MANTENIMIENTO:
            if not self.inicio_mantenimiento:
                frappe.throw(_("Indique cuándo empieza el mantenimiento."))
            if self.fin_mantenimiento and get_datetime(self.fin_mantenimiento) <= get_datetime(
                self.inicio_mantenimiento
            ):
                frappe.throw(_("El fin del mantenimiento debe ser posterior a su inicio."))

    def _roles(self):
        return {r.rol for r in self.roles}

    @frappe.whitelist()
    def enviar(self):
        """Envía el comunicado. Una sola vez."""
        self.check_permission("write")
        if self.estado == "Enviado":
            frappe.throw(_("Este comunicado ya se envió el {0}.").format(self.fecha_envio),
                         title=_("Ya enviado"))
        if self.tipo == MANTENIMIENTO:
            limite = add_to_date(now_datetime(), hours=ANTELACION_HORAS)
            if get_datetime(self.inicio_mantenimiento) < limite:
                frappe.throw(
                    _("Un mantenimiento se avisa con al menos {0} horas de antelación: "
                      "el inicio es demasiado próximo.").format(ANTELACION_HORAS),
                    title=_("Sin antelación"),
                )
        correos = destinatarios_de_roles(self._roles())
        if not correos:
            frappe.throw(_("Ningún usuario activo con correo tiene los roles elegidos."),
                         title=_("Sin destinatarios"))

        cuerpo = self.mensaje or ""
        if self.tipo == MANTENIMIENTO:
            cuerpo = _("<p><b>Mantenimiento programado:</b> desde {0}{1}.</p>").format(
                frappe.utils.format_datetime(self.inicio_mantenimiento),
                _(" hasta {0}").format(frappe.utils.format_datetime(self.fin_mantenimiento))
                if self.fin_mantenimiento else "",
            ) + cuerpo
        resultado = enviar(correos, "[{0}] {1}".format(self.tipo, self.asunto), cuerpo,
                           self.doctype, self.name, origen="Comunicado")

        self.estado = "Enviado"
        self.enviado_por = frappe.session.user
        self.fecha_envio = now_datetime()
        self.n_destinatarios = len(resultado["enviados"])
        self.n_retenidos = len(resultado["retenidos"])
        self.save()
        return {"enviados": self.n_destinatarios, "retenidos": self.n_retenidos}
