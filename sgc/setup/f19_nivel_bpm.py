"""F19 — Poblado idempotente de `nivel_bpm` en los Proceso existentes.

El campo `nivel_bpm` (Macroproceso N0 / Proceso N1 / Subproceso N2) se deriva del
árbol en `Proceso.validate` (ver doctype/proceso/proceso.py). Eso cubre los altas
y ediciones futuras, pero un sitio ya instalado tiene registros que nunca pasarán
por `validate` salvo que alguien los abra y guarde. Este paso los recorre todos y
fija el nivel, para que la list view y los filtros funcionen desde el primer
`bench migrate` sin editar nada a mano.

Idempotente: recalcula el valor canónico y solo escribe si cambió. `nivel_bpm` es
un campo derivado read_only, así que pisarlo siempre es correcto (no hay entrada
manual que respetar). Se escribe con `update_modified=False` para no ensuciar la
marca de tiempo de registros que no cambiaron de contenido.

La derivación lee `parent_proceso` de la base (no lft/rgt), así que el orden de
recorrido es indiferente.

Ejecutar (idempotente):
    bench --site <site> execute sgc.setup.f19_nivel_bpm.run
"""
import frappe

from sgc.sgc_procesos.doctype.proceso.proceso import derivar_nivel_bpm


def run():
    procesos = frappe.get_all("Proceso", fields=["name", "parent_proceso", "is_group", "nivel_bpm"])

    cambios = []
    for p in procesos:
        es_grupo = bool(int(p.is_group or 0))
        nivel = derivar_nivel_bpm(p.parent_proceso, es_grupo)
        if p.nivel_bpm != nivel:
            frappe.db.set_value("Proceso", p.name, "nivel_bpm", nivel, update_modified=False)
            cambios.append((p.name, p.nivel_bpm or "—", nivel))

    frappe.db.commit()

    print("F19 nivel_bpm: %d proceso(s), %d actualizado(s)" % (len(procesos), len(cambios)))
    for name, antes, ahora in cambios:
        print("   %-10s %s -> %s" % (name, antes, ahora))

    return {"total": len(procesos), "cambios": cambios}
