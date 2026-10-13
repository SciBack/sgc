"""Chequeo del inicio de sesión institucional (#46).

Un sitio sin SSO funciona —se entra con contraseña—, pero tiene que ser un estado DECLARADO:
por eso es INFO y no silencio. Si `site_config` declara SSO y el registro no coincide con lo
declarado, es AVISO: alguien espera entrar con su cuenta institucional y el botón no lo hará.
"""

import frappe

from sgc.setup import f3b_sso
from sgc.verificacion import AVISO, INFO, Hallazgo


def inicio_de_sesion_institucional():
    try:
        cfg = f3b_sso.leer(frappe.conf)
    except f3b_sso.ConfiguracionInvalida as e:
        return [Hallazgo(AVISO, "sso-config-invalida", f"La configuración de SSO en site_config no es válida: {e}.",
                         remedio="Corregir las claves sgc_sso_* de site_config.json y volver a migrar.")]

    activos = frappe.get_all("Social Login Key", filters={"enable_social_login": 1}, pluck="name")
    if cfg is None:
        if activos:
            return []  # hay un registro creado a mano: funciona, solo que no lo gestiona el despliegue
        return [Hallazgo(INFO, "sso-no-configurado",
                         "No hay inicio de sesión institucional: solo se entra con usuario y contraseña.",
                         remedio="Declarar sgc_sso_issuer, sgc_sso_client_id y sgc_sso_client_secret en "
                                 "site_config.json y migrar (ver sgc/setup/F3B-SSO-DEPLOY.md).")]

    esperado = f3b_sso.componer(cfg)
    if not frappe.db.exists("Social Login Key", cfg["proveedor"]):
        detalle = [f"No existe el registro «{cfg['proveedor']}»."]
    else:
        real = frappe.db.get_value("Social Login Key", cfg["proveedor"],
                                   ["base_url", "client_id", "redirect_url", "enable_social_login"], as_dict=True)
        detalle = [f"{campo}: es «{real[campo]}», se esperaba «{esperado[campo]}»"
                   for campo in ("base_url", "client_id", "redirect_url", "enable_social_login")
                   if str(real[campo] or "") != str(esperado[campo])]
    if not detalle:
        return []
    return [Hallazgo(AVISO, "sso-desalineado",
                     "El inicio de sesión institucional no coincide con lo declarado en site_config.",
                     detalle=detalle, remedio="Volver a migrar: el paso f3b_sso lo alinea.")]


CHEQUEOS = [inicio_de_sesion_institucional]
