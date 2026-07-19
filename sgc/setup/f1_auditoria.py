"""F1 auditoria — crea los DocTypes de las ramas 1 (Auditoría interna) y 4
(Revisión por la dirección). Grupo B1, módulo `SGC Auditoria`. Ejecutar:
bench --site sgc.localhost execute sgc.setup.f1_auditoria.run

Solo ESTRUCTURA (F1): sin is_submittable, sin Workflow. `estado` = Select.
Child tables se crean antes que sus padres. Idempotente vía `_dt`.

Links a targets de OTROS agentes (existirán al integrar en el orden A1→A2→B*):
- `Programa Sede`, `Unidad Organica`, `Programa`, `Periodo Academico` → A1
- `Elemento Marco` → A1
- `Proceso` → B4
- `Evidencia` → A2
- `No Conformidad` → A2
- `Comite`, `Reunion` → B3
- `User` → Frappe core
- `DocType` → Frappe core (para Dynamic Link polimórfico)
"""
import frappe

MODULE = "SGC Auditoria"


def _dt(name, fields, istable=0, is_tree=0, autoname=None, title_field=None,
        search_fields=None, track_changes=1):
    if frappe.db.exists("DocType", name):
        return
    doc = {
        "doctype": "DocType", "name": name, "module": MODULE, "custom": 0,
        "istable": istable, "is_tree": is_tree,
        "editable_grid": 1 if istable else 0,
        "track_changes": 0 if istable else track_changes,
        "fields": fields,
        "permissions": [] if istable else [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1}
        ],
    }
    if autoname: doc["autoname"] = autoname
    if title_field: doc["title_field"] = title_field
    if search_fields: doc["search_fields"] = search_fields
    frappe.get_doc(doc).insert(ignore_permissions=True)


