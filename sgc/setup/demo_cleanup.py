"""Borra los datos operativos/demo del SGC, dejando intactos los frameworks
normativos, la estructura institucional y el dato que producen otros sistemas.

Auto-descubre los DocTypes operativos: todos los de la app `sgc` MENOS la lista
blanca. Se descubren en vez de listarse para que un DocType nuevo entre solo.

⚠️ La lista blanca creció el 2026-08-19 y conviene entender por qué. Este script
nació con la premisa de que «en producción los operativos están en 0 hasta que
llegan datos reales, así que borrarlos = eliminar exactamente el demo». **Esa
premisa ya no se cumple**, y ejecutarlo tal como estaba habría borrado:

  - los **216 `Valor Indicador`** que el almacén de datos institucional publica
    a diario (dato real de tres productores: dw, lamb y midpoint);
  - los **22 `Proceso` oficiales** (C01-C13, E01-E04, S01-S05), transcritos del
    Requerimiento Técnico §2.2.

Ninguno de los dos es demo, y ninguno de los dos lo dice su nombre. De ahí la
regla: **antes de ampliar lo que este script borra, mirar qué hay en producción**,
no lo que se supone que debería haber.

Ejecutar: bench --site <site> execute sgc.setup.demo_cleanup.run
"""

import frappe

# Se CONSERVAN (frameworks normativos + estructura institucional).
_KEEP = {
    "Marco Normativo", "Elemento Marco", "Escala Valoracion", "Nivel Escala", "Nivel Marco",
    "Indicador", "Ficha Indicador", "Indicador Criterio",
    "Programa", "Programa Sede", "Unidad Organica", "Periodo Academico",
    # Lo publica un productor externo, no este sistema: borrarlo aqui destruiria
    # dato real y el historico no se recupera (el conector solo repone el ultimo).
    "Valor Indicador",
}

# De estos DocTypes se borra SOLO lo marcado como demostracion: conviven registros
# reales y de prueba en la misma tabla, y el nombre es lo unico que los separa.
_SOLO_DEMO = {"Proceso"}


def _es_demo(dt, name):
    if dt not in _SOLO_DEMO:
        return True
    return "DEMO" in (name or "").upper()


def run():
    mods = frappe.get_all("Module Def", {"app_name": "sgc"}, pluck="name")
    dts = frappe.get_all("DocType", {"module": ["in", mods], "istable": 0}, pluck="name")
    operativos = [d for d in dts if d not in _KEEP]

    total = 0
    # Varias pasadas para respetar dependencias por Link.
    for _ in range(5):
        remaining = 0
        for dt in operativos:
            if not frappe.db.table_exists(dt):
                continue
            for name in frappe.get_all(dt, pluck="name"):
                if not _es_demo(dt, name):
                    continue
                try:
                    frappe.delete_doc(dt, name, force=1, ignore_permissions=True, delete_permanently=True)
                    total += 1
                except Exception:
                    remaining += 1
        frappe.db.commit()
        if remaining == 0:
            break

    print("DEMO_CLEANUP: %d registros operativos eliminados en %d DocTypes. "
          "Frameworks normativos, estructura, indicadores publicados y procesos "
          "oficiales intactos." % (total, len(operativos)))
