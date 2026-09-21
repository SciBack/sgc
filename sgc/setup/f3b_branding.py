"""F3b branding — identidad visual del despliegue.

El canónico **no lleva la identidad de ninguna institución**. Hasta el 20-sep-2026
este fichero fijaba el nombre, el logotipo y el copyright de una universidad
concreta, en un repositorio que es común a todos los despliegues: cualquier
institución nueva arrancaba con la identidad de otra hasta que alguien editaba
el código.

Ahora los valores se leen de `site_config.json`, que es donde Frappe guarda la
configuración propia de cada site y que nunca entra al repositorio. Sin
configuración se aplican los valores neutros del producto.

Claves reconocidas en `site_config.json` (todas opcionales):

    {
      "sgc_app_name":   "SGC UPeU",
      "sgc_logo":       "/files/membrete-institucional.png",
      "sgc_favicon":    "/files/favicon.ico",
      "sgc_copyright":  "Nombre de la institución — Oficina de Calidad"
    }

Fijarlas sin editar ficheros:

    bench --site <site> set-config sgc_app_name "SGC <institución>"
    bench --site <site> set-config sgc_logo "/files/<logo-subido>.png"

El logotipo y el favicon son rutas a ficheros ya subidos al site (Archivos del
Desk). Este script NO sube imágenes: si la ruta no existe, Frappe simplemente
no muestra nada, y eso es preferible a fallar el despliegue por una imagen.

`disable_signup` se fija siempre a 1 y no es configurable: un sistema de gestión
de la calidad no admite auto-registro de usuarios, sea cual sea la institución.
Eso es política del producto, no identidad.

Ejecutar (lo hace también `f_deploy_run_all` en cada migrate):
    bench --site <site> execute sgc.setup.f3b_branding.run
"""
import frappe

# Valores del producto cuando el despliegue no declara los suyos. Neutros a
# propósito: es preferible un sistema sin logotipo a uno con el logotipo de
# otra institución.
NEUTRO_APP_NAME = "SGC"
NEUTRO_COPYRIGHT = ""


def _config():
    """Lee la identidad declarada en site_config.json.

    Devuelve siempre las cuatro claves; las no declaradas vienen como None
    (logo/favicon) o con el valor neutro del producto (nombre/copyright).
    """
    conf = frappe.conf or {}
    return {
        "app_name": (conf.get("sgc_app_name") or NEUTRO_APP_NAME).strip(),
        "logo": (conf.get("sgc_logo") or "").strip() or None,
        "favicon": (conf.get("sgc_favicon") or "").strip() or None,
        "copyright": (conf.get("sgc_copyright") or NEUTRO_COPYRIGHT).strip(),
        # Quinta clave, para los documentos impresos (#73). NO es `app_name`: ahí
        # va cómo se llama el sistema («SGC UPeU»), aquí cómo se llama la
        # institución («UNIVERSIDAD PERUANA UNIÓN»), que es lo que encabeza un
        # documento oficial. Sin declarar, los PDF salen sin nombre — nunca con
        # el de otra universidad.
        "institucion": (conf.get("sgc_institucion") or "").strip(),
    }


def _brand_html(app_name, logo):
    """Marca del navbar: logotipo + nombre, o solo el nombre si no hay logotipo.

    Se escapa el nombre porque acaba dentro de HTML y viene de configuración de
    despliegue: una comilla mal puesta en `sgc_app_name` no debe romper la
    cabecera de todo el sistema.
    """
    nombre = frappe.utils.escape_html(app_name)
    if not logo:
        return nombre
    return '<img src="{0}" style="height:24px;margin-right:6px"> {1}'.format(
        frappe.utils.escape_html(logo), nombre
    )


def _set(doc, **kw):
    """Asigna solo los campos que el doctype tiene de verdad.

    Website Settings y Navbar Settings cambian de campos entre versiones de
    Frappe; asignar a ciegas rompería el despliegue en la siguiente.
    """
    for k, v in kw.items():
        if doc.meta.has_field(k):
            doc.set(k, v)


