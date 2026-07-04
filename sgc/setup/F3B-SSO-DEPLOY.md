# F3B · SSO OIDC del SGC-Frappe contra Keycloak UPeU

Guía de despliegue para habilitar el login OIDC de Frappe contra el Keycloak
corporativo (`realm upeu`, issuer `https://keyid.upeu.edu.pe/realms/upeu`).

> **El login real es de DESPLIEGUE.** Requiere (a) un host público con HTTPS
> que exponga el callback de Frappe y (b) un cliente Keycloak registrado con
> ese redirect URI. En el lab (`sgc.localhost`) **NO se prueba** el login: no
> hay redirect público ni cliente en el realm. Aquí solo se prepara la config.

## Datos verificados contra el código de Frappe v16

Leídos de `apps/frappe/frappe/integrations/oauth2_logins.py` y
`apps/frappe/frappe/utils/oauth.py`:

| Elemento | Valor verificado |
|---|---|
| Proveedor | **Keycloak nativo** (`login_via_keycloak` → `login_via_oauth2("keycloak", ...)`) |
| `name` del Social Login Key | **`keycloak`** (autoname = `frappe.scrub(provider_name)`; por eso `provider_name="Keycloak"`) |
| **Redirect URI (callback)** | `https://<host-frappe>/api/method/frappe.integrations.oauth2_logins.login_via_keycloak` |
| authorize | `{issuer}/protocol/openid-connect/auth` |
| token | `{issuer}/protocol/openid-connect/token` |
| userinfo | `{issuer}/protocol/openid-connect/userinfo` |
| `base_url` del doc | el **issuer** (`.../realms/upeu`) — con `custom_base_url=1`, Frappe compone `base_url + path` |
| scope | `openid email profile` |
| user id social | `sub` (claim OIDC estable) |
| mapeo email | `email` \| `upn` \| `unique_name` |
| mapeo nombre | first: `given_name`; last: `family_name` |

> **Nota sobre el redirect URI exacto:** Frappe construye el redirect absoluto
> como `frappe.utils.get_url()` + la ruta relativa `redirect_url` del doc
> (`utils/oauth.py::get_redirect_uri`). Por tanto el host del redirect es el de
> `site_config`/`host_name` del sitio Frappe. **No** se usa el callback genérico
> `.../oauth2_logins.custom/keycloak` porque Keycloak es proveedor nativo; el
> nativo exige que el `name` del doc sea exactamente `keycloak`.

---

## Responsabilidad del **admin de Keycloak** (realm `upeu`)

Hoy existen los clientes `ciso-assistant` y `mayan-sgc`. Falta crear
`sgc-frappe`. Estos pasos NO los hace el script de Frappe:

1. **Crear cliente** `sgc-frappe` en el realm `upeu`:
   - **Client type:** OpenID Connect
   - **Client authentication:** ON (**confidential** — genera client secret)
   - **Standard flow:** ON (Authorization Code Flow). Direct access grants: OFF.
2. **Valid redirect URIs:**
   `https://<host-frappe>/api/method/frappe.integrations.oauth2_logins.login_via_keycloak`
   (usar el host real del Frappe; se admite un patrón por entorno).
3. **Web origins:** `https://<host-frappe>` (o `+` para derivar de los redirect URIs).
4. **Client scopes / mappers** — asegurar que el userinfo entregue:
   - `sub` (siempre presente), `email`, `email_verified`,
     `given_name`, `family_name`, `preferred_username`.
   - Los client scopes por defecto `email` y `profile` ya cubren esos claims;
     verificar que estén asignados como *Default* al cliente.
5. **(Opcional) mapper de roles** si más adelante se mapean roles Keycloak →
   roles Frappe. En esta fase el alta de usuario la controla Frappe
   (`Portal Settings.default_role` / `sign_ups`).
6. **Entregar al despliegue** el `client_id` (=`sgc-frappe`) y el
   `client_secret` generado. Estos van a `~/.secrets/sgc-sso.env`
   (NUNCA al repo), siguiendo el patrón de los otros clientes.

---

## Responsabilidad del **despliegue Frappe** (orquestador)

### 1. Guardar los secretos (patrón de los otros clientes)

```bash
# ~/.secrets/sgc-sso.env   (chmod 600)
SGC_KEYCLOAK_CLIENT_ID=sgc-frappe
SGC_KEYCLOAK_CLIENT_SECRET=<secret-generado-por-keycloak>
SGC_KEYCLOAK_ISSUER=https://keyid.upeu.edu.pe/realms/upeu
```

### 2. Verificar el `host_name` del sitio (define el redirect URI)

El redirect que Frappe reporta a Keycloak sale de la URL del sitio. Fíjala si
el sitio está detrás de proxy:

```bash
bench --site <site> set-config host_name https://<host-frappe>
```

### 3. Inyectar la config (idempotente)

```bash
source ~/.secrets/sgc-sso.env
bench --site <site> execute sgc.setup.f3b_sso.configurar_keycloak \
  --kwargs "{'client_id': '${SGC_KEYCLOAK_CLIENT_ID}', \
             'client_secret': '${SGC_KEYCLOAK_CLIENT_SECRET}', \
             'issuer': '${SGC_KEYCLOAK_ISSUER}', 'enable': True}"
```

El comando imprime el `name` del Social Login Key, los endpoints resueltos y el
`redirect_uri` exacto. Re-ejecutarlo es seguro (actualiza, no duplica).

> **Alternativa sin ejecutar código** (site_config): los secretos también
> pueden vivir en `site_config.json` bajo la clave `keycloak_login`
> (`{"client_id": "...", "client_secret": "...", "redirect_uri": "..."}`);
> `utils/oauth.py::get_oauth_keys`/`get_redirect_uri` la priorizan sobre el
> DocType. Aun así hace falta el Social Login Key para los endpoints y el
> botón de login, así que el método recomendado es el `bench execute` de arriba.

### 4. Verificar el login (solo en el host público, no en el lab)

1. Ir a `https://<host-frappe>/login` → debe aparecer el botón
   **“Login with Keycloak”**.
2. Click → redirige a `keyid.upeu.edu.pe` (pantalla de Keycloak).
3. Autenticar con un usuario del realm `upeu`.
4. Keycloak redirige al callback `.../login_via_keycloak`; Frappe crea/enlaza
   el usuario por email y abre sesión.
5. Comprobaciones:
   - `bench --site <site> console` →
     `frappe.db.get_value("Social Login Key", "keycloak", ["enable_social_login","base_url","redirect_url"])`
   - Revisar `User Social Login` del usuario logueado: provider `keycloak`,
     userid = `sub`.
   - Ante errores, `bench --site <site> show-config` y los logs
     (`logs/web.error.log`); un `redirect_uri` que no coincida EXACTAMENTE con
     el registrado en Keycloak produce `invalid redirect_uri`.

---

## Checklist rápido

- [ ] (Keycloak) Cliente `sgc-frappe` confidential + standard flow.
- [ ] (Keycloak) Redirect URI `.../login_via_keycloak` con el host real.
- [ ] (Keycloak) Web origins + scopes `email`/`profile` como Default.
- [ ] (Secretos) `~/.secrets/sgc-sso.env` con id/secret/issuer (chmod 600).
- [ ] (Frappe) `host_name` del sitio fijado al host público.
- [ ] (Frappe) `bench execute sgc.setup.f3b_sso.configurar_keycloak ...`.
- [ ] (Frappe) Botón “Login with Keycloak” visible y login end-to-end OK.
- [ ] (Lab) NO se prueba en `sgc.localhost` (sin redirect público).
