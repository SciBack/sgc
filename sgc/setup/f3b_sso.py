"""F3b SSO — inicio de sesión institucional (OIDC) del SGC, configurado desde el despliegue (#46).

Crea o actualiza, de forma idempotente, el `Social Login Key` con el que Frappe ofrece el botón
«Iniciar sesión con …» contra el proveedor de identidad de la institución. **No lleva ningún
dato de una institución**: todo sale de `site_config.json`, igual que la identidad visual
(`f3b_branding`). Corre en cada `migrate` como paso del orquestador.

Claves (todas en `site_config.json` del sitio):

    sgc_sso_issuer         URL del issuer OIDC (p. ej. https://idp.example.org/realms/x).
                           SIN ella el paso no hace nada y lo dice: un sitio sin SSO es un
                           estado válido, pero declarado, no un olvido.
    sgc_sso_client_id      Client ID registrado en el proveedor.
    sgc_sso_client_secret  Client secret. Solo es obligatorio para CREAR el registro: si ya
                           existe con un secreto, se conserva. Nunca se imprime.
    sgc_sso_proveedor      Nombre del registro. Por defecto «keycloak», que usa el callback
                           NATIVO de Frappe (`login_via_keycloak`). Con otro nombre se usa el
                           callback genérico `custom/<proveedor>`, que también funciona.
    sgc_sso_etiqueta       Texto del botón de inicio de sesión. Por defecto «Cuenta institucional».
    sgc_sso_rutas          Opcional: {"autorizacion", "token", "usuario"} relativas al issuer.
                           Por defecto, las de un realm de Keycloak.
    sgc_sso_habilitado     Opcional, 1 por defecto. 0 deja el registro creado pero apagado.

Decisiones verificadas contra el código de Frappe v16:

1) El callback nativo `login_via_keycloak` busca el `Social Login Key` con name «keycloak»
   (`frappe/integrations/oauth2_logins.py`). El genérico `custom` resuelve el proveedor por el
   último tramo de la ruta y exige que exista un registro con ese name.
2) El name se autogenera con `frappe.scrub(provider_name)` (`SocialLoginKey.autoname`), y
   `provider_name` —que es además el TEXTO DEL BOTÓN— es set_only_once. Por eso se crea con
   `provider_name = <proveedor>` (para fijar el name) y la etiqueta se escribe después.
3) Con `custom_base_url=1`, Frappe compone las URLs como `base_url + ruta`
   (`frappe/utils/oauth.py`), así que `base_url` es el ISSUER y las rutas van relativas.
4) Identidad (utils/oauth.py): el usuario se busca POR CORREO (`email|upn|unique_name`) y el
   identificador social es `user_id_property` (`sub`). Con el autorregistro desactivado, un
   correo que no exista en el sitio no entra.

Cambiar `sgc_sso_proveedor` y volver a migrar deja solo el nuevo: el registro que este paso
gestionaba antes se elimina. Un `Social Login Key` creado a mano, que este paso no gestiona,
nunca se toca.
"""

import json
import re

import frappe

PROVEEDOR_POR_DEFECTO = "keycloak"
ETIQUETA_POR_DEFECTO = "Cuenta institucional"
NATIVOS = {"keycloak": "/api/method/frappe.integrations.oauth2_logins.login_via_keycloak"}
RUTA_GENERICA = "/api/method/frappe.integrations.oauth2_logins.custom/{proveedor}"
RUTAS_POR_DEFECTO = {
    "autorizacion": "/protocol/openid-connect/auth",
    "token": "/protocol/openid-connect/token",
    "usuario": "/protocol/openid-connect/userinfo",
}
# Qué registro gestiona este paso: así un cambio de proveedor no deja el anterior vivo, y un
# registro creado a mano no se borra nunca.
CLAVE_GESTIONADO = "sgc_sso_proveedor_gestionado"


class ConfiguracionInvalida(Exception):
    pass


# ---------------------------------------------------------------- lógica pura


def leer(conf):
    """La configuración de SSO declarada en `conf` (un site_config), o None si no hay.

    Normaliza y valida sin tocar la base de datos. El secreto viaja aparte del resto
    para que nada que se imprima o se compare lo arrastre.
    """
    issuer = str(conf.get("sgc_sso_issuer") or "").strip().rstrip("/")
    if not issuer:
        return None
    if not issuer.startswith("https://"):
        raise ConfiguracionInvalida(f"sgc_sso_issuer debe ser una URL https:// (es «{issuer}»)")
    client_id = str(conf.get("sgc_sso_client_id") or "").strip()
    if not client_id:
        raise ConfiguracionInvalida("falta sgc_sso_client_id")
    proveedor = str(conf.get("sgc_sso_proveedor") or PROVEEDOR_POR_DEFECTO).strip()
    if not re.fullmatch(r"[a-z0-9_]+", proveedor):
        raise ConfiguracionInvalida(
            f"sgc_sso_proveedor solo admite minúsculas, cifras y «_» (es «{proveedor}»): es el name del registro"
        )
    rutas = {**RUTAS_POR_DEFECTO, **(conf.get("sgc_sso_rutas") or {})}
    for clave, ruta in rutas.items():
        if not str(ruta).startswith("/"):
            raise ConfiguracionInvalida(f"sgc_sso_rutas.{clave} debe empezar por «/» (es «{ruta}»)")
    return {
        "issuer": issuer,
        "client_id": client_id,
        "client_secret": str(conf.get("sgc_sso_client_secret") or "").strip() or None,
        "proveedor": proveedor,
        "etiqueta": str(conf.get("sgc_sso_etiqueta") or ETIQUETA_POR_DEFECTO).strip(),
        "rutas": rutas,
        "habilitado": 1 if conf.get("sgc_sso_habilitado", 1) else 0,
    }


