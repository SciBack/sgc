"""F1 procesos — crea los DocTypes de la rama B4 (SGC Procesos + IAC). Ejecutar:
bench --site sgc.localhost execute sgc.setup.f1_procesos.run

Grupo B4 — módulo `SGC Procesos`. Depende de A1/A2 y de B2 (IAC → Riesgo / Obligacion Ente).
Insumos: F (procesos, ficha SIPOC oficial, procedimiento, interacción) + E RAMA 8 (Licenciamiento/IAC §8.1-8.2).
F1 = SOLO estructura (sin is_submittable, sin Workflow; `estado` = Select). Idempotente.
"""
import frappe

MODULE = "SGC Procesos"

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
    # ============================================================
    # 1) CHILD TABLES primero (istable=1) — sin permissions ni autoname
    # ============================================================

    # --- SIPOC: entradas de la Ficha de Caracterización ---
    _dt("Entrada Proceso", [
        {"fieldname": "proveedor", "fieldtype": "Data", "label": "Proveedor", "in_list_view": 1,
         "description": "Área/unidad o parte interesada que provee (Data o Unidad Organica)"},
        {"fieldname": "unidad_organica", "fieldtype": "Link", "label": "Unidad proveedora",
         "options": "Unidad Organica"},
        {"fieldname": "insumo", "fieldtype": "Data", "label": "Insumo / Entrada", "in_list_view": 1, "reqd": 1},
    ], istable=1)

    # --- SIPOC: salidas de la Ficha de Caracterización ---
    _dt("Salida Proceso", [
        {"fieldname": "entregable", "fieldtype": "Data", "label": "Entregable / Salida", "in_list_view": 1, "reqd": 1},
        {"fieldname": "cliente", "fieldtype": "Data", "label": "Cliente", "in_list_view": 1,
         "description": "Destinatario de la salida (Data o proceso destino)"},
        {"fieldname": "unidad_organica", "fieldtype": "Link", "label": "Unidad cliente",
         "options": "Unidad Organica"},
    ], istable=1)

    # --- Actividades principales / procedimientos ---
    _dt("Actividad Proceso", [
        {"fieldname": "descripcion", "fieldtype": "Small Text", "label": "Descripción de la actividad",
         "in_list_view": 1, "reqd": 1},
        {"fieldname": "procedimiento", "fieldtype": "Link", "label": "Procedimiento", "options": "Procedimiento"},
        {"fieldname": "orden", "fieldtype": "Int", "label": "Orden", "in_list_view": 1},
    ], istable=1)

    # --- Riesgos + acción de mitigación (con puente al inventario GRC B2) ---
    _dt("Riesgo Proceso", [
        {"fieldname": "riesgo_identificado", "fieldtype": "Small Text", "label": "Riesgo identificado",
         "in_list_view": 1, "reqd": 1},
        {"fieldname": "accion_mitigacion", "fieldtype": "Small Text", "label": "Acción de mitigación",
         "in_list_view": 1},
        {"fieldname": "riesgo", "fieldtype": "Link", "label": "Riesgo (inventario GRC)", "options": "Riesgo",
         "description": "Escala el riesgo de la ficha al inventario GRC formal (B2) sin recapturarse"},
    ], istable=1)

    # --- Registros del proceso ---
    _dt("Registro Proceso", [
        {"fieldname": "registro", "fieldtype": "Data", "label": "Registro", "in_list_view": 1, "reqd": 1},
        {"fieldname": "responsable", "fieldtype": "Link", "label": "Responsable", "options": "User"},
        {"fieldname": "frecuencia_revision", "fieldtype": "Data", "label": "Frecuencia de revisión"},
    ], istable=1)

    # --- Documentos asociados (reutiliza Documento Controlado / Mayan) ---
    _dt("Doc Proceso Link", [
        {"fieldname": "documento_controlado", "fieldtype": "Link", "label": "Documento controlado",
         "options": "Documento Controlado", "in_list_view": 1, "reqd": 1},
        {"fieldname": "nota", "fieldtype": "Data", "label": "Nota"},
    ], istable=1)

    # --- Indicadores de la ficha (Link de conveniencia al Indicador polimórfico A1) ---
    _dt("Indicador Proceso Link", [
        {"fieldname": "indicador", "fieldtype": "Link", "label": "Indicador", "options": "Indicador",
         "in_list_view": 1, "reqd": 1},
    ], istable=1)

    # --- Control de cambios de la ficha ---
    _dt("Cambio Ficha", [
        {"fieldname": "version", "fieldtype": "Data", "label": "Versión", "in_list_view": 1, "reqd": 1},
        {"fieldname": "fecha", "fieldtype": "Date", "label": "Fecha", "in_list_view": 1},
        {"fieldname": "detalle", "fieldtype": "Small Text", "label": "Detalle del cambio", "in_list_view": 1},
    ], istable=1)

    # --- Cumplimiento por condición CBC (child del IAC / Informe Cumplimiento) ---
    _dt("Cumplimiento CBC", [
        {"fieldname": "condicion", "fieldtype": "Link", "label": "Condición (CBC)", "options": "Elemento Marco",
         "in_list_view": 1, "reqd": 1},
        {"fieldname": "cumple", "fieldtype": "Select", "label": "Cumplimiento",
         "options": "Cumple\nCumple parcial\nNo cumple", "in_list_view": 1},
        {"fieldname": "justificacion", "fieldtype": "Text", "label": "Justificación"},
        {"fieldname": "evidencia", "fieldtype": "Table MultiSelect", "label": "Evidencias", "options": "Evidencia Enlace"},
        {"fieldname": "no_conformidad", "fieldtype": "Link", "label": "No conformidad",
         "options": "No Conformidad",
         "description": "Una CBC 'No cumple' abre una No Conformidad (A2)"},
    ], istable=1)

    # ============================================================
    # 2) PADRES
    # ============================================================

    # --- Proceso (Tree, mapa E/C/S navegable) ---
    _dt("Proceso", [
        {"fieldname": "codigo", "fieldtype": "Data", "label": "Código", "reqd": 1, "unique": 1, "in_list_view": 1,
         "description": "PK natural: E01…E04 · C01…C13 · S01…S05"},
        {"fieldname": "proceso", "fieldtype": "Data", "label": "Denominación del proceso", "in_list_view": 1,
         "description": "Denominación oficial (PENDIENTE Mapa v8.0 para los 22)"},
        {"fieldname": "nivel", "fieldtype": "Select", "label": "Nivel",
         "options": "Estratégico\nClave\nSoporte", "in_list_view": 1, "in_standard_filter": 1},
        {"fieldname": "subsistema", "fieldtype": "Data", "label": "Subsistema"},
        {"fieldname": "propietario_unidad", "fieldtype": "Link", "label": "Propietario (área)",
         "options": "Unidad Organica"},
        {"fieldname": "responsable", "fieldtype": "Link", "label": "Responsable (dueño de proceso)",
         "options": "User"},
        {"fieldname": "estado", "fieldtype": "Select", "label": "Estado",
         "options": "Borrador\nVigente\nObsoleto", "default": "Borrador", "in_standard_filter": 1},
        {"fieldname": "orden", "fieldtype": "Int", "label": "Orden"},
        {"fieldname": "is_group", "fieldtype": "Check", "label": "Es grupo (macroproceso)"},
        {"fieldname": "parent_proceso", "fieldtype": "Link", "label": "Proceso padre", "options": "Proceso"},
    ], is_tree=1, autoname="field:codigo", title_field="proceso")

    # --- Procedimiento (N:1 con Proceso; es documento controlado con diagrama de flujo) ---
    _dt("Procedimiento", [
        {"fieldname": "codigo", "fieldtype": "Data", "label": "Código", "reqd": 1, "unique": 1, "in_list_view": 1},
        {"fieldname": "titulo", "fieldtype": "Data", "label": "Título", "in_list_view": 1},
        {"fieldname": "proceso", "fieldtype": "Link", "label": "Proceso", "options": "Proceso",
         "in_list_view": 1, "in_standard_filter": 1},
        {"fieldname": "documento_controlado", "fieldtype": "Link", "label": "Documento controlado",
         "options": "Documento Controlado"},
        {"fieldname": "diagrama_flujo", "fieldtype": "Attach", "label": "Diagrama de flujo",
         "description": "Diagrama de flujo formato UPeU (NO BPMN) — adjunto/PDF del editor"},
        {"fieldname": "estado", "fieldtype": "Select", "label": "Estado",
         "options": "Borrador\nEn revisión\nAprobado\nPublicado\nObsoleto", "default": "Borrador",
         "in_standard_filter": 1},
    ], autoname="field:codigo", title_field="titulo")

    # --- Ficha Caracterizacion Proceso (1:1 con Proceso; plantilla SIPOC oficial 2026) ---
    _dt("Ficha Caracterizacion Proceso", [
        {"fieldname": "proceso", "fieldtype": "Link", "label": "Proceso", "options": "Proceso",
         "reqd": 1, "unique": 1, "in_list_view": 1},
        {"fieldname": "version", "fieldtype": "Data", "label": "Versión", "in_list_view": 1},
        {"fieldname": "fecha_emision", "fieldtype": "Date", "label": "Fecha de emisión"},
        {"fieldname": "estado", "fieldtype": "Select", "label": "Estado",
         "options": "Borrador\nEn revisión\nAprobado\nPublicado\nObsoleto", "default": "Borrador",
         "in_standard_filter": 1},
        {"fieldname": "sec_plan", "fieldtype": "Section Break", "label": "Planificar (P)"},
        {"fieldname": "objetivo", "fieldtype": "Small Text", "label": "Objetivo del proceso"},
        {"fieldname": "alcance", "fieldtype": "Small Text", "label": "Alcance"},
        {"fieldname": "requisitos_aplicables", "fieldtype": "Small Text", "label": "Requisitos aplicables"},
        {"fieldname": "recursos", "fieldtype": "Small Text", "label": "Recursos"},
        {"fieldname": "sec_entradas", "fieldtype": "Section Break", "label": "SIPOC"},
        {"fieldname": "entradas", "fieldtype": "Table", "label": "Entradas", "options": "Entrada Proceso"},
        {"fieldname": "actividades", "fieldtype": "Table", "label": "Actividades / Procedimientos",
         "options": "Actividad Proceso"},
        {"fieldname": "salidas", "fieldtype": "Table", "label": "Salidas", "options": "Salida Proceso"},
        {"fieldname": "sec_verificar", "fieldtype": "Section Break", "label": "Verificar / Actuar (V/A)"},
        {"fieldname": "indicadores", "fieldtype": "Table", "label": "Indicadores",
         "options": "Indicador Proceso Link"},
        {"fieldname": "registros", "fieldtype": "Table", "label": "Registros", "options": "Registro Proceso"},
        {"fieldname": "riesgos", "fieldtype": "Table", "label": "Riesgos", "options": "Riesgo Proceso"},
        {"fieldname": "documentos_asociados", "fieldtype": "Table", "label": "Documentos asociados",
         "options": "Doc Proceso Link"},
        {"fieldname": "sec_control", "fieldtype": "Section Break", "label": "Control de emisión y cambios"},
        {"fieldname": "elaborado_por", "fieldtype": "Link", "label": "Elaborado por", "options": "User"},
        {"fieldname": "revisado_por", "fieldtype": "Link", "label": "Revisado por", "options": "User"},
        {"fieldname": "aprobado_por", "fieldtype": "Link", "label": "Aprobado por", "options": "User"},
        {"fieldname": "resolucion_aprobacion", "fieldtype": "Data", "label": "Resolución N°"},
        {"fieldname": "control_cambios", "fieldtype": "Table", "label": "Control de cambios",
         "options": "Cambio Ficha"},
    ], autoname="format:FICHA-{proceso}", title_field="proceso")

    # --- Interaccion Proceso (grafo del mapa: quién entrega qué a quién) ---
    _dt("Interaccion Proceso", [
        {"fieldname": "proceso_origen", "fieldtype": "Link", "label": "Proceso origen", "options": "Proceso",
         "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
        {"fieldname": "proceso_destino", "fieldtype": "Link", "label": "Proceso destino", "options": "Proceso",
         "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
        {"fieldname": "objeto_intercambio", "fieldtype": "Data", "label": "Objeto de intercambio",
         "in_list_view": 1},
        {"fieldname": "tipo", "fieldtype": "Select", "label": "Tipo",
         "options": "Entrega\nRetroalimentación\nControl", "in_list_view": 1, "in_standard_filter": 1},
    ], autoname="hash", title_field="objeto_intercambio")

    # --- Informe Cumplimiento (IAC — E §8.1; anual, institucional, marco CBC) ---
    _dt("Informe Cumplimiento", [
        {"fieldname": "anio", "fieldtype": "Int", "label": "Año", "reqd": 1, "in_list_view": 1,
         "in_standard_filter": 1},
        {"fieldname": "marco_normativo", "fieldtype": "Link", "label": "Marco normativo", "options": "Marco Normativo",
         "in_list_view": 1, "description": "Fija CBC-SUNEDU (reutiliza el árbol de 8 CBC)"},
        {"fieldname": "unidad_organica", "fieldtype": "Link", "label": "Unidad orgánica (institucional)",
         "options": "Unidad Organica"},
        {"fieldname": "autoevaluacion", "fieldtype": "Link", "label": "Autoevaluación de apoyo",
         "options": "Autoevaluacion",
         "description": "El IAC puede apoyarse en una Autoevaluación contra el marco CBC (A2)"},
        {"fieldname": "obligacion_ente", "fieldtype": "Link", "label": "Obligación al ente",
         "options": "Obligacion Ente", "description": "La obligación 'IAC' que este informe cumple (B2)"},
        {"fieldname": "estado", "fieldtype": "Select", "label": "Estado",
         "options": "Borrador\nEn revisión\nAprobado\nPresentado a SUNEDU", "default": "Borrador",
         "in_standard_filter": 1},
        {"fieldname": "condiciones", "fieldtype": "Table", "label": "Condiciones (CBC)",
         "options": "Cumplimiento CBC"},
        {"fieldname": "riesgos_detectados", "fieldtype": "Table MultiSelect",
         "label": "Riesgos institucionales detectados", "options": "Riesgo Enlace"},
        {"fieldname": "resumen", "fieldtype": "Text Editor", "label": "Resumen / declaración jurada"},
        {"fieldname": "fecha_presentacion", "fieldtype": "Date", "label": "Fecha de presentación"},
        {"fieldname": "pdf", "fieldtype": "Attach", "label": "Informe (PDF)"},
    ], autoname="format:IAC-{anio}", title_field="anio")

    frappe.db.commit()
    print("f1_procesos OK")
