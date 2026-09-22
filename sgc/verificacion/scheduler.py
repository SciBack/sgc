"""Chequeo del scheduler: ¿siguen corriendo las tareas programadas? (#42)

La lógica vive en `sgc.latido`, que también consulta el Desk al cargar; aquí
solo se traduce su resultado a hallazgos. Es AVISO y no BLOQUEANTE: con el
scheduler parado la gente sigue pudiendo trabajar, pero los estados que el
sistema pone solo —Vencida, Vencido— dejan de ponerse.
"""

from sgc import latido
from sgc.verificacion import AVISO, Hallazgo


def tareas_programadas_paradas():
    resultado = latido.comprobar()
    if not resultado["alerta"]:
        return []

    detalle = []
    if resultado["scheduler_apagado"]:
        detalle.append("El scheduler está desactivado en System Settings o en site_config.")
    detalle.extend(latido._describir(f) for f in resultado["tareas"] if f["alerta"])

    return [
        Hallazgo(
            AVISO,
            "scheduler-parado",
            "Hay tareas programadas que llevan más de lo debido sin completarse.",
            detalle=detalle,
            remedio=(
                "Mirar el contenedor del scheduler (`docker compose ps`) y el "
                "Scheduled Job Log de cada tarea. `bench doctor` dice si está activo."
            ),
        )
    ]


CHEQUEOS = [tareas_programadas_paradas]
