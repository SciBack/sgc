"""F1 riesgos — crea los DocTypes de las ramas 3 (Riesgos/GRC) y 5 (Obligaciones a entes).
Módulo: SGC Riesgos. Depende de A1 (Unidad Organica, Elemento Marco, Documento? no) y A2
(Accion Mejora, No Conformidad, Evidencia), B4 (Proceso, Informe Cumplimiento).

Ejecutar (lo hace el orquestador, NO este agente):
bench --site sgc.localhost execute sgc.setup.f1_riesgos.run
"""
import frappe

MODULE = "SGC Riesgos"

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
    # ================= RAMA 3 — Riesgos / GRC (ISO 31000) =================

    # 3.1 Matriz Riesgo (config) — escala prob×impacto como dato
    _dt("Matriz Riesgo", [
        {"fieldname": "codigo", "fieldtype": "Data", "label": "Código", "reqd": 1, "unique": 1, "in_list_view": 1},
        {"fieldname": "nombre", "fieldtype": "Data", "label": "Nombre", "reqd": 1, "in_list_view": 1},
        {"fieldname": "dimension", "fieldtype": "Int", "label": "Dimensión", "description": "p. ej. 5 (matriz 5×5)", "in_list_view": 1},
        {"fieldname": "cfg_sb", "fieldtype": "Section Break", "label": "Configuración de escala"},
        {"fieldname": "niveles_probabilidad", "fieldtype": "JSON", "label": "Niveles de probabilidad", "description": "[{valor,etiqueta}]"},
        {"fieldname": "niveles_impacto", "fieldtype": "JSON", "label": "Niveles de impacto", "description": "[{valor,etiqueta}]"},
        {"fieldname": "umbrales", "fieldtype": "JSON", "label": "Umbrales", "description": "mapea rango de score → Bajo/Moderado/Alto/Extremo + color"},
    ], autoname="field:codigo", title_field="nombre")

    # 3.2 Riesgo — el riesgo identificado (ISO 31000 §6.4.2)
    _dt("Riesgo", [
        {"fieldname": "titulo", "fieldtype": "Data", "label": "Título", "reqd": 1, "in_list_view": 1},
        {"fieldname": "descripcion", "fieldtype": "Text", "label": "Descripción", "description": "evento incierto"},
        {"fieldname": "categoria", "fieldtype": "Select", "label": "Categoría",
         "options": "Estrategico\nOperacional\nCumplimiento\nFinanciero\nReputacional\nSeguridad de informacion\nAcademico",
         "in_list_view": 1, "in_standard_filter": 1},
        {"fieldname": "sb_scoping", "fieldtype": "Section Break", "label": "Ámbito"},
        {"fieldname": "unidad_organica", "fieldtype": "Link", "label": "Unidad orgánica", "options": "Unidad Organica",
         "description": "dueño del riesgo", "in_standard_filter": 1},
        {"fieldname": "proceso", "fieldtype": "Link", "label": "Proceso", "options": "Proceso",
         "description": "riesgo de proceso (vincula GRC↔gestión por procesos)"},
        {"fieldname": "elemento_marco", "fieldtype": "Link", "label": "Elemento de marco", "options": "Elemento Marco",
         "description": "si el riesgo amenaza un estándar/condición (p. ej. una CBC)"},
        {"fieldname": "cb_scoping", "fieldtype": "Column Break"},
        {"fieldname": "causa", "fieldtype": "Text", "label": "Causa", "description": "fuente del riesgo (§6.4.2)"},
        {"fieldname": "consecuencia", "fieldtype": "Text", "label": "Consecuencia", "description": "impacto potencial"},
        {"fieldname": "propietario", "fieldtype": "Link", "label": "Propietario (risk owner)", "options": "User"},
        {"fieldname": "sb_estado", "fieldtype": "Section Break"},
        {"fieldname": "matriz_riesgo", "fieldtype": "Link", "label": "Matriz de riesgo", "options": "Matriz Riesgo",
         "description": "qué escala usa"},
        {"fieldname": "estado", "fieldtype": "Select", "label": "Estado",
         "options": "Identificado\nEvaluado\nEn tratamiento\nMonitoreado\nCerrado\nMaterializado",
         "default": "Identificado", "in_list_view": 1, "in_standard_filter": 1},
    ], autoname="format:RSK-{YYYY}-{#####}", title_field="titulo")

    # 3.3 Evaluacion Riesgo — §6.4.3/6.4.4 análisis+valoración, fechada (serie)
    _dt("Evaluacion Riesgo", [
        {"fieldname": "riesgo", "fieldtype": "Link", "label": "Riesgo", "options": "Riesgo", "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
        {"fieldname": "momento", "fieldtype": "Select", "label": "Momento", "options": "Inherente\nResidual",
         "in_list_view": 1, "in_standard_filter": 1},
        {"fieldname": "fecha", "fieldtype": "Date", "label": "Fecha", "description": "permite serie temporal de reevaluación", "in_list_view": 1},
        {"fieldname": "cb_valores", "fieldtype": "Column Break"},
        {"fieldname": "probabilidad", "fieldtype": "Int", "label": "Probabilidad", "description": "valor en la escala de Matriz Riesgo"},
        {"fieldname": "impacto", "fieldtype": "Int", "label": "Impacto"},
        {"fieldname": "sb_calc", "fieldtype": "Section Break", "label": "Resultado (calculado en F4)"},
        {"fieldname": "nivel", "fieldtype": "Select", "label": "Nivel",
         "options": "Bajo\nModerado\nAlto\nExtremo",
         "description": "derivado leyendo Matriz Riesgo.umbrales (Server Script en F4)", "read_only": 1, "in_list_view": 1},
        {"fieldname": "score", "fieldtype": "Int", "label": "Score", "description": "prob×impacto (calculado en F4)", "read_only": 1},
        {"fieldname": "cb_calc", "fieldtype": "Column Break"},
        {"fieldname": "evaluado_por", "fieldtype": "Link", "label": "Evaluado por", "options": "User"},
    ], autoname="format:EVR-{YYYY}-{#####}")

    # 3.4 Tratamiento Riesgo — §6.5 opciones de tratamiento
    _dt("Tratamiento Riesgo", [
        {"fieldname": "riesgo", "fieldtype": "Link", "label": "Riesgo", "options": "Riesgo", "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
        {"fieldname": "estrategia", "fieldtype": "Select", "label": "Estrategia",
         "options": "Evitar\nReducir\nTransferir\nAceptar", "in_list_view": 1, "in_standard_filter": 1},
        {"fieldname": "descripcion", "fieldtype": "Text", "label": "Descripción", "description": "control/plan de tratamiento"},
        {"fieldname": "responsable", "fieldtype": "Link", "label": "Responsable", "options": "User"},
        {"fieldname": "fecha_compromiso", "fieldtype": "Date", "label": "Fecha compromiso"},
        {"fieldname": "estado", "fieldtype": "Select", "label": "Estado",
         "options": "Planificado\nEn ejecucion\nImplementado\nVerificado", "default": "Planificado", "in_list_view": 1},
        {"fieldname": "sb_costura", "fieldtype": "Section Break", "label": "Costura con mejora / evidencia"},
        {"fieldname": "accion_mejora", "fieldtype": "Link", "label": "Acción de mejora", "options": "Accion Mejora",
         "description": "reutiliza el CAPA si el tratamiento es una acción concreta ejecutable"},
        {"fieldname": "evidencia", "fieldtype": "Link", "label": "Evidencia", "options": "Evidencia",
         "description": "prueba de implementación del control"},
    ], autoname="format:TRR-{YYYY}-{#####}")

    # ================= RAMA 5 — Obligaciones / entregas a entes =================

    # 5.1 Ente Externo (config)
    _dt("Ente Externo", [
        {"fieldname": "codigo", "fieldtype": "Data", "label": "Código", "reqd": 1, "unique": 1, "in_list_view": 1},
        {"fieldname": "nombre", "fieldtype": "Data", "label": "Nombre", "reqd": 1, "in_list_view": 1,
         "description": "SUNEDU·SINEACE·CONCYTEC·MINEDU·INEI·SUNAT/MTPE·PRONABEC·PCM-SGTD"},
        {"fieldname": "tipo", "fieldtype": "Select", "label": "Tipo",
         "options": "Regulador\nAcreditador\nEstadistico\nTributario", "in_list_view": 1, "in_standard_filter": 1},
        {"fieldname": "canal_default", "fieldtype": "Select", "label": "Canal por defecto",
         "options": "OAI-PMH\nCERIF+OAI-PMH\nSOAP/WSDL (PIDE)\nFormulario web\nCarga documental\nDVD"},
        {"fieldname": "url", "fieldtype": "Data", "label": "URL"},
        {"fieldname": "notas", "fieldtype": "Text", "label": "Notas"},
    ], autoname="field:codigo", title_field="nombre")

    # 5.2 Obligacion Ente — registro vivo de obligaciones
    _dt("Obligacion Ente", [
        {"fieldname": "codigo", "fieldtype": "Data", "label": "Código", "reqd": 1, "unique": 1, "in_list_view": 1},
        {"fieldname": "nombre", "fieldtype": "Data", "label": "Nombre", "reqd": 1, "in_list_view": 1,
         "description": "\"IAC — cumplimiento CBC\", \"Tesis RENATI\", \"SIBE\""},
        {"fieldname": "ente_externo", "fieldtype": "Link", "label": "Ente externo", "options": "Ente Externo",
         "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
        {"fieldname": "descripcion", "fieldtype": "Text", "label": "Descripción", "description": "qué se entrega"},
        {"fieldname": "sb_periodicidad", "fieldtype": "Section Break", "label": "Periodicidad y vencimiento"},
        {"fieldname": "periodicidad", "fieldtype": "Select", "label": "Periodicidad",
         "options": "Continua\nMensual\nSemestral\nAnual\nDecenal\nPor proceso\nOn-demand",
         "in_list_view": 1, "in_standard_filter": 1},
        {"fieldname": "fecha_referencia", "fieldtype": "Date", "label": "Fecha de referencia", "description": "ancla del cálculo (p. ej. 31-mar para IAC)"},
        {"fieldname": "proximo_vencimiento", "fieldtype": "Date", "label": "Próximo vencimiento",
         "description": "calculado por Scheduler desde periodicidad+fecha_referencia (F4)", "read_only": 1, "in_list_view": 1},
        {"fieldname": "cb_periodicidad", "fieldtype": "Column Break"},
        {"fieldname": "interoperable", "fieldtype": "Select", "label": "Interoperable",
         "options": "Alto\nMedio\nBajo", "description": "semáforo de automatización del mapa"},
        {"fieldname": "protocolo", "fieldtype": "Data", "label": "Protocolo", "description": "OAI-PMH / CERIF / SOAP-PIDE / formulario"},
        {"fieldname": "sistema_fuente", "fieldtype": "Data", "label": "Sistema fuente", "description": "DSpace / DSpace-CRIS / SGC / RRHH"},
        {"fieldname": "sb_resp", "fieldtype": "Section Break", "label": "Responsabilidad"},
        {"fieldname": "responsable", "fieldtype": "Link", "label": "Responsable", "options": "User"},
        {"fieldname": "unidad_organica", "fieldtype": "Link", "label": "Unidad orgánica", "options": "Unidad Organica",
         "description": "área responsable"},
        {"fieldname": "documento_controlado", "fieldtype": "Link", "label": "Documento controlado", "options": "Documento Controlado",
         "description": "plantilla/instructivo"},
        {"fieldname": "activa", "fieldtype": "Check", "label": "Activa", "default": "1"},
    ], autoname="field:codigo", title_field="nombre")

    # 5.3 Entrega Obligacion — cada cumplimiento concreto (la serie)
    _dt("Entrega Obligacion", [
        {"fieldname": "obligacion_ente", "fieldtype": "Link", "label": "Obligación al ente", "options": "Obligacion Ente",
         "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
        {"fieldname": "periodo", "fieldtype": "Data", "label": "Periodo", "description": "\"2026\", \"2026-I\"", "in_list_view": 1},
        {"fieldname": "fecha_limite", "fieldtype": "Date", "label": "Fecha límite", "in_list_view": 1},
        {"fieldname": "fecha_entrega", "fieldtype": "Date", "label": "Fecha de entrega"},
        {"fieldname": "estado", "fieldtype": "Select", "label": "Estado",
         "options": "Pendiente\nEn preparacion\nEntregada\nAceptada\nObservada\nSubsanada",
         "default": "Pendiente", "in_list_view": 1, "in_standard_filter": 1},
        {"fieldname": "responsable", "fieldtype": "Link", "label": "Responsable", "options": "User"},
        {"fieldname": "observaciones", "fieldtype": "Text", "label": "Observaciones"},
        {"fieldname": "sb_costura", "fieldtype": "Section Break", "label": "Costura con evidencia / IAC / NC"},
        {"fieldname": "evidencia", "fieldtype": "Link", "label": "Evidencia", "options": "Evidencia",
         "description": "cargo/constancia de la entrega"},
        {"fieldname": "informe_cumplimiento", "fieldtype": "Link", "label": "Informe de cumplimiento (IAC)", "options": "Informe Cumplimiento",
         "description": "si la entrega ES el IAC"},
        {"fieldname": "no_conformidad", "fieldtype": "Link", "label": "No conformidad", "options": "No Conformidad",
         "description": "si una entrega se incumple/observa → NC (origen=ObligacionEnte)"},
    ], autoname="format:ENT-{YYYY}-{#####}")

    # child de enlace para Table MultiSelect de Riesgo (Frappe exige child con Link)
    _dt("Riesgo Enlace", [
        {"fieldname":"riesgo","fieldtype":"Link","label":"Riesgo","options":"Riesgo","in_list_view":1,"reqd":1},
    ], istable=1)

    frappe.db.commit()
    print("f1_riesgos OK")
