"""Verificación de instancia — ¿esta instalación sirve para lo que la instalaron?

Una instancia a medias no se distingue a simple vista de una completa: el sitio
responde, la gente entra, las pantallas se ven. Lo que falta aparece cuando
alguien lo necesita, y para entonces ya está en uso.

Este paquete es el marco de esa comprobación. Hoy trae los chequeos de acceso
(#58) y el del scheduler (#42); los de configuración —SSO, correo, estructura,
marcos— son #50 y entran aquí sin rediseñar nada: se registran en `CHEQUEOS` y ya.

Tres niveles, y la diferencia entre ellos es qué se puede hacer con la instancia:

- `BLOQUEANTE` — no se puede usar. Ej.: ninguna cuenta puede entrar al Desk.
- `AVISO`      — se puede usar, pero alguien concreto no puede trabajar.
- `INFO`       — conviene mirarlo; nada se rompe.

Ejecutar:
    bench --site calidad.upeu.edu.pe execute sgc.verificacion.run
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


def _chequeos():
    """Los chequeos registrados. Import diferido: cada módulo toca la base."""
    from sgc.verificacion import accesos, scheduler

    return [
        *accesos.CHEQUEOS,
        *scheduler.CHEQUEOS,
    ]


def verificar():
    """Corre todos los chequeos y devuelve los hallazgos, peor primero.

    No lanza excepciones por un chequeo roto: un fallo al comprobar no debe
    impedir que se vea el resto del informe, así que se reporta como hallazgo.
    """
    hallazgos = []

    for chequeo in _chequeos():
        try:
            hallazgos.extend(chequeo() or [])
        except Exception as e:
            hallazgos.append(
                Hallazgo(
                    AVISO,
                    "chequeo-fallido",
                    f"El chequeo `{getattr(chequeo, '__name__', chequeo)}` falló: {e}",
                    remedio="Es un fallo de la verificación, no necesariamente de la instancia.",
                )
            )

    return sorted(hallazgos, key=lambda h: (_ORDEN.get(h.nivel, 9), h.codigo))


def run():
    """Imprime el informe de verificación. Devuelve los hallazgos en crudo."""
    hallazgos = verificar()

    print("=" * 60)
    print("VERIFICACIÓN DE INSTANCIA")
    print("=" * 60)

    if not hallazgos:
        print("Sin hallazgos: pasan las comprobaciones de acceso y del scheduler.")
        return []

    for h in hallazgos:
        print(f"\n[{h.nivel}] {h.codigo} — {h.resumen}")
        for linea in h.detalle:
            print(f"    · {linea}")
        if h.remedio:
            print(f"    → {h.remedio}")

    bloqueantes = [h for h in hallazgos if h.nivel == BLOQUEANTE]
    print("\n" + "-" * 60)
    print(f"{len(hallazgos)} hallazgo(s); {len(bloqueantes)} bloqueante(s).")

    return [h.as_dict() for h in hallazgos]