def componer(cfg):
    """Los campos del `Social Login Key` (sin secreto ni etiqueta) a partir de la configuración."""
    return {
        "social_login_provider": "Custom",
        "custom_base_url": 1,
        "base_url": cfg["issuer"],
        "authorize_url": cfg["rutas"]["autorizacion"],
        "access_token_url": cfg["rutas"]["token"],
        "api_endpoint": cfg["rutas"]["usuario"],
        "redirect_url": NATIVOS.get(cfg["proveedor"], RUTA_GENERICA.format(proveedor=cfg["proveedor"])),
        "auth_url_data": json.dumps({"response_type": "code", "scope": "openid email profile"}),
        "user_id_property": "sub",
        # Sin icono: Frappe solo trata `icon` como clase de icono si el proveedor se llama «Custom»;
        # con cualquier otro nombre lo pone como <img src=…> y el botón sale con una imagen rota.
        "icon": "",
        "client_id": cfg["client_id"],
        "enable_social_login": cfg["habilitado"],
    }


# ---------------------------------------------------------------- aplicación


def aplicar(cfg):
    """Crea o actualiza el registro. Devuelve (name, acción). Idempotente."""
    campos = componer(cfg)
    proveedor = cfg["proveedor"]
    if frappe.db.exists("Social Login Key", proveedor):
        doc = frappe.get_doc("Social Login Key", proveedor)
        cambios = {k: v for k, v in campos.items()
                   if k != "social_login_provider" and str(doc.get(k) or "") != str(v)}
        doc.update(cambios)
        # El secreto se guarda cifrado: solo se reescribe si se declaró y es distinto. Si no se
        # declara, se conserva el que ya tiene el registro.
        secreto_nuevo = bool(cfg["client_secret"]) and cfg["client_secret"] != doc.get_password(
            "client_secret", raise_exception=False)
        if secreto_nuevo:
            doc.client_secret = cfg["client_secret"]
        accion = "actualizado" if cambios or secreto_nuevo else "sin cambios"
    else:
        if not cfg["client_secret"]:
            raise ConfiguracionInvalida("falta sgc_sso_client_secret para crear el registro")
        doc = frappe.new_doc("Social Login Key")
        doc.provider_name = proveedor  # fija el name (autoname = scrub(provider_name))
        doc.update(campos)
        doc.client_secret = cfg["client_secret"]
        accion = "creado"
    if accion != "sin cambios":
        doc.flags.ignore_permissions = True
        doc.save()
    # provider_name es set_only_once, y es el texto del botón: se escribe aparte.
    if frappe.db.get_value("Social Login Key", doc.name, "provider_name") != cfg["etiqueta"]:
        frappe.db.set_value("Social Login Key", doc.name, "provider_name", cfg["etiqueta"])
        if accion == "sin cambios":
            accion = "actualizado"
    return doc.name, accion


def _retirar_anterior(actual):
    """Si este paso gestionaba otro proveedor, lo elimina. Nunca toca uno creado a mano."""
    anterior = frappe.db.get_default(CLAVE_GESTIONADO)
    if anterior and anterior != actual and frappe.db.exists("Social Login Key", anterior):
        frappe.delete_doc("Social Login Key", anterior, ignore_permissions=True, force=True)
        return anterior
    return None


def run():
    """Paso del orquestador: aplica la configuración de site_config, o declara que no la hay."""
    try:
        cfg = leer(frappe.conf)
    except ConfiguracionInvalida as e:
        print(f"SSO: configuración inválida en site_config — {e}. No se toca nada.")
        return "invalida"
    if cfg is None:
        print("SSO: no configurado (sin sgc_sso_issuer en site_config). Solo se entra con contraseña; "
              "no se crea ni se toca ningún Social Login Key.")
        return "sin-configurar"
    try:
        nombre, accion = aplicar(cfg)
    except ConfiguracionInvalida as e:
        print(f"SSO: {e}. No se crea nada.")
        return "invalida"
    retirado = _retirar_anterior(nombre)
    frappe.db.set_default(CLAVE_GESTIONADO, nombre)
    frappe.db.commit()
    print(f"SSO {accion}: «{cfg['etiqueta']}» (registro «{nombre}», "
          f"{'activo' if cfg['habilitado'] else 'apagado'}) · issuer {cfg['issuer']} · "
          f"redirect_uri {frappe.utils.get_url(componer(cfg)['redirect_url'])}"
          + (f" · retirado el anterior «{retirado}»" if retirado else ""))
    return accion
