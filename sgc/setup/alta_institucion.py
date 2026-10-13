"""Alta de una institución en un comando (#49).

Cada pieza ya es parametrizable —identidad (#40, #73), inicio de sesión institucional (#46),
marcos del perfil de país (#47), estructura (#48)— pero poner en marcha una institución seguía
siendo una secuencia de pasos que había que conocer y ejecutar en orden. Esto la convierte en un
comando que toma un perfil y deja la instancia operable:

    bench --site <sitio> execute sgc.setup.alta_institucion.run --kwargs "{'perfil': '/ruta/perfil.yaml'}"

El perfil (ejemplo comentado: `sgc/setup/perfil-institucion.ejemplo.yaml`) declara:

    institucion        nombre (encabeza los documentos), sistema (cómo se llama el SGC),
                       logo, favicon, copyright            -> claves sgc_* de identidad
    identidad_digital  issuer, client_id, proveedor, etiqueta, rutas, habilitado
                       y `client_secret_env`: el NOMBRE de la variable de entorno que trae el
                       secreto. El secreto nunca va en el perfil, que suele versionarse.
    pais               marcos: [nombres de sgc/setup/marcos/ o rutas a YAML]
    estructura         ruta (relativa al perfil) a la carpeta de CSV o al .xlsx de #48

Orden: validación completa → configuración del sitio → arranque común (los pasos del
despliegue, que aplican identidad, SSO y marcos) → estructura → verificación (#50).

- **Nada se escribe si el perfil no es válido**: se valida entero —incluida la estructura y los
  marcos— y se dice qué falta.
- **Un paso que falla detiene el alta** y dice cuál; lo anterior queda hecho, y como todo es
  idempotente, se corrige y se vuelve a lanzar.
- **Reejecutar con el mismo perfil no duplica ni altera nada.** Lo que el perfil no declara no
  se toca: un perfil sin `identidad_digital` no apaga un SSO que ya exista.
- Termina con la verificación de instancia, y con código de salida 1 si queda algún bloqueante.

**Qué NO hace, a propósito:** crear el sitio, pedir certificados, registrar el cliente en el
proveedor de identidad ni configurar el correo. Es infraestructura y depende de terceros: el
alta empieza donde termina el despliegue.
"""

import os

import frappe
import yaml

from sgc.setup import f3b_sso, importador_estructura, marcos_normativos

# Perfil -> claves de site_config, por bloque.
IDENTIDAD = {"nombre": "sgc_institucion", "sistema": "sgc_app_name", "logo": "sgc_logo",
             "favicon": "sgc_favicon", "copyright": "sgc_copyright"}
SSO = {"issuer": "sgc_sso_issuer", "client_id": "sgc_sso_client_id", "proveedor": "sgc_sso_proveedor",
       "etiqueta": "sgc_sso_etiqueta", "rutas": "sgc_sso_rutas", "habilitado": "sgc_sso_habilitado"}
BLOQUES = {"institucion", "identidad_digital", "pais", "estructura"}


class PerfilInvalido(Exception):
    def __init__(self, errores):
        self.errores = errores
        super().__init__("perfil no válido; no se ha escrito nada:\n  " + "\n  ".join(errores))


class PasoFallido(Exception):
    pass


# ---------------------------------------------------------------- perfil


def leer(ruta):
    if not ruta or not os.path.isfile(ruta):
        raise PerfilInvalido([f"no existe el perfil «{ruta}»"])
    with open(ruta, encoding="utf-8") as fh:
        try:
            perfil = yaml.safe_load(fh) or {}
        except yaml.YAMLError as e:
            raise PerfilInvalido([f"el perfil no es YAML válido: {e}"]) from None
    if not isinstance(perfil, dict):
        raise PerfilInvalido(["el perfil debe ser un mapa con los bloques " + ", ".join(sorted(BLOQUES))])
    return perfil


