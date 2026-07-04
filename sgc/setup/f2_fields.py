"""F2 fields — añade a los DocTypes F1 los campos de scoring de la rama de agosto.

Contrato: F2-CONTRATO.md §1. Añade, de forma idempotente:
  - Valoracion Criterio : cumple (Select), debilidad (Text), comentario (Text)
  - Valoracion Estandar : nivel_propuesto (Select NL/L/LP, read_only), confirmado (Check)
  - Autoevaluacion      : vigencia_propuesta (Select, read_only), avance_pct (Percent, read_only)

`Valoracion Estandar.nivel` (Link a Nivel Escala, permlevel 1) sigue siendo el nivel OFICIAL
confirmado por el humano. El motor (scoring.py) nunca lo escribe: solo escribe `nivel_propuesto`.

Ejecutar (lo hace el orquestador, NO este agente):
    bench --site sgc.localhost execute sgc.setup.f2_fields.run
"""
import frappe

# fieldname -> definición de campo a AÑADIR, por DocType.
# `insert_after` ancla el campo en un fieldname existente del DocType F1.
CAMPOS = {
    "Valoracion Criterio": [
        {
            "fieldname": "cumple",
            "fieldtype": "Select",
            "label": "Cumple",
            # Juicio de campo del contrato §1. NOTA: el DocType F1 ya trae `cumple`
            # con opciones "Cumple / Cumple parcial / No cumple / No aplica"; si ya
            # existe NO se re-añade (idempotencia), y el motor tolera ambos literales
            # ("Cumple parcial" == "Cumple con debilidad"). [VERIFICAR con Calidad]
            "options": "Cumple\nCumple con debilidad\nNo cumple",
            "in_list_view": 1,
            "in_standard_filter": 1,
            "insert_after": "criterio",
        },
        {
            "fieldname": "debilidad",
            "fieldtype": "Text",
            "label": "Debilidad / OM",
            "description": "Descripción de la debilidad u oportunidad de mejora, si aplica.",
            "insert_after": "cumple",
        },
        {
            "fieldname": "comentario",
            "fieldtype": "Text",
            "label": "Comentario (sustento)",
            "description": "Sustento del juicio del criterio.",
            "insert_after": "debilidad",
        },
    ],
    "Valoracion Estandar": [
        {
            "fieldname": "nivel_propuesto",
            "fieldtype": "Select",
            "label": "Nivel propuesto (motor)",
            "options": "\nNL\nL\nLP",
            "read_only": 1,
            "in_list_view": 1,
            "description": "Lo propone el motor de scoring. El nivel oficial (`nivel`) lo "
                           "confirma el humano tras revisar la evolución de los indicadores (±3%).",
            "insert_after": "nivel",
        },
        {
            "fieldname": "confirmado",
            "fieldtype": "Check",
            "label": "Confirmado por humano",
            "default": "0",
            "description": "El humano confirmó el `nivel` oficial (permlevel 1).",
            "insert_after": "nivel_propuesto",
        },
    ],
    "Autoevaluacion": [
        {
            "fieldname": "vigencia_propuesta",
            "fieldtype": "Select",
            "label": "Vigencia propuesta (motor)",
            "options": "\nEn proceso\nAcreditado 3 anios\nAcreditado 6 anios\nAcreditado 8 anios",
            "read_only": 1,
            "description": "Propuesta por el motor sobre los niveles CONFIRMADOS de los 10 "
                           "estándares (Tabla 9). El `resultado_vigencia` oficial lo fija el humano.",
            "insert_after": "resultado_vigencia",
        },
        {
            "fieldname": "avance_pct",
            "fieldtype": "Percent",
            "label": "Avance (%)",
            "read_only": 1,
            "description": "% de criterios valorados sobre el total de criterios del marco.",
            "insert_after": "vigencia_propuesta",
        },
    ],
}


def _existe_field(doctype, fieldname):
    doc = frappe.get_doc("DocType", doctype)
    return any(f.fieldname == fieldname for f in doc.fields)


def run():
    frappe.flags.in_patch = True
    frappe.flags.in_fixtures = True

    resumen = {"anadidos": [], "omitidos": []}

    for doctype, campos in CAMPOS.items():
        if not frappe.db.exists("DocType", doctype):
            resumen["omitidos"].append(f"{doctype} (DocType inexistente)")
            continue

        doc = frappe.get_doc("DocType", doctype)
        existentes = {f.fieldname for f in doc.fields}
        cambio = False

        for campo in campos:
            fname = campo["fieldname"]
            if fname in existentes:
                resumen["omitidos"].append(f"{doctype}.{fname} (ya existe)")
                continue
            doc.append("fields", campo)
            existentes.add(fname)
            resumen["anadidos"].append(f"{doctype}.{fname}")
            cambio = True

        if cambio:
            doc.save(ignore_permissions=True)

    frappe.db.commit()

    print("F2 fields — añadidos:", resumen["anadidos"])
    print("F2 fields — omitidos:", resumen["omitidos"])
    return resumen
