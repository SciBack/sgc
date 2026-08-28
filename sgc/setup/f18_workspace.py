# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

"""Crea el Workspace **nativo** del SGC — el panel de inicio del Desk.

Por qué existe: hasta ahora el panel de inicio se armaba a mano en la UI con un
bloque HTML a medida ("SGC Inicio"). Eso no vivía en el código, así que una
instalación limpia nacía sin panel y la home del Desk salía en blanco. Aquí se
declara el workspace con piezas NATIVAS de Frappe (shortcuts + cards + content),
de modo que se cree solo al instalar y se muestre a cualquier usuario con acceso
al Desk, sin depender de estado manual ni de la SPA.

Idempotente: si el workspace ya existe se recrea, de forma que un redeploy
actualiza el panel a esta definición.
"""

import json

import frappe

WS = "SGC"

# Accesos rápidos (lo que se usa a diario). (etiqueta, doctype)
SHORTCUTS = [
    ("Documentos", "Documento Controlado"),
    ("Evidencias", "Evidencia"),
    ("Autoevaluación", "Autoevaluacion"),
    ("Hallazgos", "Hallazgo"),
    ("Riesgos", "Riesgo"),
    ("Auditorías", "Auditoria"),
]

# Tarjetas por área. (título de la tarjeta, [doctypes])
CARDS = [
    ("Gestión documental", ["Documento Controlado", "Evidencia", "Trazabilidad"]),
    ("Autoevaluación", ["Autoevaluacion", "Valoracion Criterio", "Valoracion Estandar", "Valor Indicador"]),
    ("Mejora continua", ["Hallazgo", "No Conformidad", "Plan Mejora", "Accion Mejora"]),
    ("Auditoría", ["Programa Auditoria", "Auditoria", "Hallazgo Auditoria", "Informe Auditoria", "Revision Direccion"]),
    ("Riesgos y obligaciones", ["Riesgo", "Tratamiento Riesgo", "Matriz Riesgo", "Evaluacion Riesgo", "Obligacion Ente", "Entrega Obligacion"]),
    ("Procesos", ["Proceso", "Procedimiento", "Ficha Caracterizacion Proceso", "Informe Cumplimiento"]),
    ("Gobierno de la calidad", ["Politica Calidad", "Objetivo Calidad", "Comite", "Reunion", "Acuerdo", "Instrumento", "Aplicacion Instrumento"]),
    ("Marcos e indicadores", ["Marco Normativo", "Elemento Marco", "Indicador", "Ficha Indicador", "Escala Valoracion"]),
    ("Estructura", ["Unidad Organica", "Programa", "Programa Sede", "Periodo Academico"]),
]


def _contenido():
    """El layout del área central: cabecera + accesos + cabecera + tarjetas.

    Son bloques del editor nativo de Frappe (shortcut / card / header). No es HTML
    a medida: es lo mismo que genera la UI cuando se arma un workspace a mano.
    """
    b = [{"id": "hdr_a", "type": "header",
          "data": {"text": "Sistema de Gestión de la Calidad", "col": 12}}]
    for i, (label, _dt) in enumerate(SHORTCUTS):
        b.append({"id": f"sc{i}", "type": "shortcut",
                  "data": {"shortcut_name": label, "col": 3}})
    b.append({"id": "hdr_b", "type": "header", "data": {"text": "Módulos", "col": 12}})
    for i, (card, _items) in enumerate(CARDS):
        b.append({"id": f"cd{i}", "type": "card", "data": {"card_name": card, "col": 4}})
    return json.dumps(b, ensure_ascii=False)


def run():
    # Solo doctypes que existen (defensivo: si un módulo aún no se cargó, no rompe).
    existe = set(frappe.get_all("DocType", pluck="name"))

    if frappe.db.exists("Workspace", WS):
        frappe.delete_doc("Workspace", WS, force=1, ignore_permissions=True)

    ws = frappe.new_doc("Workspace")
    ws.name = WS
    ws.title = WS
    ws.label = WS
    ws.public = 1
    ws.module = "SGC Nucleo"
    ws.icon = "tool"
    ws.sequence_id = 1
    ws.content = _contenido()

    for label, dt in SHORTCUTS:
        if dt in existe:
            ws.append("shortcuts", {"type": "DocType", "link_to": dt, "label": label})

    for card, items in CARDS:
        ws.append("links", {"type": "Card Break", "label": card})
        for dt in items:
            if dt in existe:
                ws.append("links", {"type": "Link", "link_type": "DocType",
                                    "link_to": dt, "label": dt})

    ws.insert(ignore_permissions=True)
    frappe.db.commit()
    print(f"Workspace '{WS}' creado — {len(SHORTCUTS)} accesos, {len(CARDS)} tarjetas")
