"""Chequeo de la identidad de la instancia: ¿dice de quién es? (#50)

Sin identidad declarada el producto se presenta neutro —«SGC», sin logotipo— y
los documentos impresos salen sin el nombre de la institución (#73). Funciona,
pero un documento oficial sin nombre no sirve: AVISO. El logotipo es INFO.

Lo que no se puede comprobar desde aquí es si la identidad declarada es la
CORRECTA: eso lo sabe quien despliega, no la base de datos.
"""

import frappe

from sgc.verificacion import AVISO, INFO, Hallazgo


def identidad_declarada():
    conf = frappe.conf or {}
    faltan = []
    if not (conf.get("sgc_app_name") or "").strip():
        faltan.append("sgc_app_name — el sistema se llama «SGC» a secas")
    # No vale `f3b_branding.nombre_institucion()` a secas: su último recurso es el
    # `app_name` de System Settings, que en un sitio neutro es «SGC», y entonces
    # el PDF lleva «SGC» como institución y esto diría que está bien.
    if not ((conf.get("sgc_institucion") or "").strip() or frappe.db.get_default("company")):
        faltan.append("sgc_institucion — los PDF salen sin el nombre de la institución")

    hallazgos = []
    if faltan:
        hallazgos.append(
            Hallazgo(
                AVISO,
                "identidad-sin-declarar",
                "La instancia usa la identidad neutra del producto.",
                detalle=faltan,
                remedio="Declarar las claves con `bench --site <sitio> set-config` y migrar (ver `sgc.setup.f3b_branding`).",
            )
        )
    if not (conf.get("sgc_logo") or "").strip():
        hallazgos.append(
            Hallazgo(
                INFO,
                "identidad-sin-logo",
                "No hay logotipo declarado: la cabecera muestra solo el nombre.",
                remedio="Subir el logotipo y declarar su ruta en `sgc_logo`.",
            )
        )
    return hallazgos


CHEQUEOS = [identidad_declarada]
