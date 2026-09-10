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

# Accesos rápidos (lo que se usa a diario). (etiqueta, destino) donde el destino es
# un doctype, o la tupla ("Report", "<nombre>") para un informe.
SHORTCUTS = [
    ("Indicadores", ("Report", "Indicadores de Acreditacion")),
    ("Documentos", "Documento Controlado"),
    ("Evidencias", "Evidencia"),
    ("Autoevaluación", "Autoevaluacion"),
    ("Hallazgos", "Hallazgo"),
    ("Riesgos", "Riesgo"),
    ("Auditorías", "Auditoria"),
]

# Tarjetas por área. (título de la tarjeta, [items]); un item es un doctype o la
# tupla ("Report", "<nombre>").
CARDS = [
    ("Gestión documental", ["Documento Controlado", "Evidencia", "Trazabilidad"]),
    ("Autoevaluación", ["Autoevaluacion", "Valoracion Criterio", "Valoracion Estandar", "Valor Indicador"]),
    ("Mejora continua", ["Hallazgo", "No Conformidad", "Plan Mejora", "Accion Mejora"]),
    ("Auditoría", ["Programa Auditoria", "Auditoria", "Hallazgo Auditoria", "Informe Auditoria", "Revision Direccion"]),
    ("Riesgos y obligaciones", ["Riesgo", "Tratamiento Riesgo", "Matriz Riesgo", "Evaluacion Riesgo", "Obligacion Ente", "Entrega Obligacion"]),
    ("Procesos", ["Proceso", "Procedimiento", "Ficha Caracterizacion Proceso", "Informe Cumplimiento"]),
    ("Gobierno de la calidad", ["Politica Calidad", "Objetivo Calidad", "Comite", "Reunion", "Acuerdo", "Instrumento", "Aplicacion Instrumento"]),
    ("Marcos e indicadores", ["Marco Normativo", "Elemento Marco", "Indicador", "Ficha Indicador",
                              "Escala Valoracion", ("Report", "Indicadores de Acreditacion")]),
    ("Estructura", ["Unidad Organica", "Programa", "Programa Sede", "Periodo Academico"]),
]


# Etiqueta con la que se muestra cada enlace en el workspace. Sin entrada aquí se
# usa el nombre del doctype, que es lenguaje de desarrollador («Proceso», «Ficha
# Caracterizacion Proceso»): quien trabaja en Calidad no busca «un proceso», busca
# el mapa. La clave es el nombre EXACTO del doctype.
ETIQUETAS = {
    "Proceso": "Mapa de procesos",
    "Ficha Caracterizacion Proceso": "Ficha de caracterización",
}

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


def _destino(item):
    """Un item es un doctype (str) o la tupla ("Report", "<nombre>")."""
    if isinstance(item, tuple):
        return item
    return "DocType", item


def _disponible(tipo, nombre, doctypes):
    """Defensivo: nunca enlazar algo que todavía no existe, o el panel sale roto.

    Los Report estándar los crea `migrate` al importar su .json, antes de que corran
    los pasos de despliegue; pero si el informe se retira, el panel debe seguir vivo.
    """
    if tipo == "DocType":
        return nombre in doctypes
    return bool(frappe.db.exists(tipo, nombre))


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

    for label, destino in SHORTCUTS:
        tipo, nombre = _destino(destino)
        if _disponible(tipo, nombre, existe):
            ws.append("shortcuts", {"type": tipo, "link_to": nombre, "label": label})

    for card, items in CARDS:
        ws.append("links", {"type": "Card Break", "label": card})
        for item in items:
            tipo, nombre = _destino(item)
            if _disponible(tipo, nombre, existe):
                ws.append("links", {"type": "Link", "link_type": tipo,
                                    "link_to": nombre,
                                    "label": ETIQUETAS.get(nombre, nombre)})

    ws.insert(ignore_permissions=True)
    frappe.db.commit()

    # Frappe 16 dejó de armar el MENÚ lateral del Desk desde el Workspace: usa un
    # doctype nuevo, "Workspace Sidebar". El Workspace de arriba solo alimenta la
    # RUTA directa /app/<name>; sin el Workspace Sidebar, la home del Desk sale en
    # blanco para quien no sea Workspace Manager. Se genera con la propia función
    # de Frappe (idempotente; solo crea los que falten). try/except para no romper
    # en versiones anteriores a la introducción del doctype.
    try:
        if frappe.db.exists("DocType", "Workspace Sidebar") and not frappe.db.exists(
            "Workspace Sidebar", WS
        ):
            from frappe.desk.doctype.workspace_sidebar.workspace_sidebar import (
                create_workspace_sidebar_for_workspaces,
            )

            create_workspace_sidebar_for_workspaces()
            frappe.db.commit()
    except Exception as e:  # el menú es cosmético; no debe tumbar el deploy
        frappe.logger().warning(f"f18: no se pudo crear el Workspace Sidebar: {e}")

    _desktop_icon()
    _iconos_de_miga()
    _sidebars_por_modulo()

    print(f"Workspace '{WS}' creado — {len(SHORTCUTS)} accesos, {len(CARDS)} tarjetas")


