"""Datos de PRUEBA para ejercitar todos los flujos del SGC (borrables).

Añade evidencias vinculadas a criterios, acciones de mejora en el plan,
hallazgos extra y valores de indicadores sobre la autoevaluación más reciente.
Todo marcado con "[DEMO]" y códigos *-DEMO-* para poder borrarlo.

Ejecutar:  bench --site calidad.upeu.edu.pe execute sgc.setup.demo_seed.run
Borrar:    bench --site calidad.upeu.edu.pe execute sgc.setup.demo_cleanup.run
"""

import frappe


def _ins(doc):
    d = frappe.get_doc(doc)
    d.flags.ignore_permissions = True
    d.insert()
    return d.name


def run():
    aes = frappe.get_all("Autoevaluacion", order_by="modified desc", limit_page_length=1, pluck="name")
    if not aes:
        print("demo_seed: no hay autoevaluación; corre primero f2_e2e_test.")
        return
    ae = aes[0]
    meta = frappe.db.get_value("Autoevaluacion", ae, ["programa_sede", "periodo_academico"], as_dict=1) or {}
    ps, per = meta.get("programa_sede"), meta.get("periodo_academico")

    # 1) Evidencias vinculadas a criterios reales (origen_doctype=Elemento Marco)
    crits = frappe.get_all("Valoracion Criterio", {"autoevaluacion": ae}, ["criterio"],
                           order_by="criterio", limit_page_length=8)
    tipos = ["Documento", "Acta", "Registro", "Documento", "Acta", "Registro"]
    titulos = ["Plan de estudios vigente", "Acta del comité de calidad",
               "Registro de encuestas de satisfacción", "Sílabos por competencias",
               "Informe de seguimiento a egresados", "Convenio de prácticas preprofesionales"]
    n_ev = 0
    for i, c in enumerate(crits[:6]):
        cod = "EVID-DEMO-%02d" % (i + 1)
        if frappe.db.exists("Evidencia", cod):
            continue
        _ins({"doctype": "Evidencia", "codigo": cod, "titulo": titulos[i],
              "descripcion": "[DEMO] Evidencia de prueba", "tipo": tipos[i],
              "origen_doctype": "Elemento Marco", "origen_id": c.criterio,
              "programa_sede": ps, "periodo_academico": per})
        n_ev += 1

    # 2) Acciones de mejora en el plan
    planes = frappe.get_all("Plan Mejora", {"autoevaluacion": ae}, pluck="name")
    n_acc = 0
    if planes:
        acciones = [("Actualizar el plan de estudios al nuevo modelo educativo", "Correctiva", 100, "Verificada eficaz"),
                    ("Implementar encuesta de satisfacción estudiantil semestral", "Mejora", 60, "En ejecucion"),
                    ("Fortalecer el sistema de seguimiento a egresados", "Preventiva", 30, "Planificada")]
        for i, (desc, tipo, av, est) in enumerate(acciones):
            cod = "ACC-DEMO-%02d" % (i + 1)
            if frappe.db.exists("Accion Mejora", cod):
                continue
            _ins({"doctype": "Accion Mejora", "codigo": cod, "plan_mejora": planes[0],
                  "descripcion": "[DEMO] " + desc, "tipo": tipo, "avance_pct": av, "estado": est})
            n_acc += 1

    # 3) Hallazgos adicionales
    extra_h = [("CONEAU-3.1", "Falta formalizar el plan de mejora del área de investigación"),
               ("CONEAU-2.1", "Oportunidad de digitalizar los registros de asistencia docente")]
    n_h = 0
    for i, (crit, desc) in enumerate(extra_h):
        cod = "HALL-DEMO-%02d" % (i + 1)
        if frappe.db.exists("Hallazgo", cod) or not frappe.db.exists("Elemento Marco", crit):
            continue
        _ins({"doctype": "Hallazgo", "codigo": cod, "tipo": "Debilidad", "estado": "Abierto",
              "criterio": crit, "autoevaluacion": ae, "descripcion": "[DEMO] " + desc})
        n_h += 1

    # 4) Valores de indicadores
    inds = frappe.get_all("Indicador", pluck="name", limit_page_length=12)
    vals = [78.5, 92.0, 65.3, 88.0, 71.2, 95.5, 60.0, 83.7, 90.1, 74.4]
    n_vi = 0
    for i, ind in enumerate(inds[:10]):
        if frappe.db.exists("Valor Indicador", {"indicador": ind, "autoevaluacion": ae}):
            continue
        _ins({"doctype": "Valor Indicador", "indicador": ind, "autoevaluacion": ae,
              "periodo_academico": per, "programa_sede": ps,
              "valor_num": vals[i % len(vals)], "fuente": "[DEMO] Fuente de prueba"})
        n_vi += 1

    frappe.db.commit()
    print("DEMO_SEED DONE: %d evidencias · %d acciones · %d hallazgos · %d valores indicador"
          % (n_ev, n_acc, n_h, n_vi))
