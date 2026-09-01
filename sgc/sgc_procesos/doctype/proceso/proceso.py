# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.nestedset import NestedSet

# Jerarquía BPM de 5 niveles del SGC (docs/decisiones/modelado-procesos-bpm.md):
#   N0 Macroproceso · N1 Proceso · N2 Subproceso · N3 Procedimiento · N4 Tarea.
# El DocType Proceso (NestedSet) cubre N0/N1/N2 en el mismo árbol; N3 y N4 son
# otros artefactos (DocType Procedimiento y las cajas de los BPMN).
#
# `nivel_bpm` se DERIVA del árbol y no se edita a mano (read_only). Regla:
#   - profundidad 0 (raíz)  + is_group  -> Macroproceso  (p. ej. S04)
#   - profundidad 0 (raíz)  sin is_group -> Proceso       (los 22: E01..S05)
#   - profundidad 1                      -> Proceso       (p. ej. S04.01..05)
#   - profundidad >= 2                   -> Subproceso
# La profundidad se cuenta caminando `parent_proceso` hacia arriba (no lft/rgt),
# porque en `validate` de un doc nuevo el NestedSet aún no ha calculado lft/rgt
# (frappe/utils/nestedset.py: se fijan en after_insert/on_update).


def derivar_nivel_bpm(parent_proceso, is_group):
    """Devuelve el nivel BPM (Macroproceso/Proceso/Subproceso) según el árbol.

    Idempotente y sin efectos secundarios: solo lee `parent_proceso` hacia arriba.
    """
    profundidad = 0
    padre = parent_proceso
    vistos = set()
    while padre:
        if padre in vistos:  # ciclo defensivo: no colgarse
            break
        vistos.add(padre)
        profundidad += 1
        padre = frappe.db.get_value("Proceso", padre, "parent_proceso")

    if profundidad == 0:
        return "Macroproceso" if is_group else "Proceso"
    if profundidad == 1:
        return "Proceso"
    return "Subproceso"


class Proceso(NestedSet):
    def validate(self):
        # `is_group` puede llegar como 1/0/"1"/"0"; normalizar a bool (gotcha v16:
        # db castea, pero el valor del form puede venir como str).
        es_grupo = bool(int(self.is_group or 0))
        self.nivel_bpm = derivar_nivel_bpm(self.parent_proceso, es_grupo)
