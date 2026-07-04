"""F1 gobierno — crea los DocTypes de las ramas 6 (Satisfaccion / grupos de interes)
y 7 (Comites, actas y politica) del dominio E. Solo estructura (F1).

Ejecutar (lo hace el orquestador, NO este agente):
    bench --site sgc.localhost execute sgc.setup.f1_gobierno.run

Grupo B3 · modulo "SGC Gobierno" · depende de A1 (Indicador, Programa Sede,
Unidad Organica, Periodo Academico) y A2 (Valor Indicador, Documento Controlado).
"""
import frappe

MODULE = "SGC Gobierno"

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
    # =====================================================================
    # CHILD TABLES PRIMERO (istable=1, sin permissions ni autoname)
    # =====================================================================

    # Reunion Asistente (child auxiliar del patron Table MultiSelect de Reunion.asistentes)
    # Frappe NO admite Table MultiSelect -> User directo: requiere un child con un Link.
    _dt("Reunion Asistente", [
        {"fieldname":"usuario","fieldtype":"Link","label":"Usuario","options":"User","reqd":1,"in_list_view":1},
    ], istable=1)

    # 7.2 Miembro Comite (child de Comite)
    _dt("Miembro Comite", [
        {"fieldname":"usuario","fieldtype":"Link","label":"Usuario","options":"User","reqd":1,"in_list_view":1},
        {"fieldname":"rol","fieldtype":"Select","label":"Rol",
         "options":"Presidente\nSecretario\nMiembro\nInvitado","in_list_view":1},
        {"fieldname":"desde","fieldtype":"Date","label":"Desde","in_list_view":1},
        {"fieldname":"hasta","fieldtype":"Date","label":"Hasta","in_list_view":1},
    ], istable=1)

    # =====================================================================
    # RAMA 6 — SATISFACCION / GRUPOS DE INTERES (M-Interes)
    # =====================================================================

    # 6.1 Grupo Interes (config)
    _dt("Grupo Interes", [
        {"fieldname":"codigo","fieldtype":"Data","label":"Código","reqd":1,"unique":1,"in_list_view":1},
        {"fieldname":"nombre","fieldtype":"Data","label":"Nombre","reqd":1,"in_list_view":1},
        {"fieldname":"tipo","fieldtype":"Select","label":"Tipo",
         "options":"Beneficiario\nColaborador\nExterno","in_list_view":1,"in_standard_filter":1},
        {"fieldname":"descripcion","fieldtype":"Small Text","label":"Descripción"},
    ], autoname="field:codigo", title_field="nombre")

    # 6.2 Instrumento (plantilla de medicion)
    _dt("Instrumento", [
        {"fieldname":"codigo","fieldtype":"Data","label":"Código","reqd":1,"unique":1,"in_list_view":1},
        {"fieldname":"nombre","fieldtype":"Data","label":"Nombre","reqd":1,"in_list_view":1},
        {"fieldname":"tipo","fieldtype":"Select","label":"Tipo",
         "options":"Encuesta satisfacción\nFocus group\nEntrevista\nBuzón","in_list_view":1,"in_standard_filter":1},
        {"fieldname":"grupo_interes","fieldtype":"Link","label":"Grupo de interés","options":"Grupo Interes","in_standard_filter":1},
        {"fieldname":"plataforma","fieldtype":"Select","label":"Plataforma",
         "options":"LimeSurvey\nOtra","default":"LimeSurvey"},
        {"fieldname":"limesurvey_survey_id","fieldtype":"Data","label":"LimeSurvey survey_id",
         "description":"Puntero al survey en LimeSurvey (RemoteControl2). [VERIFICAR] acceso."},
        {"fieldname":"indicador","fieldtype":"Link","label":"Indicador","options":"Indicador",
         "description":"A qué indicador tributa el resultado (A1)."},
        {"fieldname":"escala","fieldtype":"Text","label":"Escala","description":"P. ej. Likert 1-5; qué punto es satisfactorio."},
    ], autoname="field:codigo", title_field="nombre")

    # 6.3 Aplicacion Instrumento (una aplicacion en un periodo)
    _dt("Aplicacion Instrumento", [
        {"fieldname":"instrumento","fieldtype":"Link","label":"Instrumento","options":"Instrumento","reqd":1,"in_list_view":1},
        {"fieldname":"periodo_academico","fieldtype":"Link","label":"Periodo académico","options":"Periodo Academico","in_standard_filter":1},
        {"fieldname":"unidad_organica","fieldtype":"Link","label":"Unidad orgánica","options":"Unidad Organica","in_standard_filter":1},
        {"fieldname":"programa_sede","fieldtype":"Link","label":"Programa-Sede","options":"Programa Sede","in_standard_filter":1},
        {"fieldname":"fecha_inicio","fieldtype":"Date","label":"Fecha inicio"},
        {"fieldname":"fecha_fin","fieldtype":"Date","label":"Fecha fin"},
        {"fieldname":"poblacion","fieldtype":"Int","label":"Población"},
        {"fieldname":"muestra","fieldtype":"Int","label":"Muestra"},
        {"fieldname":"tasa_respuesta","fieldtype":"Percent","label":"Tasa de respuesta"},
        {"fieldname":"limesurvey_response_count","fieldtype":"Int","label":"Respuestas LimeSurvey"},
        {"fieldname":"estado","fieldtype":"Select","label":"Estado",
         "options":"Planificada\nEn campo\nCerrada","default":"Planificada","in_list_view":1,"in_standard_filter":1},
    ], autoname="format:APL-{YYYY}-{#####}", title_field="instrumento")

    # 6.4 Resultado Instrumento (agregado que alimenta el indicador)
    _dt("Resultado Instrumento", [
        {"fieldname":"aplicacion_instrumento","fieldtype":"Link","label":"Aplicación de instrumento","options":"Aplicacion Instrumento","reqd":1,"in_list_view":1},
        {"fieldname":"dimension","fieldtype":"Data","label":"Dimensión","in_list_view":1},
        {"fieldname":"valor","fieldtype":"Float","label":"Valor","in_list_view":1},
        {"fieldname":"unidad","fieldtype":"Data","label":"Unidad","description":"%, media Likert…"},
        {"fieldname":"n","fieldtype":"Int","label":"n"},
        {"fieldname":"fecha_corte","fieldtype":"Date","label":"Fecha de corte"},
        {"fieldname":"valor_indicador","fieldtype":"Link","label":"Valor indicador","options":"Valor Indicador",
         "description":"Materializa la lectura fechada que el motor de indicadores lee (A2)."},
    ], autoname="format:RES-{YYYY}-{#####}", title_field="dimension")

    # =====================================================================
    # RAMA 7 — COMITES, ACTAS Y POLITICA (M-Gobierno)
    # =====================================================================

    # 7.1 Comite
    _dt("Comite", [
        {"fieldname":"codigo","fieldtype":"Data","label":"Código","reqd":1,"unique":1,"in_list_view":1},
        {"fieldname":"nombre","fieldtype":"Data","label":"Nombre","reqd":1,"in_list_view":1},
        {"fieldname":"tipo","fieldtype":"Select","label":"Tipo",
         "options":"Calidad institucional\nAutoevaluación de programa\nComité de riesgos\nAd-hoc","in_list_view":1,"in_standard_filter":1},
        {"fieldname":"unidad_organica","fieldtype":"Link","label":"Unidad orgánica","options":"Unidad Organica","in_standard_filter":1},
        {"fieldname":"programa_sede","fieldtype":"Link","label":"Programa-Sede","options":"Programa Sede","in_standard_filter":1},
        {"fieldname":"presidente","fieldtype":"Link","label":"Presidente","options":"User"},
        {"fieldname":"secretario","fieldtype":"Link","label":"Secretario","options":"User"},
        {"fieldname":"miembros","fieldtype":"Table","label":"Miembros","options":"Miembro Comite"},
        {"fieldname":"documento_controlado","fieldtype":"Link","label":"Documento de constitución","options":"Documento Controlado",
         "description":"Resolución de creación (A2)."},
        {"fieldname":"estado","fieldtype":"Select","label":"Estado",
         "options":"Activo\nInactivo","default":"Activo","in_list_view":1,"in_standard_filter":1},
    ], autoname="field:codigo", title_field="nombre")

    # 7.3 Reunion (Acta)
    _dt("Reunion", [
        {"fieldname":"comite","fieldtype":"Link","label":"Comité","options":"Comite","reqd":1,"in_list_view":1,"in_standard_filter":1},
        {"fieldname":"titulo","fieldtype":"Data","label":"Título","in_list_view":1},
        {"fieldname":"numero_sesion","fieldtype":"Int","label":"N.º de sesión"},
        {"fieldname":"fecha","fieldtype":"Datetime","label":"Fecha","in_list_view":1},
        {"fieldname":"modalidad","fieldtype":"Select","label":"Modalidad",
         "options":"Presencial\nVirtual\nHíbrida"},
        {"fieldname":"asistentes","fieldtype":"Table MultiSelect","label":"Asistentes","options":"Reunion Asistente"},
        {"fieldname":"agenda","fieldtype":"Text Editor","label":"Agenda"},
        {"fieldname":"desarrollo","fieldtype":"Text Editor","label":"Desarrollo"},
        {"fieldname":"estado","fieldtype":"Select","label":"Estado",
         "options":"Borrador\nAprobada\nFirmada","default":"Borrador","in_list_view":1,"in_standard_filter":1},
        {"fieldname":"pdf","fieldtype":"Attach","label":"Acta firmada (PDF)"},
    ], autoname="format:ACTA-{YYYY}-{#####}", title_field="titulo")

    # 7.4 Acuerdo (compromiso accionable con seguimiento)
    _dt("Acuerdo", [
        {"fieldname":"reunion","fieldtype":"Link","label":"Reunión","options":"Reunion","reqd":1,"in_list_view":1,"in_standard_filter":1},
        {"fieldname":"descripcion","fieldtype":"Text","label":"Descripción","in_list_view":1},
        {"fieldname":"responsable","fieldtype":"Link","label":"Responsable","options":"User","in_standard_filter":1},
        {"fieldname":"fecha_compromiso","fieldtype":"Date","label":"Fecha de compromiso"},
        {"fieldname":"estado","fieldtype":"Select","label":"Estado",
         "options":"Pendiente\nEn proceso\nCumplido\nVencido\nCancelado","default":"Pendiente","in_list_view":1,"in_standard_filter":1},
        {"fieldname":"genero_doctype","fieldtype":"Link","label":"Tipo de documento generado","options":"DocType",
         "description":"Un acuerdo puede escalar a Accion Mejora / No Conformidad…"},
        {"fieldname":"genero_id","fieldtype":"Dynamic Link","label":"Documento generado","options":"genero_doctype"},
    ], autoname="format:ACU-{YYYY}-{#####}", title_field="descripcion")

    # 7.5 Politica Calidad
    _dt("Politica Calidad", [
        {"fieldname":"codigo","fieldtype":"Data","label":"Código","reqd":1,"unique":1,"in_list_view":1},
        {"fieldname":"version","fieldtype":"Data","label":"Versión","in_list_view":1},
        {"fieldname":"texto","fieldtype":"Text Editor","label":"Texto de la política"},
        {"fieldname":"vigente_desde","fieldtype":"Date","label":"Vigente desde","in_list_view":1},
        {"fieldname":"vigente_hasta","fieldtype":"Date","label":"Vigente hasta"},
        {"fieldname":"aprobada_por","fieldtype":"Link","label":"Aprobada por","options":"User"},
        {"fieldname":"documento_controlado","fieldtype":"Link","label":"Documento publicado","options":"Documento Controlado",
         "description":"La política publicada (A2)."},
        {"fieldname":"estado","fieldtype":"Select","label":"Estado",
         "options":"Borrador\nVigente\nDerogada","default":"Borrador","in_list_view":1,"in_standard_filter":1},
    ], autoname="field:codigo", title_field="version")

    # 7.6 Objetivo Calidad
    _dt("Objetivo Calidad", [
        {"fieldname":"codigo","fieldtype":"Data","label":"Código","reqd":1,"unique":1,"in_list_view":1},
        {"fieldname":"politica_calidad","fieldtype":"Link","label":"Política de calidad","options":"Politica Calidad","in_standard_filter":1},
        {"fieldname":"descripcion","fieldtype":"Text","label":"Descripción","in_list_view":1},
        {"fieldname":"indicador","fieldtype":"Link","label":"Indicador","options":"Indicador",
         "description":"Medible con un indicador (A1)."},
        {"fieldname":"meta_valor","fieldtype":"Float","label":"Meta"},
        {"fieldname":"unidad","fieldtype":"Data","label":"Unidad","description":"% / n.º"},
        {"fieldname":"periodo_academico","fieldtype":"Link","label":"Periodo académico","options":"Periodo Academico","in_standard_filter":1},
        {"fieldname":"unidad_organica","fieldtype":"Link","label":"Unidad orgánica","options":"Unidad Organica","in_standard_filter":1},
        {"fieldname":"responsable","fieldtype":"Link","label":"Responsable","options":"User"},
        {"fieldname":"valor_actual","fieldtype":"Float","label":"Valor actual",
         "description":"Último Valor Indicador del indicador (calculado en F2+)."},
        {"fieldname":"estado","fieldtype":"Select","label":"Estado",
         "options":"Vigente\nCumplido\nNo cumplido\nEn riesgo","default":"Vigente","in_list_view":1,"in_standard_filter":1},
    ], autoname="field:codigo", title_field="descripcion")

    frappe.db.commit()
    print("f1_gobierno OK")
