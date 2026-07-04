"""F2 E2E — prueba end-to-end del flujo de autoevaluación Enfermería:
estructura mínima -> autoevaluación -> valoraciones -> motor NL/L/LP -> CAPA.
Ejecutar: echo 'from sgc.setup import f2_e2e_test; f2_e2e_test.run()' | bench --site sgc.localhost console
"""
import frappe
from sgc import scoring, capa


def _ensure(doctype, filters, doc):
    name = frappe.db.get_value(doctype, filters)
    if name:
        return name
    d = frappe.get_doc({"doctype": doctype, **doc})
    d.flags.ignore_permissions = True
    d.insert()
    return d.name


def _name(x):
    return x.name if hasattr(x, "name") else x


def run():
    frappe.flags.in_patch = True
    # --- estructura mínima Enfermería-Lima ---
    sede = _ensure("Unidad Organica", {"codigo": "SEDE-LIMA"},
                   {"codigo": "SEDE-LIMA", "nombre": "Sede Lima", "tipo": "Sede", "is_group": 1})
    prog = _ensure("Programa", {"codigo": "ENF"}, {"codigo": "ENF", "nombre": "Enfermeria"})
    ps = _ensure("Programa Sede", {"codigo": "ENF-LIMA"},
                 {"codigo": "ENF-LIMA", "programa": prog, "sede": sede})
    per = _ensure("Periodo Academico", {"codigo": "2026-I"}, {"codigo": "2026-I"})
    ae = _ensure("Autoevaluacion", {"codigo": "AE-ENF-LIMA-2026I"},
                 {"codigo": "AE-ENF-LIMA-2026I", "marco_normativo": "CONEAU-Programas-2025",
                  "programa_sede": ps, "periodo_academico": per})

    def criterios(est):
        return frappe.get_all("Elemento Marco",
                              {"parent_elemento_marco": est, "es_valorable": 1}, pluck="name")

    def valorar(est, overrides):
        crs = criterios(est)
        for i, cr in enumerate(crs):
            if frappe.db.exists("Valoracion Criterio", {"autoevaluacion": ae, "criterio": cr}):
                continue
            vc = frappe.get_doc({"doctype": "Valoracion Criterio", "autoevaluacion": ae,
                                 "criterio": cr, "cumple": overrides.get(i, "Cumple")})
            vc.flags.ignore_permissions = True
            vc.insert()  # on_update dispara el motor
        return crs

    valorar("CONEAU-E1", {})                 # todos Cumple -> LP
    e2 = valorar("CONEAU-E2", {0: "No cumple"})       # un No cumple -> NL
    valorar("CONEAU-E3", {0: "Cumple parcial"})       # un Cumple parcial -> L

    scoring.recalcular_autoevaluacion(ae)
    frappe.db.commit()

    def np(est):
        return frappe.db.get_value("Valoracion Estandar",
                                   {"autoevaluacion": ae, "elemento_marco": est}, "nivel_propuesto")

    print("=== RESULTADOS MOTOR NL/L/LP ===")
    print(f"  E1 (todos Cumple)      -> {np('CONEAU-E1')}  (esperado LP)")
    print(f"  E2 (un No cumple)      -> {np('CONEAU-E2')}  (esperado NL)")
    print(f"  E3 (un Cumple parcial) -> {np('CONEAU-E3')}  (esperado L)")
    print(f"  vigencia_propuesta     -> {frappe.db.get_value('Autoevaluacion', ae, 'vigencia_propuesta')}")
    print(f"  avance_pct             -> {frappe.db.get_value('Autoevaluacion', ae, 'avance_pct')}")

    print("=== FLUJO CAPA (criterio No cumple de E2) ===")
    vc_nc = frappe.db.get_value("Valoracion Criterio", {"autoevaluacion": ae, "criterio": e2[0]}, "name")
    h = _name(capa.generar_hallazgo(vc_nc))
    nc = _name(capa.escalar_a_no_conformidad(h))
    pl = _name(capa.crear_plan(nc))
    print(f"  Hallazgo={h} -> No Conformidad={nc} -> Plan Mejora={pl}")
    frappe.db.commit()
    print("E2E DONE")