def preparar(perfil, base, entorno=None, conf=None):
    """Valida el perfil y lo traduce a lo que hay que aplicar. Lanza PerfilInvalido con TODO lo que falte.

    Devuelve {"config": {clave: valor}, "secreto": str|None, "estructura": ruta|None}. `base` es la
    carpeta del perfil (las rutas relativas parten de ahí); `entorno` y `conf` son os.environ y el
    site_config actual, inyectables para probarlo sin sitio.
    """
    entorno = os.environ if entorno is None else entorno
    conf = conf or {}
    errores, config = [], {}

    sobran = sorted(set(perfil) - BLOQUES)
    if sobran:
        errores.append(f"bloques desconocidos: {', '.join(sobran)} (válidos: {', '.join(sorted(BLOQUES))})")

    # Identidad: el nombre de la institución es lo mínimo; sin él los documentos salen sin nombre.
    inst = perfil.get("institucion") or {}
    if not isinstance(inst, dict) or not str(inst.get("nombre") or "").strip():
        errores.append("institucion.nombre es obligatorio: encabeza los documentos oficiales")
    else:
        for campo in sorted(set(inst) - set(IDENTIDAD)):
            errores.append(f"institucion.{campo} no existe (válidos: {', '.join(IDENTIDAD)})")
        for campo, clave in IDENTIDAD.items():
            if str(inst.get(campo) or "").strip():
                config[clave] = str(inst[campo]).strip()

    # Inicio de sesión institucional: se valida con el mismo lector que usa el despliegue.
    secreto = None
    sso = perfil.get("identidad_digital")
    if sso:
        if not isinstance(sso, dict):
            errores.append("identidad_digital debe ser un mapa")
        else:
            for campo in sorted(set(sso) - set(SSO) - {"client_secret_env"}):
                errores.append(f"identidad_digital.{campo} no existe (válidos: {', '.join(SSO)}, client_secret_env)")
            if "client_secret" in sso:
                errores.append("identidad_digital.client_secret no va en el perfil: declarar client_secret_env "
                               "con el nombre de la variable de entorno que lo trae")
            claves = {SSO[c]: v for c, v in sso.items() if c in SSO}
            variable = sso.get("client_secret_env")
            if variable:
                secreto = entorno.get(variable) or None
                if not secreto:
                    errores.append(f"identidad_digital: la variable de entorno {variable} no está definida o está vacía")
            try:
                cfg = f3b_sso.leer({**claves, "sgc_sso_client_secret": secreto})
            except f3b_sso.ConfiguracionInvalida as e:
                errores.append(f"identidad_digital: {e}")
            else:
                if cfg and not secreto and not conf.get("sgc_sso_client_secret") and \
                        not frappe.db.exists("Social Login Key", cfg["proveedor"]):
                    errores.append("identidad_digital: hace falta el secreto para crear el registro "
                                   "(client_secret_env) y no hay uno guardado")
                config.update(claves)

    # Perfil de país: los marcos tienen que existir.
    pais = perfil.get("pais") or {}
    if pais:
        marcos = pais.get("marcos") if isinstance(pais, dict) else None
        if marcos is None:
            errores.append("pais.marcos es obligatorio en el bloque pais (lista de marcos)")
        else:
            absolutos = [m if os.path.isabs(str(m)) or not str(m).endswith((".yaml", ".yml"))
                         else os.path.normpath(os.path.join(base, str(m))) for m in (marcos or [])]
            try:
                marcos_normativos.declarados({marcos_normativos.CLAVE: absolutos})
            except marcos_normativos.PerfilInvalido as e:
                errores.append(f"pais.marcos: {e}")
            else:
                config[marcos_normativos.CLAVE] = absolutos

    # Estructura: se valida entera contra el sitio, igual que la validaría el importador.
    estructura = None
    if perfil.get("estructura"):
        estructura = os.path.normpath(os.path.join(base, str(perfil["estructura"])))
        try:
            hojas = importador_estructura.leer(estructura)
            if not hojas:
                errores.append(f"estructura: «{estructura}» no trae ninguna hoja")
            else:
                errores.extend(f"estructura: {e}" for e in
                               importador_estructura.validar(hojas, importador_estructura.describir_sitio()))
        except importador_estructura.EstructuraInvalida as e:
            errores.extend(f"estructura: {x}" for x in e.errores)

    if errores:
        raise PerfilInvalido(errores)
    return {"config": config, "secreto": secreto, "estructura": estructura}