def _desktop_icon():
    """Crea el Desktop Icon (tipo App) del SGC para el *apps screen* del Desk.

    Por qué existe: en Frappe 16 la home del Desk sin workspace en la URL (`/desk`
    pelado, a donde apunta el ítem «Escritorio» del menú de usuario) renderiza el
    `home_page` del boot. Como `desktop:home_page` = "sgc" NO es una Page, cae al
    fallback "desktop" — el *apps screen*, que pinta `boot.desktop_icons`. Ese set
    lo filtra por permisos `get_desktop_icons`: para un usuario que solo ve el
    workspace SGC (p. ej. «Dueño de Proceso»), el icono App «Framework» de Frappe no
    pasa `check_app_permission` y sus hijos no están permitidos → 0 iconos → PANTALLA
    EN BLANCO. SGC nunca tuvo su propio Desktop Icon porque el `after_app_install` de
    Frappe abortaba con KeyError('logo') (ver hooks.py::add_to_apps_screen).

    Con el `logo` ya presente en el hook, aquí se crea el icono de forma idempotente
    para que los despliegues EXISTENTES lo obtengan en el `bench migrate` (este módulo
    corre desde el pipeline `after_migrate`), sin depender del install fresco.

    Es un icono estándar=0 propiedad de Administrator: `get_desktop_icons` lo muestra
    a TODOS los usuarios. Al no tener iconos hijos, un clic navega directo a su `link`
    (`/desk/sgc`), es decir, al workspace SGC.
    """
    try:
        app = (frappe.get_hooks("add_to_apps_screen", app_name="sgc") or [{}])[0]
        label = app.get("title") or "SGC UPeU"
        if frappe.db.exists("Desktop Icon", label):
            return
        icon = frappe.new_doc("Desktop Icon")
        icon.label = label
        icon.link_type = "External"
        icon.icon_type = "App"
        icon.app = "sgc"
        icon.link = app.get("route") or "/desk/sgc"
        icon.logo_url = app.get("logo") or frappe.get_hooks("app_logo_url", app_name="sgc")
        icon.idx = 1
        icon.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:  # el icono es cosmético; no debe tumbar el deploy
        frappe.logger().warning(f"f18: no se pudo crear el Desktop Icon del SGC: {e}")


# Un Desktop Icon por cada barra lateral del SGC. Sin esto la MIGA DE PAN se queda
# en blanco al navegar: Frappe la dibuja buscando un icono cuyo `label` coincida
# EXACTAMENTE con el título de la barra lateral activa (`breadcrumbs.js`, en
# `set_workspace_breadcrumb`), y el app declara siete módulos —siete barras— contra
# un único icono, «SGC UPeU». Van ocultos: existen para resolver la miga, no para
# aparecer como aplicaciones en el conmutador del Desk.
ICONOS_DE_MIGA = [
    "SGC",
    "SGC Nucleo",
    "SGC Estructura",
    "SGC Procesos",
    "SGC Gobierno",
    "SGC Auditoria",
    "SGC Riesgos",
]

# Barras laterales con nombres de persona. Frappe autogenera una por módulo cuando no
# existe el registro, pero la arma con los TRES primeros doctypes del módulo por fecha
# de creación y usa el nombre del doctype como rótulo: salía «Ficha Caracterizacion
# Pr…» y faltaba todo lo demás. Declararlas aquí sustituye a la autogenerada.
SIDEBARS = {
    "SGC Procesos": [
        ("Mapa de procesos", "DocType", "Proceso"),
        ("Procedimiento", "DocType", "Procedimiento"),
        ("Ficha de caracterización", "DocType", "Ficha Caracterizacion Proceso"),
        ("Informe de cumplimiento", "DocType", "Informe Cumplimiento"),
        ("Volver al SGC", "Workspace", WS),
    ],
    "SGC Estructura": [
        ("Marcos normativos", "DocType", "Marco Normativo"),
        ("Estándares y criterios", "DocType", "Elemento Marco"),
        ("Escalas de valoración", "DocType", "Escala Valoracion"),
        ("Indicadores", "DocType", "Indicador"),
        ("Fichas de indicador", "DocType", "Ficha Indicador"),
        ("Informe de indicadores", "Report", "Indicadores de Acreditacion"),
        ("Unidades orgánicas", "DocType", "Unidad Organica"),
        ("Programas", "DocType", "Programa"),
        ("Programas por sede", "DocType", "Programa Sede"),
        ("Periodos académicos", "DocType", "Periodo Academico"),
        ("Volver al SGC", "Workspace", WS),
    ],
}


def _iconos_de_miga():
    """Crea los iconos que la miga de pan necesita. Idempotente."""
    for label in ICONOS_DE_MIGA:
        try:
            if frappe.db.exists("Desktop Icon", {"label": label}):
                continue
            icon = frappe.new_doc("Desktop Icon")
            icon.label = label
            icon.link_type = "External"
            icon.link = "/desk/sgc"
            icon.app = "sgc"
            icon.standard = 0
            icon.hidden = 1
            icon.insert(ignore_permissions=True)
        except Exception as e:  # la miga es cosmética; no debe tumbar el deploy
            frappe.logger().warning(f"f18: no se pudo crear el icono {label}: {e}")
    frappe.db.commit()


def _sidebars_por_modulo():
    """Declara las barras laterales de módulo, en vez de dejar la autogenerada."""
    if not frappe.db.exists("DocType", "Workspace Sidebar"):
        return
    for titulo, items in SIDEBARS.items():
        try:
            if frappe.db.exists("Workspace Sidebar", titulo):
                continue
            barra = frappe.new_doc("Workspace Sidebar")
            barra.title = titulo
            barra.module = titulo
            barra.header_icon = "tool"
            for etiqueta, tipo, destino in items:
                if tipo == "DocType" and not frappe.db.exists("DocType", destino):
                    continue
                if tipo == "Report" and not frappe.db.exists("Report", destino):
                    continue
                barra.append("items", {
                    "label": etiqueta, "link_type": tipo,
                    "type": "Link", "link_to": destino, "collapsible": 1,
                })
            barra.insert(ignore_permissions=True)
        except Exception as e:  # el menú es cosmético; no debe tumbar el deploy
            frappe.logger().warning(f"f18: no se pudo crear la barra {titulo}: {e}")
    frappe.db.commit()
