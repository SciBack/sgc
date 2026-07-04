"""F3b SSO — SSO OIDC del SGC-Frappe contra Keycloak UPeU (realm `upeu`).

Crea/actualiza (idempotente) un DocType **Social Login Key** que habilita el
login OIDC de Frappe contra Keycloak. NO contiene secretos: `client_id` y
`client_secret` son PARÁMETROS que el orquestador inyecta en el despliegue
desde `~/.secrets/sgc-sso.env` (ver F3B-SSO-DEPLOY.md).

Decisiones verificadas contra el código de Frappe v16
(apps/frappe/frappe/integrations/oauth2_logins.py y
apps/frappe/frappe/utils/oauth.py):

1) Keycloak es proveedor NATIVO en Frappe v16 — existe el callback
   `login_via_keycloak` que llama `login_via_oauth2("keycloak", ...)`.
   Ese callback busca el Social Login Key cuyo `name == "keycloak"`.

2) El `name` del doc se autogenera con `frappe.scrub(provider_name)`
   (SocialLoginKey.autoname). Para que el callback nativo resuelva el
   proveedor, el `name` DEBE ser exactamente "keycloak", por lo que
   `provider_name` debe scrubbear a "keycloak" → usamos "Keycloak".
   (Si se usara "Keycloak UPeU", el name sería "keycloak_upeu" y el
   callback nativo NO lo encontraría; habría que caer al callback
   genérico `custom/<provider>`. Aquí elegimos el nativo por robustez.)

3) Con `custom_base_url=1`, Frappe compone las URLs como
   `base_url + path_relativo` (utils/oauth.py::build_oauth_url). Por eso
   `base_url` debe ser el ISSUER (`.../realms/upeu`) y los endpoints van
   como paths relativos `/protocol/openid-connect/{auth,token,userinfo}`.

4) Redirect URI (verificado): el sitio Frappe compone
   `get_url()` + `redirect_url` →
   `https://<host>/api/method/frappe.integrations.oauth2_logins.login_via_keycloak`

5) Mapeo de identidad (utils/oauth.py): email = `email|upn|unique_name`;
   first = `first_name|given_name|name`; last = `last_name|family_name`;
   userid social = `user_id_property` (default "sub"). Keycloak emite
   `sub`, `email`, `given_name`, `family_name`, `preferred_username`.

Ejecutar (en despliegue, con secretos ya cargados por el orquestador):
    bench --site <site> execute sgc.setup.f3b_sso.configurar_keycloak \
        --kwargs "{'client_id': '...', 'client_secret': '...'}"
"""

import json

import frappe

# name canónico del Social Login Key. Debe coincidir con el proveedor que
# busca el callback nativo login_via_keycloak → login_via_oauth2("keycloak").
PROVIDER_NAME = "Keycloak"          # frappe.scrub("Keycloak") == "keycloak"
PROVIDER_KEY = "keycloak"           # == name del doc (autoname/scrub)

# Callback nativo de Frappe v16 (ruta relativa; el sitio antepone su URL).
REDIRECT_PATH = "/api/method/frappe.integrations.oauth2_logins.login_via_keycloak"

# Endpoints OIDC relativos al issuer (se concatenan a base_url=issuer).
AUTHORIZE_PATH = "/protocol/openid-connect/auth"
TOKEN_PATH = "/protocol/openid-connect/token"
USERINFO_PATH = "/protocol/openid-connect/userinfo"