def run():
    # ==================================================================
    # RAMA 1 — Auditoría interna (ISO 9001 §9.2)
    # ==================================================================

    # ---- Child tables PRIMERO ----

    # 1.3 Criterio Auditoria (child de Auditoria) — polimórfico por tipo
    _dt("Criterio Auditoria", [
        {"fieldname":"tipo_criterio","fieldtype":"Select","label":"Tipo de criterio",
         "options":"Clausula norma\nElemento de marco\nDocumento controlado\nRequisito legal",
         "in_list_view":1},
        {"fieldname":"elemento_marco","fieldtype":"Link","label":"Elemento de marco",
         "options":"Elemento Marco","in_list_view":1},
        {"fieldname":"documento_controlado","fieldtype":"Link","label":"Documento controlado",
         "options":"Documento Controlado"},
        {"fieldname":"referencia","fieldtype":"Data","label":"Referencia",
         "in_list_view":1,"description":"Texto libre, p. ej. \"ISO 9001 §7.5\""},
    ], istable=1)

    # 1.4 Equipo Auditoria (child de Auditoria)
    _dt("Equipo Auditoria", [
        {"fieldname":"usuario","fieldtype":"Link","label":"Usuario","options":"User",
         "reqd":1,"in_list_view":1},
        {"fieldname":"rol","fieldtype":"Select","label":"Rol",
         "options":"Auditor lider\nAuditor\nObservador\nExperto tecnico","in_list_view":1},
        {"fieldname":"independiente_del_area","fieldtype":"Check",
         "label":"Independiente del área","in_list_view":1,
         "description":"Evidencia de independencia (§9.2.2 e)"},
    ], istable=1)

    # ---- Padres ----

    # 1.1 Programa Auditoria — plan anual de auditorías (§9.2.2)
    _dt("Programa Auditoria", [
        {"fieldname":"codigo","fieldtype":"Data","label":"Código","reqd":1,"unique":1,
         "in_list_view":1},
        {"fieldname":"titulo","fieldtype":"Data","label":"Título","reqd":1,"in_list_view":1},
        {"fieldname":"periodo_academico","fieldtype":"Link","label":"Periodo académico",
         "options":"Periodo Academico","in_standard_filter":1},
        {"fieldname":"objetivo","fieldtype":"Small Text","label":"Objetivo"},
        {"fieldname":"alcance","fieldtype":"Text","label":"Alcance",
         "description":"Procesos/unidades cubiertos"},
        {"fieldname":"responsable","fieldtype":"Link","label":"Responsable","options":"User",
         "description":"Jefe de Auditoría Interna"},
        {"fieldname":"estado","fieldtype":"Select","label":"Estado",
         "options":"Borrador\nAprobado\nEn ejecucion\nCerrado","default":"Borrador",
         "in_list_view":1,"in_standard_filter":1},
        {"fieldname":"aprobado_por","fieldtype":"Link","label":"Aprobado por","options":"User"},
        {"fieldname":"fecha_aprobacion","fieldtype":"Date","label":"Fecha de aprobación"},
    ], autoname="field:codigo", title_field="titulo")

    # 1.2 Auditoria — plan + ejecución de una auditoría concreta (§9.2.2 c/d)
    _dt("Auditoria", [
        {"fieldname":"programa_auditoria","fieldtype":"Link","label":"Programa de auditoría",
         "options":"Programa Auditoria","in_standard_filter":1},
        {"fieldname":"titulo","fieldtype":"Data","label":"Título","reqd":1,"in_list_view":1},
        {"fieldname":"tipo","fieldtype":"Select","label":"Tipo",
         "options":"Interna\nExterna (certificacion)\nDe seguimiento",
         "in_list_view":1,"in_standard_filter":1},
        {"fieldname":"unidad_organica","fieldtype":"Link","label":"Unidad orgánica",
         "options":"Unidad Organica","in_standard_filter":1},
        {"fieldname":"proceso","fieldtype":"Link","label":"Proceso","options":"Proceso"},
        {"fieldname":"programa_sede","fieldtype":"Link","label":"Programa-Sede",
         "options":"Programa Sede","in_standard_filter":1},
        {"fieldname":"periodo_academico","fieldtype":"Link","label":"Periodo académico",
         "options":"Periodo Academico","in_standard_filter":1},
        {"fieldname":"objetivo","fieldtype":"Small Text","label":"Objetivo"},
        {"fieldname":"alcance","fieldtype":"Text","label":"Alcance"},
        {"fieldname":"criterios","fieldtype":"Table","label":"Criterios",
         "options":"Criterio Auditoria"},
        {"fieldname":"equipo","fieldtype":"Table","label":"Equipo auditor",
         "options":"Equipo Auditoria"},
        {"fieldname":"fecha_plan","fieldtype":"Date","label":"Fecha planificada"},
        {"fieldname":"fecha_inicio","fieldtype":"Date","label":"Fecha de inicio"},
        {"fieldname":"fecha_fin","fieldtype":"Date","label":"Fecha de fin"},
        {"fieldname":"estado","fieldtype":"Select","label":"Estado",
         "options":"Planificada\nEn ejecucion\nEjecutada\nInforme emitido\nCerrada",
         "default":"Planificada","in_list_view":1,"in_standard_filter":1},
        {"fieldname":"informe","fieldtype":"Link","label":"Informe de auditoría",
         "options":"Informe Auditoria"},
    ], autoname="format:AUD-{YYYY}-{###}", title_field="titulo")

    # 1.5 Hallazgo Auditoria — hallazgo de auditoría (distinto del de autoevaluación)
    _dt("Hallazgo Auditoria", [
        {"fieldname":"codigo","fieldtype":"Data","label":"Código","reqd":1,"unique":1,
         "in_list_view":1},
        {"fieldname":"auditoria","fieldtype":"Link","label":"Auditoría","options":"Auditoria",
         "reqd":1,"in_standard_filter":1},
        {"fieldname":"tipo","fieldtype":"Select","label":"Tipo",
         "options":"No conformidad mayor\nNo conformidad menor\nObservacion\n"
                   "Oportunidad de mejora\nConformidad\nFortaleza",
         "in_list_view":1,"in_standard_filter":1},
        {"fieldname":"criterio_incumplido","fieldtype":"Link","label":"Criterio incumplido",
         "options":"Elemento Marco","description":"Qué requisito se incumple"},
        {"fieldname":"descripcion","fieldtype":"Text","label":"Descripción",
         "description":"Evidencia objetiva del hallazgo"},
        {"fieldname":"unidad_organica","fieldtype":"Link","label":"Unidad orgánica",
         "options":"Unidad Organica","in_standard_filter":1},
        {"fieldname":"proceso","fieldtype":"Link","label":"Proceso","options":"Proceso"},
        {"fieldname":"evidencia","fieldtype":"Table MultiSelect","label":"Evidencias",
         "options":"Evidencia Enlace"},
        {"fieldname":"genera_nc","fieldtype":"Check","label":"Genera no conformidad",
         "description":"Si escala a No Conformidad transversal (§2)"},
        {"fieldname":"no_conformidad","fieldtype":"Link","label":"No conformidad",
         "options":"No Conformidad",
         "description":"Puente a §2: el hallazgo que es NC se materializa como No Conformidad"},
        {"fieldname":"estado","fieldtype":"Select","label":"Estado",
         "options":"Abierto\nEscalado a NC\nCerrado","default":"Abierto",
         "in_list_view":1,"in_standard_filter":1},
    ], autoname="field:codigo")

    # 1.6 Informe Auditoria — §9.2.2 f (informar resultados a la dirección)
    _dt("Informe Auditoria", [
        {"fieldname":"codigo","fieldtype":"Data","label":"Código","reqd":1,"unique":1,
         "in_list_view":1},
        {"fieldname":"auditoria","fieldtype":"Link","label":"Auditoría","options":"Auditoria",
         "reqd":1,"in_standard_filter":1},
        {"fieldname":"resumen_ejecutivo","fieldtype":"Text Editor","label":"Resumen ejecutivo"},
        {"fieldname":"conclusiones","fieldtype":"Text","label":"Conclusiones"},
        {"fieldname":"n_nc_mayores","fieldtype":"Int","label":"N.º NC mayores"},
        {"fieldname":"n_nc_menores","fieldtype":"Int","label":"N.º NC menores"},
        {"fieldname":"n_observaciones","fieldtype":"Int","label":"N.º observaciones"},
        {"fieldname":"n_om","fieldtype":"Int","label":"N.º oportunidades de mejora"},
        {"fieldname":"fecha_emision","fieldtype":"Date","label":"Fecha de emisión","in_list_view":1},
        {"fieldname":"emitido_por","fieldtype":"Link","label":"Emitido por","options":"User"},
        {"fieldname":"pdf","fieldtype":"Attach","label":"PDF"},
        {"fieldname":"presentado_en","fieldtype":"Link","label":"Presentado en (Revisión Dirección)",
         "options":"Revision Direccion",
         "description":"Insumo de §9.3 — cierra el ciclo con la rama 4"},
    ], autoname="field:codigo")

    # ==================================================================
    # RAMA 4 — Revisión por la dirección (ISO 9001 §9.3)
    # ==================================================================

    # ---- Child tables PRIMERO ----

    # 4.2 Entrada Revision (child de Revision Direccion) — §9.3.2
    _dt("Entrada Revision", [
        {"fieldname":"tipo_entrada","fieldtype":"Select","label":"Tipo de entrada",
         "options":"Estado de acciones de revisiones previas\n"
                   "Cambios en cuestiones externas/internas\n"
                   "Desempeno y eficacia del SGC\n"
                   "Suficiencia de recursos\n"
                   "Eficacia de acciones frente a riesgos\n"
                   "Oportunidades de mejora",
         "in_list_view":1},
        {"fieldname":"resumen","fieldtype":"Text","label":"Resumen"},
        {"fieldname":"fuente_doctype","fieldtype":"Link","label":"Tipo de fuente",
         "options":"DocType","in_list_view":1},
        {"fieldname":"fuente_id","fieldtype":"Dynamic Link","label":"Fuente",
         "options":"fuente_doctype","in_list_view":1,
         "description":"Evidencia real: InformeAuditoria, ResultadoInstrumento, "
                       "ValorIndicador, EvaluacionRiesgo…"},
    ], istable=1)

    # 4.3 Salida Revision (child de Revision Direccion) — §9.3.3
    _dt("Salida Revision", [
        {"fieldname":"tipo_salida","fieldtype":"Select","label":"Tipo de salida",
         "options":"Oportunidad de mejora\nCambio en el SGC\nNecesidad de recursos",
         "in_list_view":1},
        {"fieldname":"descripcion","fieldtype":"Text","label":"Descripción"},
        {"fieldname":"responsable","fieldtype":"Link","label":"Responsable","options":"User",
         "in_list_view":1},
        {"fieldname":"fecha_compromiso","fieldtype":"Date","label":"Fecha de compromiso"},
        {"fieldname":"genera_doctype","fieldtype":"Link","label":"Genera (tipo)",
         "options":"DocType"},
        {"fieldname":"genera_id","fieldtype":"Dynamic Link","label":"Genera",
         "options":"genera_doctype",
         "description":"Materializa en AccionMejora, Acuerdo, No Conformidad u ObjetivoCalidad"},
    ], istable=1)

    # ---- Padre ----

    # 4.1 Revision Direccion — §9.3.1 (intervalos planificados)
    _dt("Revision Direccion", [
        {"fieldname":"codigo","fieldtype":"Data","label":"Código","reqd":1,"unique":1,
         "in_list_view":1},
        {"fieldname":"titulo","fieldtype":"Data","label":"Título","reqd":1,"in_list_view":1},
        {"fieldname":"periodo_academico","fieldtype":"Link","label":"Periodo académico",
         "options":"Periodo Academico","in_standard_filter":1},
        {"fieldname":"unidad_organica","fieldtype":"Link","label":"Unidad orgánica",
         "options":"Unidad Organica","in_standard_filter":1,
         "description":"Alcance (universidad / sede / facultad)"},
        {"fieldname":"fecha","fieldtype":"Date","label":"Fecha","in_list_view":1},
        {"fieldname":"comite","fieldtype":"Link","label":"Comité","options":"Comite",
         "description":"Usualmente el Comité de Calidad la ejecuta (rama 7)"},
        {"fieldname":"reunion","fieldtype":"Link","label":"Reunión (acta)","options":"Reunion",
         "description":"El acta que la respalda (rama 7)"},
        {"fieldname":"entradas","fieldtype":"Table","label":"Entradas (§9.3.2)",
         "options":"Entrada Revision"},
        {"fieldname":"salidas","fieldtype":"Table","label":"Salidas (§9.3.3)",
         "options":"Salida Revision"},
        {"fieldname":"estado","fieldtype":"Select","label":"Estado",
         "options":"Planificada\nRealizada\nCerrada","default":"Planificada",
         "in_list_view":1,"in_standard_filter":1},
        {"fieldname":"pdf","fieldtype":"Attach","label":"PDF (acta/informe)"},
    ], autoname="format:RPD-{YYYY}-{##}", title_field="titulo")

    frappe.db.commit()
    print("f1_auditoria OK")