def run():
    frappe.flags.in_patch = True
    cfg = _config()

    ws = frappe.get_doc("Website Settings")
    _set(
        ws,
        app_name=cfg["app_name"],
        app_logo=cfg["logo"],
        banner_image=cfg["logo"],
        favicon=cfg["favicon"],
        brand_html=_brand_html(cfg["app_name"], cfg["logo"]),
        copyright=cfg["copyright"],
        # Política del producto, no de la institución: sin auto-registro.
        disable_signup=1,
    )
    ws.flags.ignore_permissions = True
    ws.save()

    # Navbar Settings no existe en todas las versiones; su ausencia no debe
    # tumbar el despliegue.
    try:
        ns = frappe.get_doc("Navbar Settings")
        _set(ns, app_logo=cfg["logo"], logo_width=120)
        ns.flags.ignore_permissions = True
        ns.save()
    except Exception as e:
        print("navbar skip:", str(e)[:80])

    frappe.db.commit()

    declarado = "site_config" if (frappe.conf or {}).get("sgc_app_name") else "neutro (sin declarar)"
    print(
        "branding OK — app_name={0}, logo={1}, origen={2}".format(
            cfg["app_name"], cfg["logo"] or "(ninguno)", declarado
        )
    )


# ===========================================================================
# Identidad en los documentos impresos (#73)
# ===========================================================================

def resolver_identidad(html):
    """Sustituye los marcadores `%%SGC_*%%` de un Print Format por la identidad
    declarada en `site_config`.

    Por qué marcadores propios y no Jinja: el HTML de los Print Format YA es una
    plantilla Jinja de Frappe (`{{ doc.name }}`), que se resuelve al imprimir. Si
    la identidad fuera también Jinja habría que distinguir dos momentos de render
    en la misma cadena; y con `str.format` las llaves de Jinja reventarían. Un
    marcador que no colisiona con nada se sustituye en Python y se acabó.

    Se hornea al crear el formato, no en cada render: es el mismo trato que
    `f3b_branding` da al Desk, y `f19`/`f6` corren en cada `migrate`, así que un
    despliegue refresca la identidad. Cambiar `site_config` sin migrar deja el PDF
    con la identidad anterior hasta el siguiente despliegue.

    Los marcadores:
        %%SGC_LOGO_IMG%%          -> <img> del logo, o NADA si no hay logo
        %%SGC_INSTITUCION%%       -> nombre de la institución, o vacío
        %%SGC_PIE_INSTITUCION%%   -> " <nombre> ·" para el pie, o vacío (sin
                                     separador suelto)
    """
    cfg = _config()
    institucion = frappe.utils.escape_html(cfg["institucion"]) if cfg["institucion"] else ""
    logo = cfg["logo"]

    reemplazos = {
        "%%SGC_LOGO_IMG%%": f'<img src="{frappe.utils.escape_html(logo)}" alt="">' if logo else "",
        "%%SGC_INSTITUCION%%": institucion,
        "%%SGC_PIE_INSTITUCION%%": f" {institucion} ·" if institucion else "",
    }

    for marcador, valor in reemplazos.items():
        html = html.replace(marcador, valor)

    return html


def nombre_institucion():
    """El nombre de la institución para los documentos, o cadena vacía.

    Cadena de resolución, de lo más explícito a lo más general:
    `site_config.sgc_institucion` -> default `company` -> `System Settings.app_name`.
    Si nada está declarado devuelve **vacío**, nunca el nombre de una universidad
    concreta: hasta #73 estos sitios caían a un literal «Universidad Peruana Unión»
    que se colaba en el PDF de cualquier instalación.
    """
    return (
        (frappe.conf or {}).get("sgc_institucion")
        or frappe.db.get_default("company")
        or frappe.db.get_single_value("System Settings", "app_name")
        or ""
    )
