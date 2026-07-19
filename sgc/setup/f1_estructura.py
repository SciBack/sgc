"""F1 estructura — crea los DocTypes del módulo `SGC Estructura` (config/estructura del SGC).

Grupo A1 del contrato F1-CONTRATO.md §3. Solo estructura: campos, links, child tables,
naming, permiso básico. SIN is_submittable, SIN Workflow. `estado` = Select. Idempotente.

Ejecutar (lo hace el orquestador, NO este agente):
    bench --site sgc.localhost execute sgc.setup.f1_estructura.run
"""
import frappe

MODULE = "SGC Estructura"


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
    # =========================================================================
    # 1) CHILD TABLES primero (istable=1, sin permissions ni autoname)
    # =========================================================================

    # Nivel Marco (hija de Marco Normativo) — define, por marco, sus niveles
    # jerárquicos y su orden (B §1.3). Es lo que hace configurable la profundidad.
    _dt("Nivel Marco", [
        {"fieldname": "nombre", "fieldtype": "Data", "label": "Nombre",
         "reqd": 1, "in_list_view": 1,
         "description": "Dimensión·Factor·Estándar·Criterio·Condición·Componente·Indicador"},
        {"fieldname": "profundidad", "fieldtype": "Int", "label": "Profundidad",
         "in_list_view": 1, "description": "1 = raíz del marco; ordena la jerarquía"},
        {"fieldname": "es_valorable", "fieldtype": "Check", "label": "Es valorable",
         "in_list_view": 1,
         "description": "Nivel que recibe el juicio oficial (Estándar en CONEAU, Indicador en CBC)"},
        {"fieldname": "es_hoja_evidenciable", "fieldtype": "Check",
         "label": "Es hoja evidenciable",
         "description": "Nivel contra el que se cuelgan evidencias (Criterio en CONEAU)"},
    ], istable=1)

    # Nivel Escala (hija de Escala Valoracion) — B §1.2 (ejemplo C del contrato)
    _dt("Nivel Escala", [
        {"fieldname": "codigo", "fieldtype": "Data", "label": "Código",
         "in_list_view": 1, "reqd": 1},
        {"fieldname": "sigla", "fieldtype": "Data", "label": "Sigla",
         "in_list_view": 1, "description": "NL·L·LP"},
        {"fieldname": "etiqueta", "fieldtype": "Data", "label": "Etiqueta",
         "in_list_view": 1},
        {"fieldname": "score", "fieldtype": "Int", "label": "Score",
         "in_list_view": 1, "description": "0/1/2 (del YAML CONEAU)"},
        {"fieldname": "orden", "fieldtype": "Int", "label": "Orden", "in_list_view": 1},
        {"fieldname": "es_aprobatorio", "fieldtype": "Check", "label": "Es aprobatorio"},
        {"fieldname": "definicion", "fieldtype": "Text", "label": "Definición",
         "description": "Definición textual oficial del nivel"},
    ], istable=1)

    # Indicador Criterio (child, N:M indicador↔elemento marco) — B §1.5 / contrato A1.
    # Tabla-puente materializada. Se declara como Child; el padre operativo
    # (Indicador) la referencia por Table.
    _dt("Indicador Criterio", [
        {"fieldname": "indicador", "fieldtype": "Link", "label": "Indicador",
         "options": "Indicador", "in_list_view": 1, "reqd": 1},
        {"fieldname": "elemento_marco", "fieldtype": "Link", "label": "Elemento marco (criterio)",
         "options": "Elemento Marco", "in_list_view": 1, "reqd": 1},
    ], istable=1)

    # =========================================================================
    # 2) DOCTYPES PADRE / normales / tree
    # =========================================================================

    # ----- Escala Valoracion (Doc) — B §1.2 (ejemplo C del contrato) -----
    _dt("Escala Valoracion", [
        {"fieldname": "codigo", "fieldtype": "Data", "label": "Código",
         "reqd": 1, "unique": 1, "in_list_view": 1},
        {"fieldname": "nombre", "fieldtype": "Data", "label": "Nombre", "reqd": 1,
         "in_list_view": 1},
        {"fieldname": "tipo", "fieldtype": "Select", "label": "Tipo",
         "options": "ordinal\nbinaria\nporcentual", "in_list_view": 1},
        {"fieldname": "min_score", "fieldtype": "Int", "label": "Score mínimo"},
        {"fieldname": "max_score", "fieldtype": "Int", "label": "Score máximo"},
        {"fieldname": "niveles", "fieldtype": "Table", "label": "Niveles",
         "options": "Nivel Escala"},
    ], autoname="field:codigo", title_field="nombre")

    # ----- Marco Normativo (Doc) — B §1.1 -----
    _dt("Marco Normativo", [
        {"fieldname": "codigo", "fieldtype": "Data", "label": "Código",
         "reqd": 1, "unique": 1, "in_list_view": 1,
         "description": "CONEAU-PROG-2025, CBC-SUNEDU-2026, ISO-21001…"},
        {"fieldname": "nombre", "fieldtype": "Data", "label": "Nombre", "reqd": 1,
         "in_list_view": 1},
        {"fieldname": "ente", "fieldtype": "Select", "label": "Ente",
         "options": "SINEACE\nSUNEDU\nISO\nINTERNACIONAL", "in_list_view": 1,
         "in_standard_filter": 1},
        {"fieldname": "version", "fieldtype": "Data", "label": "Versión",
         "in_list_view": 1, "description": "2025, 2026 — permite convivencia de versiones"},
        {"fieldname": "vigente_desde", "fieldtype": "Date", "label": "Vigente desde"},
        {"fieldname": "vigente_hasta", "fieldtype": "Date", "label": "Vigente hasta"},
        {"fieldname": "estado", "fieldtype": "Select", "label": "Estado",
         "options": "borrador\nvigente\nderogado", "default": "borrador",
         "in_standard_filter": 1},
        {"fieldname": "escala_valoracion", "fieldtype": "Link", "label": "Escala de valoración",
         "options": "Escala Valoracion"},
        {"fieldname": "niveles", "fieldtype": "Table", "label": "Niveles del marco",
         "options": "Nivel Marco"},
        {"fieldname": "reglas_vigencia", "fieldtype": "JSON", "label": "Reglas de vigencia",
         "description": "Tabla de vigencia del ente (CONEAU: en_proceso/3a/6a/8a)"},
        {"fieldname": "nota_normativa", "fieldtype": "Text", "label": "Nota normativa",
         "description": "Fuente oficial (PDF, RCD, pp.)"},
    ], autoname="field:codigo", title_field="nombre")

    # ----- Elemento Marco (Tree) — B §1.4 ⭐. Nodo recursivo estándar→criterio -----
    _dt("Elemento Marco", [
        {"fieldname": "codigo", "fieldtype": "Data", "label": "Código",
         "reqd": 1, "in_list_view": 1,
         "description": "E1, 1.1, CBC-I, CBC-I.2 — código oficial"},
        {"fieldname": "denominacion", "fieldtype": "Data", "label": "Denominación",
         "in_list_view": 1},
        {"fieldname": "marco_normativo", "fieldtype": "Link", "label": "Marco normativo",
         "options": "Marco Normativo", "reqd": 1, "in_standard_filter": 1},
        {"fieldname": "nivel", "fieldtype": "Data", "label": "Nivel",
         "description": "Nombre del nivel (Estándar, Criterio…); denormalizado de Nivel Marco"},
        {"fieldname": "tipo", "fieldtype": "Select", "label": "Tipo",
         "options": "Dimension\nFactor\nEstandar\nCriterio\nCondicion\nComponente\nIndicador",
         "in_standard_filter": 1},
        {"fieldname": "texto_oficial", "fieldtype": "Text", "label": "Texto oficial",
         "description": "Descripción literal (del description del YAML)"},
        {"fieldname": "orden", "fieldtype": "Int", "label": "Orden"},
        {"fieldname": "peso", "fieldtype": "Float", "label": "Peso",
         "description": "Ponderación si el modelo la usa (CONEAU no pondera)"},
        {"fieldname": "es_valorable", "fieldtype": "Check", "label": "Es valorable",
         "description": "Denormalizado del nivel, para queries"},
        {"fieldname": "nota_normativa", "fieldtype": "Text", "label": "Nota normativa",
         "description": "Fuente + página (del annotation del YAML)"},
        {"fieldname": "atributos", "fieldtype": "JSON", "label": "Atributos",
         "description": "Lo variable por marco (obligatoriedad, glosa, referencia legal)"},
        {"fieldname": "is_group", "fieldtype": "Check", "label": "Es grupo"},
        {"fieldname": "parent_elemento_marco", "fieldtype": "Link", "label": "Elemento padre",
         "options": "Elemento Marco"},
    ], is_tree=1, autoname="field:codigo", title_field="denominacion")

    # ----- Indicador (Doc) — B §1.5. Polimórfico (categoria incl. Proceso + Link proceso) -----
    _dt("Indicador", [
        {"fieldname": "codigo", "fieldtype": "Data", "label": "Código",
         "reqd": 1, "unique": 1, "in_list_view": 1, "description": "ID1…"},
        {"fieldname": "nombre", "fieldtype": "Data", "label": "Nombre", "reqd": 1,
         "in_list_view": 1},
        {"fieldname": "marco_normativo", "fieldtype": "Link", "label": "Marco normativo",
         "options": "Marco Normativo", "in_standard_filter": 1},
        {"fieldname": "categoria", "fieldtype": "Select", "label": "Categoría",
         "options": "Acreditacion\nGestion\nProceso\nSatisfaccion\nOtra",
         "in_standard_filter": 1,
         "description": "Polimórfico: incluye Proceso (indicador de proceso E/C/S)"},
        # Link opcional a Proceso (target en B4/SGC Procesos). Se declara igual;
        # existirá al integrar. Sin este link no se crea un 'Indicador Proceso' aparte.
        {"fieldname": "proceso", "fieldtype": "Link", "label": "Proceso",
         "options": "Proceso",
         "depends_on": "eval:doc.categoria=='Proceso'",
         "description": "Solo si categoria=Proceso (polimórfico → B4 SGC Procesos)"},
        {"fieldname": "criterios", "fieldtype": "Table", "label": "Criterios que tributa",
         "options": "Indicador Criterio",
         "description": "N:M indicador↔elemento marco (tabla-puente)"},
    ], autoname="field:codigo", title_field="nombre")

    # ----- Ficha Indicador (Doc) — B §1.5 (1:1 con Indicador o ElementoMarco-indicador) -----
    # + contrato de datos: dominio_dato (D1..D8) + fuente_autoritativa.
    _dt("Ficha Indicador", [
        {"fieldname": "indicador", "fieldtype": "Link", "label": "Indicador",
         "options": "Indicador", "in_list_view": 1, "unique": 1,
         "description": "Ficha 1:1 con Indicador (o con ElementoMarco-indicador en CBC)"},
        {"fieldname": "elemento_marco", "fieldtype": "Link",
         "label": "Elemento marco (indicador CBC)", "options": "Elemento Marco",
         "description": "Alternativa: la ficha cuelga del nodo evaluable en CBC"},
        {"fieldname": "objetivo", "fieldtype": "Text", "label": "Objetivo",
         "description": "OBJETIVO DE MEDICIÓN: …"},
        {"fieldname": "tipo_valor", "fieldtype": "Select", "label": "Tipo de valor",
         "options": "porcentaje\nnumerico\nratio\nbooleano\nescala_satisfaccion\ntexto"},
        {"fieldname": "formula", "fieldtype": "Text", "label": "Fórmula",
         "description": "FORMA DE CÁLCULO: (EPSC/EPR)×100"},
        {"fieldname": "variables", "fieldtype": "JSON", "label": "Variables",
         "description": "VARIABLES: EPSC=…, EPR=…"},
        {"fieldname": "unidad", "fieldtype": "Data", "label": "Unidad",
         "description": "%, ratio, n.º"},
        {"fieldname": "valor_referencial", "fieldtype": "Float", "label": "Valor referencial",
         "description": "Umbral (ID1 ≥ 60%)"},
        {"fieldname": "margen_error", "fieldtype": "Float", "label": "Margen de error",
         "default": "3", "description": "±3% por defecto (escala oficial §9.1)"},
        {"fieldname": "regla_evolucion", "fieldtype": "Check", "label": "Regla de evolución",
         "description": "Si aplica evolución positiva n-1→n como aceptable"},
        {"fieldname": "interpretacion", "fieldtype": "Text", "label": "Interpretación"},
        {"fieldname": "frecuencia", "fieldtype": "Select", "label": "Frecuencia",
         "options": "anual\nsemestral\npor_promocion"},
        {"fieldname": "fuente_dato", "fieldtype": "Data", "label": "Fuente de dato",
         "description": "LAMB · Koha · DSpace · encuesta · manual"},
        {"fieldname": "responsable", "fieldtype": "Link", "label": "Responsable",
         "options": "User", "description": "Responsable del indicador (data steward)"},
        {"fieldname": "notas", "fieldtype": "Text", "label": "Notas",
         "description": "Condiciones muestrales (≥70% de matriculados)"},
        # --- Contrato de datos ---
        {"fieldname": "dominio_dato", "fieldtype": "Select", "label": "Dominio de dato",
         "options": "D1\nD2\nD3\nD4\nD5\nD6\nD7\nD8", "in_standard_filter": 1,
         "description": "Dominio del dato (contrato de datos: matrícula, egresados…)"},
        {"fieldname": "fuente_autoritativa", "fieldtype": "Data", "label": "Fuente autoritativa",
         "description": "Sistema fuente de verdad (Oracle LAMB, Koha…)"},
    ], title_field="indicador")

    # =========================================================================
    # 3) ESTRUCTURA INSTITUCIONAL (🟩) — organigrama, programa, sede, periodo
    # =========================================================================

    # ----- Unidad Organica (Tree) — B §4.1 + G fix #3 (Sede es un nodo/registro) -----
    # Ejemplo A del contrato. `tipo` Select incluye `Sede` (Sede NO es DocType aparte).
    _dt("Unidad Organica", [
        {"fieldname": "codigo", "fieldtype": "Data", "label": "Código",
         "reqd": 1, "unique": 1, "in_list_view": 1},
        {"fieldname": "nombre", "fieldtype": "Data", "label": "Nombre",
         "reqd": 1, "in_list_view": 1},
        {"fieldname": "tipo", "fieldtype": "Select", "label": "Tipo",
         "options": "Universidad\nSede\nVicerrectorado\nFacultad\nEscuela\nDireccion\nOficina\nUnidad",
         "in_list_view": 1, "in_standard_filter": 1,
         "description": "Sede es un registro de Unidad Organica (fix G #3), no un DocType aparte"},
        {"fieldname": "sede", "fieldtype": "Select", "label": "Sede (denormalizado)",
         "options": "\nLima\nJuliaca\nTarapoto",
         "description": "Denormalizado para reporting; la verdad de scoping es la posición en el árbol"},
        {"fieldname": "es_campus", "fieldtype": "Check", "label": "Es campus"},
        {"fieldname": "is_group", "fieldtype": "Check", "label": "Es grupo"},
        {"fieldname": "parent_unidad_organica", "fieldtype": "Link", "label": "Unidad padre",
         "options": "Unidad Organica"},
    ], is_tree=1, autoname="field:codigo", title_field="nombre")

    # ----- Programa (Doc) — B §4.2. El programa académico canónico (fix G #2) -----
    _dt("Programa", [
        {"fieldname": "codigo", "fieldtype": "Data", "label": "Código",
         "reqd": 1, "unique": 1, "in_list_view": 1},
        {"fieldname": "nombre", "fieldtype": "Data", "label": "Nombre",
         "reqd": 1, "in_list_view": 1},
        {"fieldname": "facultad", "fieldtype": "Link", "label": "Facultad",
         "options": "Unidad Organica"},
        {"fieldname": "escuela", "fieldtype": "Link", "label": "Escuela",
         "options": "Unidad Organica"},
        {"fieldname": "nivel", "fieldtype": "Select", "label": "Nivel",
         "options": "pregrado\nposgrado", "in_standard_filter": 1},
        {"fieldname": "estado", "fieldtype": "Select", "label": "Estado",
         "options": "activo\ninactivo", "default": "activo"},
    ], autoname="field:codigo", title_field="nombre")

    # ----- Programa Sede (Doc) — corrección G fix #2 ⭐. Ancla de scoping -----
    # La Autoevaluacion y objetos transaccionales anclan AQUÍ, no en Programa.
    _dt("Programa Sede", [
        {"fieldname": "codigo", "fieldtype": "Data", "label": "Código",
         "reqd": 1, "unique": 1, "in_list_view": 1,
         "description": "Ej. ENF-LIMA — ancla de scoping por RBAC"},
        {"fieldname": "programa", "fieldtype": "Link", "label": "Programa",
         "options": "Programa", "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
        {"fieldname": "sede", "fieldtype": "Link", "label": "Sede",
         "options": "Unidad Organica", "reqd": 1, "in_list_view": 1, "in_standard_filter": 1,
         "description": "Nodo Unidad Organica con tipo=Sede"},
        {"fieldname": "escuela", "fieldtype": "Link", "label": "Escuela",
         "options": "Unidad Organica",
         "description": "Dirección de Escuela Profesional de esa sede"},
        {"fieldname": "licencia", "fieldtype": "Data", "label": "Licencia"},
        {"fieldname": "estado", "fieldtype": "Select", "label": "Estado",
         "options": "activo\nsuspendido\ninactivo", "default": "activo",
         "in_standard_filter": 1},
    ], autoname="field:codigo", title_field="codigo")

    # ----- Periodo Academico (Doc) — B §4.3. Ancla temporal -----
    _dt("Periodo Academico", [
        {"fieldname": "codigo", "fieldtype": "Data", "label": "Código",
         "reqd": 1, "unique": 1, "in_list_view": 1, "description": "2026-I"},
        {"fieldname": "anio", "fieldtype": "Int", "label": "Año", "in_list_view": 1},
        {"fieldname": "semestre", "fieldtype": "Select", "label": "Semestre",
         "options": "\nI\nII", "in_list_view": 1},
        {"fieldname": "fecha_inicio", "fieldtype": "Date", "label": "Fecha de inicio"},
        {"fieldname": "fecha_fin", "fieldtype": "Date", "label": "Fecha de fin"},
        {"fieldname": "estado", "fieldtype": "Select", "label": "Estado",
         "options": "abierto\ncerrado", "default": "abierto", "in_standard_filter": 1},
    ], autoname="field:codigo", title_field="codigo")

    frappe.db.commit()
    print("f1_estructura OK")
