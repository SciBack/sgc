"""F1 nucleo — crea los DocTypes del núcleo del SGC (acreditación + mejora core).
Grupo A2 · módulo "SGC Nucleo" · depende de A1 ("SGC Estructura").

Cubre: Autoevaluacion · Valoracion Criterio · Valoracion Estandar · Evidencia ·
Trazabilidad · Valor Indicador · Documento Controlado · No Conformidad · Hallazgo ·
Plan Mejora · Accion Mejora.

Fuentes de campos: insumos B (§2) y E (§2, §11). Solo ESTRUCTURA (F1): sin
is_submittable, sin Workflow; `estado` = Select. Idempotente.

Ejecutar (lo hace el orquestador, NO este agente):
bench --site sgc.localhost execute sgc.setup.f1_nucleo.run
"""
import frappe

MODULE = "SGC Nucleo"


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
    # ---- Sin child tables en este grupo: todos son padres (Doc). ----

    # ===== 2.1 Autoevaluacion (B §2.1) — ancla en Programa Sede (corrección G) =====
    _dt("Autoevaluacion", [
        {"fieldname":"codigo","fieldtype":"Data","label":"Código","reqd":1,"unique":1,"in_list_view":1},
        {"fieldname":"titulo","fieldtype":"Data","label":"Título","in_list_view":1},
        {"fieldname":"marco_normativo","fieldtype":"Link","label":"Marco normativo","options":"Marco Normativo","reqd":1,"in_standard_filter":1},
        {"fieldname":"programa_sede","fieldtype":"Link","label":"Programa-Sede","options":"Programa Sede","in_standard_filter":1},
        {"fieldname":"periodo_academico","fieldtype":"Link","label":"Periodo académico","options":"Periodo Academico","in_standard_filter":1},
        {"fieldname":"alcance","fieldtype":"Text","label":"Alcance"},
        {"fieldname":"estado","fieldtype":"Select","label":"Estado",
         "options":"Planificada\nEn curso\nEn revision\nConsolidada\nCerrada","default":"Planificada","in_list_view":1,"in_standard_filter":1},
        {"fieldname":"resultado_vigencia","fieldtype":"Select","label":"Resultado de vigencia",
         "options":"\nEn proceso\nAcreditado 3 años\nAcreditado 6 años\nAcreditado 8 años"},
        {"fieldname":"puntaje_excelencia","fieldtype":"Int","label":"Puntaje de excelencia"},
        {"fieldname":"responsable","fieldtype":"Link","label":"Responsable","options":"User"},
        {"fieldname":"fecha_inicio","fieldtype":"Date","label":"Fecha de inicio"},
        {"fieldname":"fecha_cierre","fieldtype":"Date","label":"Fecha de cierre"},
    ], autoname="field:codigo", title_field="titulo",
       search_fields="titulo,marco_normativo,programa_sede")

    # ===== 2.2 Valoracion Criterio (B §2.2) =====
    _dt("Valoracion Criterio", [
        {"fieldname":"autoevaluacion","fieldtype":"Link","label":"Autoevaluación","options":"Autoevaluacion","reqd":1,"in_standard_filter":1},
        {"fieldname":"criterio","fieldtype":"Link","label":"Criterio","options":"Elemento Marco","reqd":1,"in_list_view":1},
        {"fieldname":"cumple","fieldtype":"Select","label":"Cumple",
         "options":"Cumple\nCumple parcial\nNo cumple\nNo aplica","in_list_view":1,"in_standard_filter":1},
        {"fieldname":"observacion","fieldtype":"Text","label":"Observación"},
        {"fieldname":"estado","fieldtype":"Select","label":"Estado",
         "options":"Pendiente\nEn analisis\nValorado\nRevisado","default":"Pendiente","in_standard_filter":1},
        {"fieldname":"valorado_por","fieldtype":"Link","label":"Valorado por","options":"User"},
        {"fieldname":"fecha","fieldtype":"Datetime","label":"Fecha"},
    ], autoname="hash", title_field="criterio")

    # ===== 2.3 Valoracion Estandar (B §2.3) — nivel oficial NL/L/LP (permlevel:1) =====
    _dt("Valoracion Estandar", [
        {"fieldname":"autoevaluacion","fieldtype":"Link","label":"Autoevaluación","options":"Autoevaluacion","reqd":1,"in_standard_filter":1},
        {"fieldname":"elemento_marco","fieldtype":"Link","label":"Estándar (elemento del marco)","options":"Elemento Marco","reqd":1,"in_list_view":1},
        {"fieldname":"nivel","fieldtype":"Link","label":"Nivel (NL/L/LP)","options":"Nivel Escala","permlevel":1,"in_list_view":1},
        {"fieldname":"calculado_auto","fieldtype":"Check","label":"Calculado automáticamente"},
        {"fieldname":"justificacion","fieldtype":"Text","label":"Justificación"},
        {"fieldname":"estado","fieldtype":"Select","label":"Estado",
         "options":"Borrador\nPropuesto\nAprobado","default":"Borrador","in_standard_filter":1},
        {"fieldname":"aprobado_por","fieldtype":"Link","label":"Aprobado por","options":"User"},
    ], autoname="hash", title_field="elemento_marco")

    # ===== 2.4 Evidencia (B §2.4) + programa_sede/periodo + origen polimórfico opcional (E C4) =====
    _dt("Evidencia", [
        {"fieldname":"codigo","fieldtype":"Data","label":"Código","reqd":1,"unique":1,"in_list_view":1},
        {"fieldname":"titulo","fieldtype":"Data","label":"Título","reqd":1,"in_list_view":1},
        {"fieldname":"descripcion","fieldtype":"Text","label":"Descripción"},
        {"fieldname":"tipo","fieldtype":"Select","label":"Tipo",
         "options":"Documento\nEnlace\nRegistro\nDataset\nActa","in_standard_filter":1},
        {"fieldname":"almacenamiento_uri","fieldtype":"Data","label":"URI de almacenamiento (MinIO)"},
        {"fieldname":"mime","fieldtype":"Data","label":"MIME"},
        {"fieldname":"tamano","fieldtype":"Int","label":"Tamaño (bytes)"},
        {"fieldname":"hash_sha256","fieldtype":"Data","label":"Hash SHA-256"},
        {"fieldname":"documento_controlado","fieldtype":"Link","label":"Documento controlado","options":"Documento Controlado"},
        {"fieldname":"programa_sede","fieldtype":"Link","label":"Programa-Sede","options":"Programa Sede","in_standard_filter":1},
        {"fieldname":"periodo_academico","fieldtype":"Link","label":"Periodo académico","options":"Periodo Academico","in_standard_filter":1},
        {"fieldname":"unidad_organica","fieldtype":"Link","label":"Unidad orgánica","options":"Unidad Organica"},
        {"fieldname":"estado","fieldtype":"Select","label":"Estado",
         "options":"Pendiente\nValida\nObservada\nSubsanada\nVencida","default":"Pendiente","in_list_view":1,"in_standard_filter":1},
        {"fieldname":"vigencia_desde","fieldtype":"Date","label":"Vigencia desde"},
        {"fieldname":"vigencia_hasta","fieldtype":"Date","label":"Vigencia hasta"},
        {"fieldname":"origen_doctype","fieldtype":"Link","label":"Tipo de origen","options":"DocType"},
        {"fieldname":"origen_id","fieldtype":"Dynamic Link","label":"Origen","options":"origen_doctype"},
        {"fieldname":"cargado_por","fieldtype":"Link","label":"Cargado por","options":"User"},
        {"fieldname":"fecha_carga","fieldtype":"Datetime","label":"Fecha de carga"},
    ], autoname="field:codigo", title_field="titulo",
       search_fields="titulo,codigo")

    # ===== 2.5 Trazabilidad (B §2.5) — tabla estrella RNF09: evidencia + elemento_marco + proceso =====
    _dt("Trazabilidad", [
        {"fieldname":"evidencia","fieldtype":"Link","label":"Evidencia","options":"Evidencia","reqd":1,"in_list_view":1,"in_standard_filter":1},
        {"fieldname":"elemento_marco","fieldtype":"Link","label":"Criterio / elemento del marco","options":"Elemento Marco","in_list_view":1,"in_standard_filter":1},
        {"fieldname":"proceso","fieldtype":"Link","label":"Proceso","options":"Proceso","in_standard_filter":1},
        {"fieldname":"tipo_vinculo","fieldtype":"Select","label":"Tipo de vínculo",
         "options":"Cumple\nSoporta\nParcial"},
        {"fieldname":"origen","fieldtype":"Select","label":"Origen",
         "options":"Directo\nPropagado por crosswalk","default":"Directo","in_standard_filter":1},
        {"fieldname":"vigencia_desde","fieldtype":"Date","label":"Vigencia desde"},
        {"fieldname":"vigencia_hasta","fieldtype":"Date","label":"Vigencia hasta"},
    ], autoname="hash", title_field="evidencia")

    # ===== 2.6 Valor Indicador (B §2.6) =====
    _dt("Valor Indicador", [
        {"fieldname":"indicador","fieldtype":"Link","label":"Indicador","options":"Indicador","reqd":1,"in_list_view":1,"in_standard_filter":1},
        {"fieldname":"autoevaluacion","fieldtype":"Link","label":"Autoevaluación","options":"Autoevaluacion"},
        {"fieldname":"periodo_academico","fieldtype":"Link","label":"Periodo académico","options":"Periodo Academico","in_standard_filter":1},
        {"fieldname":"programa_sede","fieldtype":"Link","label":"Programa-Sede","options":"Programa Sede","in_standard_filter":1},
        {"fieldname":"unidad_organica","fieldtype":"Link","label":"Unidad orgánica","options":"Unidad Organica"},
        {"fieldname":"valor_num","fieldtype":"Float","label":"Valor numérico","in_list_view":1},
        {"fieldname":"valor_texto","fieldtype":"Data","label":"Valor (texto)"},
        {"fieldname":"calculado","fieldtype":"Check","label":"Calculado"},
        {"fieldname":"fuente","fieldtype":"Data","label":"Fuente del dato"},
        {"fieldname":"fecha","fieldtype":"Datetime","label":"Fecha"},
        {"fieldname":"registrado_por","fieldtype":"Link","label":"Registrado por","options":"User"},
    ], autoname="hash", title_field="indicador")

    # ===== 3.1 Documento Controlado (B §3.1) — M03 control documental (Mayan) =====
    _dt("Documento Controlado", [
        {"fieldname":"codigo","fieldtype":"Data","label":"Código","reqd":1,"unique":1,"in_list_view":1},
        {"fieldname":"titulo","fieldtype":"Data","label":"Título","reqd":1,"in_list_view":1},
        {"fieldname":"version","fieldtype":"Data","label":"Versión","in_list_view":1},
        {"fieldname":"almacenamiento_uri","fieldtype":"Data","label":"URI de almacenamiento"},
        {"fieldname":"mayan_document_id","fieldtype":"Data","label":"ID documento en Mayan"},
        {"fieldname":"proceso","fieldtype":"Link","label":"Proceso","options":"Proceso","in_standard_filter":1},
        {"fieldname":"estado","fieldtype":"Select","label":"Estado",
         "options":"Borrador\nEn revision\nAprobado\nPublicado\nObsoleto\nObservado","default":"Borrador","in_list_view":1,"in_standard_filter":1},
        {"fieldname":"elaborado_por","fieldtype":"Link","label":"Elaborado por","options":"User"},
        {"fieldname":"revisado_por","fieldtype":"Link","label":"Revisado por","options":"User"},
        {"fieldname":"aprobado_por","fieldtype":"Link","label":"Aprobado por","options":"User"},
        {"fieldname":"fecha_publicacion","fieldtype":"Date","label":"Fecha de publicación"},
        {"fieldname":"reemplaza_a","fieldtype":"Link","label":"Reemplaza a","options":"Documento Controlado"},
    ], autoname="field:codigo", title_field="titulo",
       search_fields="titulo,codigo")

    # ===== 2.1(E) No Conformidad — origen polimórfico (ejemplo B del contrato · E §2.1/§11) =====
    _dt("No Conformidad", [
        {"fieldname":"titulo","fieldtype":"Data","label":"Título","reqd":1,"in_list_view":1},
        {"fieldname":"origen_doctype","fieldtype":"Link","label":"Tipo de documento origen","options":"DocType"},
        {"fieldname":"origen_id","fieldtype":"Dynamic Link","label":"Documento origen","options":"origen_doctype"},
        {"fieldname":"origen_tipo","fieldtype":"Select","label":"Origen",
         "options":"Autoevaluacion\nAuditoria\nQueja/Reclamo\nIndicador fuera de meta\nRevision por direccion\nRiesgo materializado\nIncumplimiento a ente\nProceso\nOtra","in_standard_filter":1},
        {"fieldname":"tipo","fieldtype":"Select","label":"Tipo",
         "options":"No conformidad mayor\nNo conformidad menor\nObservacion\nOportunidad de mejora","in_list_view":1,"in_standard_filter":1},
        {"fieldname":"descripcion","fieldtype":"Text","label":"Descripción"},
        {"fieldname":"requisito_incumplido","fieldtype":"Small Text","label":"Requisito incumplido"},
        {"fieldname":"unidad_organica","fieldtype":"Link","label":"Unidad orgánica","options":"Unidad Organica"},
        {"fieldname":"proceso","fieldtype":"Link","label":"Proceso","options":"Proceso"},
        {"fieldname":"programa_sede","fieldtype":"Link","label":"Programa-Sede","options":"Programa Sede","in_standard_filter":1},
        {"fieldname":"criterio","fieldtype":"Link","label":"Criterio (elemento del marco)","options":"Elemento Marco"},
        {"fieldname":"severidad","fieldtype":"Select","label":"Severidad",
         "options":"Critica\nAlta\nMedia\nBaja","in_standard_filter":1},
        {"fieldname":"requiere_analisis_causa","fieldtype":"Check","label":"Requiere análisis de causa"},
        {"fieldname":"analisis_causa","fieldtype":"Text","label":"Análisis de causa raíz"},
        {"fieldname":"correccion_inmediata","fieldtype":"Text","label":"Corrección inmediata (contención)"},
        {"fieldname":"plan_mejora","fieldtype":"Link","label":"Plan de mejora","options":"Plan Mejora"},
        {"fieldname":"estado","fieldtype":"Select","label":"Estado",
         "options":"Abierta\nEn analisis\nEn tratamiento\nEn verificacion\nCerrada eficaz\nCerrada no eficaz","default":"Abierta","in_list_view":1,"in_standard_filter":1},
        {"fieldname":"responsable","fieldtype":"Link","label":"Responsable","options":"User"},
        {"fieldname":"fecha_deteccion","fieldtype":"Date","label":"Fecha de detección"},
        {"fieldname":"fecha_compromiso","fieldtype":"Date","label":"Fecha de compromiso (ETA)"},
        {"fieldname":"evidencia_cierre","fieldtype":"Link","label":"Evidencia de cierre","options":"Evidencia"},
        {"fieldname":"verificada_por","fieldtype":"Link","label":"Verificada por","options":"User"},
    ], autoname="format:NC-{YYYY}-{#####}", title_field="titulo",
       search_fields="titulo,origen_tipo")

    # ===== 2.7(B)/2.2(E) Hallazgo — especializado (Fortaleza/Debilidad/OM) + escala a NC =====
    _dt("Hallazgo", [
        {"fieldname":"codigo","fieldtype":"Data","label":"Código","reqd":1,"unique":1,"in_list_view":1},
        {"fieldname":"tipo","fieldtype":"Select","label":"Tipo",
         "options":"Fortaleza\nDebilidad\nOportunidad de mejora","in_list_view":1,"in_standard_filter":1},
        {"fieldname":"origen","fieldtype":"Select","label":"Origen",
         "options":"Autoevaluacion\nAuditoria\nSupervision","in_standard_filter":1},
        {"fieldname":"criterio","fieldtype":"Link","label":"Criterio (elemento del marco)","options":"Elemento Marco","in_standard_filter":1},
        {"fieldname":"autoevaluacion","fieldtype":"Link","label":"Autoevaluación","options":"Autoevaluacion","in_standard_filter":1},
        {"fieldname":"proceso","fieldtype":"Link","label":"Proceso","options":"Proceso","in_standard_filter":1},
        {"fieldname":"descripcion","fieldtype":"Text","label":"Descripción"},
        {"fieldname":"unidad_organica","fieldtype":"Link","label":"Unidad orgánica","options":"Unidad Organica"},
        {"fieldname":"programa_sede","fieldtype":"Link","label":"Programa-Sede","options":"Programa Sede"},
        {"fieldname":"severidad","fieldtype":"Select","label":"Severidad",
         "options":"\nCritica\nAlta\nMedia\nBaja"},
        {"fieldname":"no_conformidad","fieldtype":"Link","label":"No conformidad","options":"No Conformidad"},
        {"fieldname":"escalado_a_nc","fieldtype":"Check","label":"Escalado a NC"},
        {"fieldname":"estado","fieldtype":"Select","label":"Estado",
         "options":"Abierto\nEn tratamiento\nVerificacion\nCerrado eficaz\nCerrado no eficaz","default":"Abierto","in_list_view":1,"in_standard_filter":1},
        {"fieldname":"detectado_por","fieldtype":"Link","label":"Detectado por","options":"User"},
        {"fieldname":"fecha","fieldtype":"Date","label":"Fecha"},
    ], autoname="field:codigo", title_field="codigo")

    # ===== 2.8(B)/2.3(E) Plan Mejora — origen polimórfico + autoevaluacion conservado =====
    _dt("Plan Mejora", [
        {"fieldname":"codigo","fieldtype":"Data","label":"Código","reqd":1,"unique":1,"in_list_view":1},
        {"fieldname":"titulo","fieldtype":"Data","label":"Título","in_list_view":1},
        {"fieldname":"origen_doctype","fieldtype":"Link","label":"Tipo de documento origen","options":"DocType"},
        {"fieldname":"origen_id","fieldtype":"Dynamic Link","label":"Documento origen","options":"origen_doctype"},
        {"fieldname":"autoevaluacion","fieldtype":"Link","label":"Autoevaluación","options":"Autoevaluacion","in_standard_filter":1},
        {"fieldname":"unidad_organica","fieldtype":"Link","label":"Unidad orgánica","options":"Unidad Organica"},
        {"fieldname":"periodo_academico","fieldtype":"Link","label":"Periodo académico","options":"Periodo Academico"},
        {"fieldname":"estado","fieldtype":"Select","label":"Estado",
         "options":"Borrador\nEn ejecucion\nCerrado","default":"Borrador","in_list_view":1,"in_standard_filter":1},
        {"fieldname":"responsable","fieldtype":"Link","label":"Responsable","options":"User"},
    ], autoname="field:codigo", title_field="titulo")

    # ===== 2.8(B)/2.4(E) Accion Mejora — CAPA: hallazgo + no_conformidad (ambos opcionales) =====
    _dt("Accion Mejora", [
        {"fieldname":"codigo","fieldtype":"Data","label":"Código","reqd":1,"unique":1,"in_list_view":1},
        {"fieldname":"plan_mejora","fieldtype":"Link","label":"Plan de mejora","options":"Plan Mejora","in_standard_filter":1},
        {"fieldname":"hallazgo","fieldtype":"Link","label":"Hallazgo","options":"Hallazgo","in_standard_filter":1},
        {"fieldname":"no_conformidad","fieldtype":"Link","label":"No conformidad","options":"No Conformidad","in_standard_filter":1},
        {"fieldname":"criterio","fieldtype":"Link","label":"Criterio (elemento del marco)","options":"Elemento Marco"},
        {"fieldname":"descripcion","fieldtype":"Text","label":"Descripción"},
        {"fieldname":"tipo","fieldtype":"Select","label":"Tipo",
         "options":"Correctiva\nPreventiva\nMejora","in_standard_filter":1},
        {"fieldname":"responsable","fieldtype":"Link","label":"Responsable","options":"User"},
        {"fieldname":"fecha_inicio","fieldtype":"Date","label":"Fecha de inicio"},
        {"fieldname":"fecha_compromiso","fieldtype":"Date","label":"Fecha de compromiso (ETA)"},
        {"fieldname":"avance_pct","fieldtype":"Int","label":"Avance (%)"},
        {"fieldname":"estado","fieldtype":"Select","label":"Estado",
         "options":"Planificada\nEn ejecucion\nEjecutada\nVerificada eficaz\nVerificada no eficaz","default":"Planificada","in_list_view":1,"in_standard_filter":1},
        {"fieldname":"evidencia_cierre","fieldtype":"Link","label":"Evidencia de cierre","options":"Evidencia"},
    ], autoname="field:codigo", title_field="codigo")

    # child de enlace para Table MultiSelect de Evidencia (Frappe exige child con Link)
    _dt("Evidencia Enlace", [
        {"fieldname":"evidencia","fieldtype":"Link","label":"Evidencia","options":"Evidencia","in_list_view":1,"reqd":1},
    ], istable=1)

    frappe.db.commit()
    print("f1_nucleo OK")
