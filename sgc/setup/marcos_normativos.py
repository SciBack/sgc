"""Marcos normativos declarados por la instancia — el perfil de país (#47).

Hasta #47 el arranque común cargaba en TODA instancia nueva el marco de acreditación de un país
concreto (CONEAU Programas 2025, de SINEACE). Para una institución peruana que acredita con él
era lo que quería; para cualquier otra, contenido ajeno cargado sin preguntar.

Ahora la instancia DECLARA qué marcos quiere, en su `site_config.json`, y este paso los carga en
cada `migrate`:

    bench --site <sitio> set-config --parse sgc_marcos '["coneau-programas-2025"]'
    bench --site <sitio> migrate

Cada entrada es el nombre de un marco de `sgc/setup/marcos/` (sin `.yaml`) o la ruta absoluta a
un YAML propio. Añadir un marco es añadir su YAML y declararlo: no se toca el arranque.

Sin declaración no se carga nada, y lo dice: una instancia con los DocTypes de marco vacíos es un
estado válido y honesto. **Nunca borra ni modifica lo ya cargado**: dejar de declarar un marco
no lo quita de una instancia que ya lo tenía, con sus valoraciones e indicadores colgando de él.

Cargar uno suelto, sin declararlo:

    bench --site <sitio> execute sgc.setup.marcos_normativos.cargar --kwargs "{'marco': 'coneau-programas-2025'}"
"""

import os

import frappe

from sgc.setup import f2_load_coneau

CLAVE = "sgc_marcos"
DIRECTORIO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "marcos")


class PerfilInvalido(Exception):
    pass


def disponibles():
    """Los marcos que trae el producto, por nombre."""
    if not os.path.isdir(DIRECTORIO):
        return []
    return sorted(f[: -len(".yaml")] for f in os.listdir(DIRECTORIO) if f.endswith(".yaml"))


def resolver(marco):
    """La ruta del YAML de un marco declarado por nombre o por ruta. Lanza PerfilInvalido si no existe."""
    marco = str(marco or "").strip()
    if not marco:
        raise PerfilInvalido("hay una entrada vacía")
    if os.path.isabs(marco) or marco.endswith((".yaml", ".yml")):
        if not os.path.isfile(marco):
            raise PerfilInvalido(f"no existe el fichero «{marco}»")
        return marco
    ruta = os.path.join(DIRECTORIO, f"{marco}.yaml")
    if not os.path.isfile(ruta):
        raise PerfilInvalido(
            f"no existe el marco «{marco}». Disponibles: {', '.join(disponibles()) or '(ninguno)'}; "
            "o declarar la ruta absoluta a un YAML propio"
        )
    return ruta


def declarados(conf):
    """Las rutas de los marcos declarados en `conf` (un site_config), en orden. [] si no hay.

    Valida TODO antes de devolver nada: un perfil con una entrada mala no carga ninguna, para no
    dejar una instancia con la mitad de su perfil y sin decirlo.
    """
    valor = conf.get(CLAVE)
    if valor in (None, "", []):
        return []
    if isinstance(valor, str):
        valor = [valor]
    if not isinstance(valor, list):
        raise PerfilInvalido(f"{CLAVE} debe ser una lista de nombres o rutas (es {type(valor).__name__})")
    rutas = []
    for marco in valor:
        ruta = resolver(marco)
        if ruta not in rutas:
            rutas.append(ruta)
    return rutas


def cargar(marco, commit=True):
    """Carga un marco por nombre o ruta, esté declarado o no. Idempotente."""
    return f2_load_coneau.run(resolver(marco), commit=commit)


def run():
    """Paso del orquestador: carga los marcos que declara site_config, o dice que no hay ninguno."""
    try:
        rutas = declarados(frappe.conf)
    except PerfilInvalido as e:
        print(f"Marcos: perfil inválido en site_config ({CLAVE}) — {e}. No se carga ninguno.")
        return "invalido"
    if not rutas:
        print(f"Marcos: ninguno declarado ({CLAVE} en site_config). No se carga ninguno; "
              "lo ya cargado se queda como está.")
        return "sin-declarar"
    for ruta in rutas:
        f2_load_coneau.run(ruta)
    return "cargados"
