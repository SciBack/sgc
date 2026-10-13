"""Verificación de instancia — ¿esta instalación sirve para lo que la instalaron?

Una instancia a medias no se distingue a simple vista de una completa: el sitio
responde, la gente entra, las pantallas se ven. Lo que falta aparece cuando
alguien lo necesita, y para entonces ya está en uso.

Cada módulo de este paquete es un grupo de chequeos con su lista `CHEQUEOS`:
`estructura` y `marcos` (lo que da de alta la institución, #50), `despliegue`
(permisos y workflows, #50), `identidad` (#50), `accesos` (#58), `scheduler`
(#42), `correo` (#41, #50) y `sso` (#46). Uno nuevo se registra en `_GRUPOS`.

Tres niveles, y la diferencia entre ellos es qué se puede hacer con la instancia:

- `BLOQUEANTE` — no se puede usar. Ej.: sin estructura, sin periodo abierto,
  sin permisos aplicados, o ninguna cuenta puede entrar al Desk.
- `AVISO`      — se puede usar, pero incompleta o alguien concreto no puede trabajar.
- `INFO`       — conviene mirarlo; nada se rompe.

Lo que no da hallazgos sale como comprobado. La regla que decide si esto sirve:
la salida es verdadera o no es. Decir «correcto» sobre una instancia a medias es
peor que no comprobar nada; ante la duda, se avisa.

Ejecutar:
    bench --site <sitio> execute sgc.verificacion.run
    bench --site <sitio> execute sgc.verificacion.run --kwargs "{'solo': 'estructura'}"

`solo` acepta un grupo (`estructura`) o un chequeo (`periodo_vigente`), o
varios separados por comas. Con algún BLOQUEANTE el comando termina con código
de salida 1, para poder encadenarlo en un despliegue automatizado.
"""

import frappe

BLOQUEANTE = "BLOQUEANTE"
AVISO = "AVISO"
INFO = "INFO"

# Orden de gravedad, para ordenar la salida. No es alfabético a propósito.
_ORDEN = {BLOQUEANTE: 0, AVISO: 1, INFO: 2}


class Hallazgo:
    """Algo que alguien tiene que mirar.

    `detalle` es una lista de líneas ya legibles: quien lee la salida no debería
    tener que consultar la base para entender qué hacer. Un hallazgo que dice
    «hay 4 cuentas mal» sin nombrarlas obliga a una segunda investigación, y esa
    es justo la fricción que hace que los avisos se ignoren.
    """

    def __init__(self, nivel, codigo, resumen, detalle=None, remedio=None):
        self.nivel = nivel
        self.codigo = codigo
        self.resumen = resumen
        self.detalle = detalle or []
        self.remedio = remedio

    def as_dict(self):
        return {
            "nivel": self.nivel,
            "codigo": self.codigo,
            "resumen": self.resumen,
            "detalle": self.detalle,
            "remedio": self.remedio,
        }


# Orden de ejecución y de presentación de los grupos: primero lo que impide usar
# la instancia, después lo que la deja incompleta.
_GRUPOS = ("estructura", "despliegue", "accesos", "marcos", "identidad", "scheduler", "correo", "sso")


def _chequeos(solo=None):
    """Los chequeos registrados, opcionalmente filtrados por grupo o por nombre.

    Import diferido: cada módulo toca la base. Un nombre en `solo` que no
    corresponde a nada es un error, no un filtro vacío: un «sin hallazgos» de
    cero chequeos sería justo la confianza falsa que esto existe para evitar.
    """
    import importlib

    chequeos = []
    for grupo in _GRUPOS:
        modulo = importlib.import_module(f"sgc.verificacion.{grupo}")
        chequeos.extend((grupo, chequeo) for chequeo in modulo.CHEQUEOS)

    if not solo:
        return [c for _, c in chequeos]

    pedidos = [p.strip() for p in (solo.split(",") if isinstance(solo, str) else solo) if p.strip()]
    conocidos = set(_GRUPOS) | {c.__name__ for _, c in chequeos}
    desconocidos = [p for p in pedidos if p not in conocidos]
    if desconocidos:
        raise ValueError(
            f"No existe el chequeo o grupo {', '.join(desconocidos)}. "
            f"Grupos: {', '.join(_GRUPOS)}. Chequeos: {', '.join(sorted(c.__name__ for _, c in chequeos))}."
        )
    return [c for grupo, c in chequeos if grupo in pedidos or c.__name__ in pedidos]


def _ejecutar(chequeos):
    """Corre los chequeos. Devuelve (hallazgos peor primero, nombres de los que pasaron).

    No lanza excepciones por un chequeo roto: un fallo al comprobar no debe
    impedir que se vea el resto del informe, así que se reporta como hallazgo
    —y ese chequeo NO cuenta como comprobado—.
    """
    hallazgos, limpios = [], []

    for chequeo in chequeos:
        nombre = getattr(chequeo, "__name__", str(chequeo))
        try:
            propios = list(chequeo() or [])
        except Exception as e:
            propios = [
                Hallazgo(
                    AVISO,
                    "chequeo-fallido",
                    f"El chequeo `{nombre}` falló: {e}",
                    remedio="Es un fallo de la verificación, no necesariamente de la instancia.",
                )
            ]
        hallazgos.extend(propios)
        if not propios:
            limpios.append(nombre)

    return sorted(hallazgos, key=lambda h: (_ORDEN.get(h.nivel, 9), h.codigo)), limpios


def verificar(solo=None):
    """Corre los chequeos (todos, o los de `solo`) y devuelve los hallazgos, peor primero."""
    return _ejecutar(_chequeos(solo))[0]


def run(solo=None, salir=True):
    """Imprime el informe de verificación.

    Con `salir` (lo que hace `bench execute`), si hay algún BLOQUEANTE termina
    con código de salida 1 después de imprimir, y no devuelve nada: `bench
    execute` imprimiría lo devuelto como JSON debajo del informe. Desde código,
    `salir=False` devuelve los hallazgos en crudo.
    """
    try:
        chequeos = _chequeos(solo)
    except ValueError as e:
        print(e)
        if salir:
            # SystemExit y no la excepción: `bench execute` reintenta con eval()
            # cualquier Exception y el error real quedaba tapado por un NameError.
            raise SystemExit(2) from None
        raise

    hallazgos, limpios = _ejecutar(chequeos)
    bloqueantes = [h for h in hallazgos if h.nivel == BLOQUEANTE]

    print("=" * 60)
    print("VERIFICACIÓN DE INSTANCIA" + (f" — solo: {solo}" if solo else ""))
    print("=" * 60)

    for h in hallazgos:
        print(f"\n[{h.nivel}] {h.codigo} — {h.resumen}")
        for linea in h.detalle:
            print(f"    · {linea}")
        if h.remedio:
            print(f"    → {h.remedio}")

    if limpios:
        print(("\n" if hallazgos else "") + f"Comprobado sin hallazgos ({len(limpios)} de {len(chequeos)}):")
        for nombre in limpios:
            print(f"    ✓ {nombre}")

    print("\n" + "-" * 60)
    if hallazgos:
        print(f"{len(hallazgos)} hallazgo(s); {len(bloqueantes)} bloqueante(s).")
    else:
        print(f"Sin hallazgos: pasan los {len(chequeos)} chequeos.")

    if salir:
        if bloqueantes:
            raise SystemExit(1)
        return None
    return [h.as_dict() for h in hallazgos]
