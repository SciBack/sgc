# F3B · Inicio de sesión institucional (OIDC) del SGC

Cómo se habilita el botón «Iniciar sesión con …» contra el proveedor de identidad de una
institución. **No hay nada que editar en el código**: se declara en el `site_config.json` del
sitio y lo aplica el paso `f3b_sso` en cada `bench migrate` (#46). Los valores de cada
institución viven en su capa (para el cliente alfa, en su repositorio de operación).

> **El login real se prueba en el host público.** Hace falta (a) un host con HTTPS que exponga el
> callback de Frappe y (b) un cliente registrado en el proveedor con ese redirect URI. En un lab
> local se comprueba la configuración, no el inicio de sesión de punta a punta.

## 1. Claves de `site_config.json`

| Clave | Obligatoria | Qué es |
|---|---|---|
| `sgc_sso_issuer` | sí | Issuer OIDC, `https://…` (en Keycloak: `https://<host-idp>/realms/<realm>`). **Sin ella el paso no hace nada y lo dice.** |
| `sgc_sso_client_id` | sí | Client ID registrado en el proveedor. |
| `sgc_sso_client_secret` | para crear | Client secret. Si el registro ya existe con un secreto, puede omitirse y se conserva. **Nunca se imprime.** |
| `sgc_sso_proveedor` | no | Name del `Social Login Key`. Por defecto `keycloak` (callback nativo de Frappe). Otro valor usa el callback genérico `custom/<proveedor>`. Solo minúsculas, cifras y `_`. |
| `sgc_sso_etiqueta` | no | Texto del botón. Por defecto «Cuenta institucional». |
| `sgc_sso_rutas` | no | `{"autorizacion", "token", "usuario"}` relativas al issuer. Por defecto las de un realm de Keycloak (`/protocol/openid-connect/{auth,token,userinfo}`). |
| `sgc_sso_habilitado` | no | `1` por defecto; `0` deja el registro creado pero sin botón. |

```bash
bench --site <sitio> set-config sgc_sso_issuer "https://<host-idp>/realms/<realm>"
bench --site <sitio> set-config sgc_sso_client_id "<client-id>"
bench --site <sitio> set-config sgc_sso_client_secret "<client-secret>"
bench --site <sitio> set-config sgc_sso_etiqueta "<texto del botón>"
bench --site <sitio> migrate
```

El `migrate` imprime `SSO creado|actualizado|sin cambios`, el registro, el issuer y el
`redirect_uri` exacto. Sin `sgc_sso_issuer` imprime `SSO: no configurado` y no toca nada.

## 2. Lo que hace el paso (verificado contra Frappe v16)

Leído de `frappe/integrations/oauth2_logins.py` y `frappe/utils/oauth.py`:

| Elemento | Valor |
|---|---|
| Callback | Nativo `login_via_keycloak` si el proveedor es `keycloak` (busca el registro con name `keycloak`); si no, el genérico `…oauth2_logins.custom/<proveedor>` |
| `name` del registro | `sgc_sso_proveedor` (autoname = `frappe.scrub(provider_name)`: se crea con el proveedor y después se escribe la etiqueta, porque `provider_name` es el texto del botón y es set_only_once) |
| URLs | `custom_base_url=1`: Frappe compone `base_url + ruta`, así que `base_url` es el issuer y las rutas van relativas |
| Redirect URI | `frappe.utils.get_url()` + la ruta del callback: el host sale del sitio (`host_name` si está detrás de proxy) |
| Scope | `openid email profile`, Authorization Code Flow |
| Identidad | `user_id_property = sub`; el usuario se busca **por correo** (`email`, `upn` o `unique_name`) |

**Idempotente:** volver a migrar con la misma configuración no cambia nada («sin cambios»).
**Cambio de proveedor:** si cambia `sgc_sso_proveedor`, el registro que el paso gestionaba antes
se elimina; uno creado a mano, que el paso no gestiona, nunca se toca.

## 3. Lo que le toca al administrador del proveedor de identidad

No lo hace el SGC:

1. Registrar el cliente: OIDC, **confidential** (con client secret), Authorization Code Flow;
   sin direct access grants.
2. **Valid redirect URI**: el `redirect_uri` que imprime el `migrate`. En Keycloak:
   `https://<host-sgc>/api/method/frappe.integrations.oauth2_logins.login_via_keycloak`.
3. **Web origins**: `https://<host-sgc>`.
4. Que el userinfo entregue `sub`, `email`, `given_name` y `family_name` (en Keycloak, los
   client scopes `email` y `profile` como *Default*).
5. Entregar `client_id` y `client_secret` al despliegue por un canal de secretos, nunca al repo.

## 4. La trampa del correo

Frappe enlaza la cuenta **solo por correo**, y el SGC trae el autorregistro desactivado: si el
correo que entrega el proveedor no coincide con el de un usuario del SGC, el botón muestra un
error y no deja entrar (no crea un usuario duplicado). Antes de dar de alta personas, comprobar
qué correo devuelve el proveedor para cada una; si difiere, la cuenta del SGC tiene que llevar
ese correo.

## 5. Comprobar

- `bench --site <sitio> execute sgc.verificacion.run`:
  - `sso-no-configurado` (AVISO) si no hay inicio de sesión institucional;
  - `sso-desalineado` (AVISO) si el registro no coincide con lo declarado;
  - nada si está bien.
- En el host público: el botón con la etiqueta en `/login`, que lleva al proveedor; tras
  autenticar, `User Social Login` del usuario con el proveedor y su `sub`.
- Un `redirect_uri` que no coincida **exactamente** con el registrado en el proveedor produce
  `invalid redirect_uri`.