def configurar_keycloak(
    client_id,
    client_secret,
    issuer="https://keyid.upeu.edu.pe/realms/upeu",
    base_url="https://keyid.upeu.edu.pe",  # informativo; ver nota abajo
    enable=True,
):
    """Crea/actualiza (idempotente) el Social Login Key `keycloak`.

    Args:
        client_id: Client ID del cliente `sgc-frappe` en Keycloak (realm upeu).
                   Parámetro obligatorio, NO hardcodeado.
        client_secret: Client Secret del mismo cliente (confidential).
                   Parámetro obligatorio, NO hardcodeado.
        issuer: Issuer OIDC del realm. Se usa como `base_url` del doc para que
                Frappe (custom_base_url=1) resuelva los paths relativos OIDC.
        base_url: Se acepta por compatibilidad con el orquestador, pero el
                `base_url` efectivo del doc es el ISSUER (ver punto 3 del
                encabezado). Se ignora para el cálculo de endpoints.
        enable: si True, activa `enable_social_login`.

    Returns:
        str: el `name` del Social Login Key creado/actualizado ("keycloak").
    """
    # --- Validación: los secretos deben llegar y no vacíos (NO hardcodeados) ---
    if not client_id or not str(client_id).strip():
        frappe.throw(
            "configurar_keycloak: 'client_id' es obligatorio y no puede estar vacío. "
            "Inyéctalo desde ~/.secrets/sgc-sso.env en el despliegue."
        )
    if not client_secret or not str(client_secret).strip():
        frappe.throw(
            "configurar_keycloak: 'client_secret' es obligatorio y no puede estar vacío. "
            "Inyéctalo desde ~/.secrets/sgc-sso.env en el despliegue."
        )
    if not issuer or not str(issuer).strip():
        frappe.throw("configurar_keycloak: 'issuer' es obligatorio.")

    client_id = str(client_id).strip()
    client_secret = str(client_secret).strip()
    # base_url del doc = issuer (sin barra final) para que build_oauth_url
    # componga issuer + /protocol/openid-connect/... correctamente.
    issuer = str(issuer).strip().rstrip("/")

    frappe.flags.in_patch = True

    # scope OIDC estándar; response_type=code (Authorization Code Flow).
    auth_url_data = json.dumps(
        {"response_type": "code", "scope": "openid email profile"}
    )

    values = {
        "social_login_provider": "Custom",   # tratamos el doc como Custom para
                                             # fijar explícitamente los endpoints
                                             # (no dependemos del wizard nativo).
        "provider_name": PROVIDER_NAME,
        "custom_base_url": 1,                # => endpoints = base_url + path
        "base_url": issuer,                  # ISSUER del realm
        "icon": "fa fa-key",
        "authorize_url": AUTHORIZE_PATH,
        "access_token_url": TOKEN_PATH,
        "api_endpoint": USERINFO_PATH,
        "redirect_url": REDIRECT_PATH,       # callback nativo login_via_keycloak
        "auth_url_data": auth_url_data,
        "user_id_property": "sub",           # identificador estable OIDC
        "client_id": client_id,
        "client_secret": client_secret,      # campo Password: se cifra al guardar
        "enable_social_login": 1 if enable else 0,
    }

    if frappe.db.exists("Social Login Key", PROVIDER_KEY):
        doc = frappe.get_doc("Social Login Key", PROVIDER_KEY)
        # provider_name y social_login_provider son set_only_once: no reescribir.
        for k, v in values.items():
            if k in ("provider_name", "social_login_provider"):
                continue
            if doc.meta.has_field(k):
                doc.set(k, v)
        accion = "actualizado"
    else:
        doc = frappe.new_doc("Social Login Key")
        for k, v in values.items():
            if doc.meta.has_field(k):
                doc.set(k, v)
        accion = "creado"

    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()

    redirect_uri = frappe.utils.get_url(REDIRECT_PATH)
    print(
        "SSO Keycloak {0}: name='{1}' · enable={2}\n"
        "  issuer      = {3}\n"
        "  authorize   = {3}{4}\n"
        "  token       = {3}{5}\n"
        "  userinfo    = {3}{6}\n"
        "  redirect_uri= {7}".format(
            accion, doc.name, values["enable_social_login"], issuer,
            AUTHORIZE_PATH, TOKEN_PATH, USERINFO_PATH, redirect_uri,
        )
    )
    return doc.name