# ---------------------------------------------------------------- aplicación


def _configurar_sitio(config, secreto):
    """Escribe en site_config solo lo que el perfil declara y lo que cambia. Devuelve las claves escritas."""
    from frappe.installer import update_site_config

    cambios = {k: v for k, v in config.items() if frappe.conf.get(k) != v}
    if secreto and frappe.conf.get("sgc_sso_client_secret") != secreto:
        cambios["sgc_sso_client_secret"] = secreto
    for clave, valor in cambios.items():
        update_site_config(clave, valor)
        frappe.local.conf[clave] = valor  # el proceso sigue con la configuración nueva
    return sorted(cambios)


def _arranque_comun():
    """Los pasos del despliegue, en su orden, deteniéndose en el primero que falle."""
    from sgc.setup.f_deploy_run_all import STEPS, _correr_paso

    for nombre, modulo in STEPS:
        try:
            _correr_paso(nombre, modulo)
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(title=f"alta_institucion: fallo en {nombre}")
            raise PasoFallido(f"arranque común, paso {nombre}: {e}") from e
    frappe.flags.in_patch = False
    frappe.clear_cache()


def alta(ruta_perfil):
    """Da de alta la institución del perfil. Devuelve la lista de hallazgos de la verificación.

    Lanza PerfilInvalido antes de escribir nada, o PasoFallido diciendo en qué paso se detuvo.
    """
    from sgc import verificacion

    ruta_perfil = os.path.abspath(ruta_perfil)
    plan = preparar(leer(ruta_perfil), os.path.dirname(ruta_perfil), conf=frappe.conf)

    pasos = [
        ("configuración del sitio", lambda: print(
            "  claves escritas: " + (", ".join(_configurar_sitio(plan["config"], plan["secreto"])) or "ninguna (sin cambios)"))),
        ("arranque común", _arranque_comun),
    ]
    if plan["estructura"]:
        def _estructura():
            resultado = importador_estructura.importar(plan["estructura"], aplicar=True)
            frappe.db.commit()
            for hoja, c in resultado.items():
                print(f"  {hoja}: {c['creados']} creados · {c['actualizados']} actualizados · {c['sin cambios']} sin cambios")
        pasos.append(("estructura", _estructura))

    for n, (nombre, paso) in enumerate(pasos, start=1):
        print(f"\n[{n}/{len(pasos) + 1}] {nombre}")
        try:
            paso()
        except PasoFallido:
            raise
        except Exception as e:
            frappe.db.rollback()
            raise PasoFallido(f"{nombre}: {e}") from e

    print(f"\n[{len(pasos) + 1}/{len(pasos) + 1}] verificación de instancia")
    return verificacion.run(salir=False)


def run(perfil=None):
    """Comando: alta de la institución descrita en `perfil`."""
    if not perfil:
        print("Falta `perfil`. Ejemplo comentado en sgc/setup/perfil-institucion.ejemplo.yaml")
        raise SystemExit(2)
    print("=" * 60)
    print(f"ALTA DE INSTITUCIÓN — {perfil}")
    print("=" * 60)
    try:
        hallazgos = alta(perfil)
    except PerfilInvalido as e:
        print(f"Alta NO iniciada — {e}")
        raise SystemExit(1) from None
    except PasoFallido as e:
        print(f"\nAlta DETENIDA en {e}\n  Lo anterior quedó aplicado; corregir y volver a lanzar (es idempotente).")
        raise SystemExit(1) from None
    from sgc.verificacion import BLOQUEANTE

    if any(h["nivel"] == BLOQUEANTE for h in hallazgos):
        print("\nAlta terminada, pero la instancia TIENE BLOQUEANTES: ver la verificación de arriba.")
        raise SystemExit(1)
    print("\nAlta terminada: sin bloqueantes.")

