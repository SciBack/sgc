# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Contraseña con elementos seguros (B4): letras, números, mayúsculas y minúsculas.

Frappe mide la fuerza por entropía (zxcvbn, `minimum_password_score` en System
Settings) y no permite exigir clases de caracteres. Los pliegos lo piden
literal. Esto AÑADE la regla de clases a la de Frappe; no la sustituye: una
contraseña tiene que pasar las dos.

Frappe cambia una contraseña por dos caminos, y los dos quedan cubiertos:

- **El formulario del usuario** (`new_password`): el controlador la vacía en su
  `validate` (`user.py`, `self.new_password = ""`), así que la regla va en
  `before_validate`, que corre antes.
- **Restablecer o cambiar la propia** (`update_password`): no pasa por
  `User.validate`; se sobrescribe el método expuesto por la API.

El medidor de la pantalla (`test_password_strength`) también la aplica, para
que la persona lo sepa antes de enviar.

Se apaga por sitio con `sgc_contrasena_clases: 0` en `site_config.json`, y
también cuando la política de contraseñas de Frappe está apagada.
"""

import re

import frappe
from frappe import _

LONGITUD_MINIMA = 8
CLASES = (
    (re.compile(r"[a-záéíóúüñ]"), "una minúscula"),
    (re.compile(r"[A-ZÁÉÍÓÚÜÑ]"), "una mayúscula"),
    (re.compile(r"\d"), "un número"),
)


def activa():
    return bool(frappe.get_system_settings("enable_password_policy")) and \
        frappe.conf.get("sgc_contrasena_clases", 1) not in (0, "0", False)


def faltas(contrasena):
    """Lo que le falta a la contraseña según la regla de clases. Vacío = cumple."""
    contrasena = contrasena or ""
    faltan = [texto for patron, texto in CLASES if not patron.search(contrasena)]
    if len(contrasena) < LONGITUD_MINIMA:
        faltan.insert(0, _("al menos {0} caracteres").format(LONGITUD_MINIMA))
    return faltan


def _mensaje(faltan):
    return _("La contraseña necesita {0}. Use letras mayúsculas y minúsculas, y números.").format(
        ", ".join(faltan))


def validar(contrasena):
    if not activa():
        return
    faltan = faltas(contrasena)
    if faltan:
        frappe.throw(_mensaje(faltan), title=_("Contraseña poco segura"))


def antes_de_validar_usuario(doc, method=None):
    """doc_events User.before_validate: la contraseña que se fija desde el formulario."""
    if doc.get("new_password"):
        validar(doc.new_password)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def update_password(new_password, logout_all_sessions=0, key=None, old_password=None):
    """`frappe.core.doctype.user.user.update_password` con la regla de clases delante."""
    from frappe.core.doctype.user import user

    validar(new_password)
    return user.update_password(
        new_password, logout_all_sessions=logout_all_sessions, key=key, old_password=old_password
    )


@frappe.whitelist(allow_guest=True)
def test_password_strength(new_password, key=None, old_password=None, user_data=None):
    """El medidor de la pantalla: la fuerza de Frappe y, además, las clases."""
    from frappe.core.doctype.user import user

    resultado = user.test_password_strength(new_password, key=key, old_password=old_password, user_data=user_data)
    if not resultado or not new_password or not activa():
        return resultado
    faltan = faltas(new_password)
    if faltan:
        feedback = resultado.setdefault("feedback", {})
        feedback["password_policy_validation_passed"] = False
        feedback["warning"] = _mensaje(faltan)
    return resultado
