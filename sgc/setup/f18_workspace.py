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

# =============================================================================
# NAVEGACIÓN DEL SGC — una sola definición para el inicio, las portadas y los menús
# =============================================================================
#
# Hasta el 12-oct-2026 los menús se agrupaban por MÓDULO TÉCNICO, que es como se
# repartió el código al programarlo, no como trabaja la DPGC: los indicadores
# estaban en tres sitios, «Gestión de la calidad» mezclaba documentos, acreditación,
# mejora y lotes técnicos de ingesta, el informe de cumplimiento SUNEDU colgaba de
# «Procesos» y la revisión por la dirección de «Auditoría». Ahora cada ÁREA es una
# tarea de la DPGC, y las pantallas se movieron al módulo de su área (las migas de
# Frappe dependen del módulo: ver `migas.js`).
#
# Todo sale de AREAS + TARJETAS + ETIQUETAS: el inicio, la portada de cada área y su
# barra lateral se generan de aquí, así que no pueden volver a contradecirse.

# Cada área: módulo -> (nombre visible, [tarjetas de su portada]). El ORDEN es el
# del menú: de lo que define el sistema (procesos, documentos) a lo que lo mide y
# lo mejora, y al final la configuración. El nombre visible tiene que coincidir
# con `translations/es.csv` (lo comprueba test_migas).
AREAS = {
    "SGC Procesos": ("Procesos", ["Mapa de procesos"]),
    "SGC Documental": ("Documentos", ["Documentos"]),
    "SGC Indicadores": ("Indicadores", ["Indicadores y mediciones", "Seguimiento"]),
    "SGC Acreditacion": ("Acreditación y licenciamiento",
                         ["Autoevaluación", "Marcos de calidad", "Licenciamiento y obligaciones"]),
    "SGC Nucleo": ("Mejora continua", ["Hallazgos e incidencias", "Planes y acciones"]),
    "SGC Auditoria": ("Auditoría", ["Auditoría interna"]),
    "SGC Riesgos": ("Riesgos", ["Gestión de riesgos"]),
    "SGC Gobierno": ("Dirección y partes interesadas", ["Dirección", "Partes interesadas y encuestas"]),
    "SGC Estructura": ("Configuración", ["Estructura institucional", "Datos e integraciones", "Sistema"]),
}

# Tarjetas: (título, [items]); un item es un doctype o ("Report", "<nombre>"). Cada
# pantalla está en UNA sola tarjeta y en el área de su módulo (test_modulos_por_area).
# Fuera de los menús a propósito: las tablas hijas y `Trazabilidad` (el vínculo entre
# una evidencia y lo que acredita, que se gestiona desde la propia evidencia).
TARJETAS = {
    "Mapa de procesos": ["Proceso", "Procedimiento", "Ficha Caracterizacion Proceso",
                         "Mapa Procesos", "Interaccion Proceso"],
    "Documentos": ["Documento Controlado", "Carpeta Documental", ("Report", "Accesos a Documentos")],
    "Indicadores y mediciones": ["Indicador", "Ficha Indicador", "Valor Indicador"],
    "Seguimiento": ["Tablero Indicadores", "Alerta Indicador", ("Report", "Indicadores de Acreditacion"),
                    ("Report", "Indicadores por Familia")],
    "Autoevaluación": ["Autoevaluacion", "Evidencia", "Valoracion Criterio", "Valoracion Estandar"],
    "Marcos de calidad": ["Marco Normativo", "Elemento Marco", "Escala Valoracion"],
    "Licenciamiento y obligaciones": ["Informe Cumplimiento", "Ente Externo", "Obligacion Ente",
                                      "Entrega Obligacion"],
    "Hallazgos e incidencias": ["Hallazgo", "No Conformidad", "Salida No Conforme"],
    "Planes y acciones": ["Plan Mejora", "Accion Mejora", ("Report", "Mejoramiento Continuo"),
                          ("Report", "Salidas No Conformes")],
    "Auditoría interna": ["Programa Auditoria", "Auditoria", "Lista Verificacion", "Hallazgo Auditoria",
                          "Informe Auditoria", ("Report", "Resultados de Auditoria")],
    "Gestión de riesgos": ["Riesgo", "Evento Riesgo", "Matriz Riesgo", "Evaluacion Riesgo",
                           "Tratamiento Riesgo", ("Report", "Matriz de Riesgos")],
    "Dirección": ["Politica Calidad", "Objetivo Calidad", "Revision Direccion", "Comite", "Reunion",
                  "Acuerdo", "Comunicado"],
    "Partes interesadas y encuestas": ["Grupo Interes", "Instrumento", "Aplicacion Instrumento",
                                       "Resultado Instrumento"],
    "Estructura institucional": ["Unidad Organica", "Programa", "Programa Sede", "Periodo Academico"],
    "Datos e integraciones": ["Fuente Dato", "Regla Validacion", "Lote Ingesta", "Termino Tesauro"],
    "Sistema": ["Configuracion Correo", "Configuracion Soporte", "Registro Correo"],
}
CARDS = list(TARJETAS.items())  # compatibilidad con quien importe CARDS

# Accesos rápidos del inicio: lo que se abre a diario, uno por área de trabajo.
SHORTCUTS = [
    ("Mapa de procesos", "Proceso"),
    ("Documentos", "Documento Controlado"),
    ("Indicadores", "Indicador"),
    ("Autoevaluación", "Autoevaluacion"),
    ("No conformidades", "No Conformidad"),
    ("Auditorías", "Auditoria"),
    ("Riesgos", "Riesgo"),
    # Lo usa cualquier colaborador: es por donde entra quien no tiene rol del SGC.
    ("Reportar evento de riesgo", "Evento Riesgo"),
]

# Cifras (Number Card) y gráficos (Dashboard Chart) que crea f21. Hasta el 12-oct no
# estaban en ninguna portada: existían y nadie los veía. Clave = portada; el valor es
# la etiqueta visible, y el documento se llama «SGC - <etiqueta>».
CIFRAS = {
    "SGC": ["Documentos por revisar", "No conformidades abiertas", "Acciones de mejora vencidas",
            "Hallazgos de auditoria abiertos", "Riesgos altos tras tratamiento",
            "Tratamientos de riesgo vencidos"],
    "SGC Documental": ["Documentos por revisar"],
    "SGC Nucleo": ["No conformidades abiertas", "Acciones de mejora abiertas", "Acciones de mejora vencidas",
                   "Incidencias abiertas", "Planes de mejora en rojo"],
    "SGC Auditoria": ["Hallazgos de auditoria abiertos"],
    "SGC Riesgos": ["Riesgos altos tras tratamiento", "Tratamientos de riesgo vencidos"],
}
GRAFICOS = {
    "SGC Nucleo": ["No conformidades por origen", "No conformidades detectadas por mes",
                   "Acciones de mejora por estado"],
    "SGC Auditoria": ["Hallazgos de auditoría por tipo"],
    "SGC Riesgos": ["Riesgos por categoría"],
}


def ruta_area(modulo):
    """Ruta del Desk de la portada de un área: el slug del nombre del workspace."""
    return "/desk/" + modulo.lower().replace(" ", "-")


# Cómo se llama cada pantalla en tarjetas y menús: en plural y en el lenguaje de quien
# trabaja en Calidad, no el nombre técnico del doctype. Cubre TODAS las de TARJETAS
# (lo comprueba test_modulos_por_area): sin entrada, el menú enseñaría «Ficha Caracterizacion
# Proceso». La miga usa el singular de `translations/es.csv`.
ETIQUETAS = {
    "Proceso": "Mapa de procesos",
    "Procedimiento": "Procedimientos",
    "Ficha Caracterizacion Proceso": "Fichas de caracterización",
    "Mapa Procesos": "Mapa institucional",
    "Interaccion Proceso": "Interacciones entre procesos",
    "Documento Controlado": "Documentos controlados",
    "Carpeta Documental": "Carpetas documentales",
    "Accesos a Documentos": "Accesos a documentos",
    "Indicador": "Indicadores",
    "Ficha Indicador": "Fichas de indicador",
    "Valor Indicador": "Mediciones",
    "Tablero Indicadores": "Tableros de indicadores",
    "Alerta Indicador": "Alertas de indicador",
    "Indicadores de Acreditacion": "Indicadores de acreditación",
    "Indicadores por Familia": "Indicadores por familia",
    "Autoevaluacion": "Autoevaluaciones",
    "Evidencia": "Evidencias",
    "Valoracion Criterio": "Valoración de criterios",
    "Valoracion Estandar": "Valoración de estándares",
    "Marco Normativo": "Marcos normativos",
    "Elemento Marco": "Estándares y criterios",
    "Escala Valoracion": "Escalas de valoración",
    "Informe Cumplimiento": "Informe de cumplimiento (SUNEDU)",
    "Ente Externo": "Entes externos",
    "Obligacion Ente": "Obligaciones ante entes",
    "Entrega Obligacion": "Entregas de obligaciones",
    "Hallazgo": "Hallazgos",
    "No Conformidad": "No conformidades",
    "Salida No Conforme": "Salidas no conformes",
    "Plan Mejora": "Planes de mejora",
    "Accion Mejora": "Acciones de mejora",
    "Mejoramiento Continuo": "Informe de mejoramiento continuo",
    "Salidas No Conformes": "Informe de salidas no conformes",
    "Programa Auditoria": "Programas de auditoría",
    "Auditoria": "Auditorías",
    "Lista Verificacion": "Listas de verificación",
    "Hallazgo Auditoria": "Hallazgos de auditoría",
    "Informe Auditoria": "Informes de auditoría",
    "Resultados de Auditoria": "Resultados de auditoría",
    "Riesgo": "Riesgos",
    "Evento Riesgo": "Eventos de riesgo",
    "Matriz Riesgo": "Matrices de riesgo",
    "Evaluacion Riesgo": "Evaluaciones de riesgo",
    "Tratamiento Riesgo": "Tratamientos de riesgo",
    "Matriz de Riesgos": "Matriz de riesgos (informe)",
    "Politica Calidad": "Política de calidad",
    "Objetivo Calidad": "Objetivos de calidad",
    "Revision Direccion": "Revisión por la dirección",
    "Comite": "Comités",
    "Reunion": "Reuniones",
    "Acuerdo": "Acuerdos",
    "Comunicado": "Comunicados",
    "Grupo Interes": "Grupos de interés",
    "Instrumento": "Instrumentos (encuestas)",
    "Aplicacion Instrumento": "Aplicaciones de encuestas",
    "Resultado Instrumento": "Resultados de encuestas",
    "Unidad Organica": "Unidades orgánicas",
    "Programa": "Programas",
    "Programa Sede": "Programas por sede",
    "Periodo Academico": "Periodos académicos",
    "Fuente Dato": "Fuentes de datos",
    "Regla Validacion": "Reglas de validación",
    "Lote Ingesta": "Lotes de ingesta",
    "Termino Tesauro": "Tesauro",
    "Configuracion Correo": "Configuración de correo",
    "Configuracion Soporte": "Configuración de soporte",
    "Registro Correo": "Registro de correos",
}


def _bloques_de_cifras(portada, prefijo):
    """Bloques de contenido para las cifras y gráficos de una portada."""
    b = []
    for i, etiqueta in enumerate(CIFRAS.get(portada, [])):
        b.append({"id": f"{prefijo}n{i}", "type": "number_card",
                  "data": {"number_card_name": etiqueta, "col": 4}})
    for i, etiqueta in enumerate(GRAFICOS.get(portada, [])):
        b.append({"id": f"{prefijo}g{i}", "type": "chart",
                  "data": {"chart_name": etiqueta, "col": 6}})
    return b


def _anadir_cifras(ws, portada):
    """Enlaza al workspace las cifras y gráficos que existen (los crea f21)."""
    for etiqueta in CIFRAS.get(portada, []):
        if frappe.db.exists("Number Card", f"SGC - {etiqueta}"):
            ws.append("number_cards", {"number_card_name": f"SGC - {etiqueta}", "label": etiqueta})
    for etiqueta in GRAFICOS.get(portada, []):
        if frappe.db.exists("Dashboard Chart", f"SGC - {etiqueta}"):
            ws.append("charts", {"chart_name": f"SGC - {etiqueta}", "label": etiqueta})


def _contenido():
    """El inicio: accesos del día a día, el estado del sistema en cifras y una tarjeta
    por área con sus pantallas, en el mismo orden que el menú.

    Son bloques del editor nativo de Frappe. No es HTML a medida: es lo mismo que
    genera la UI cuando se arma un workspace a mano.
    """
    b = [{"id": "hdr_a", "type": "header",
          "data": {"text": "Sistema de Gestión de la Calidad", "col": 12}}]
    for i, (label, _dt) in enumerate(SHORTCUTS):
        b.append({"id": f"sc{i}", "type": "shortcut",
                  "data": {"shortcut_name": label, "col": 3}})
    if CIFRAS.get(WS):
        b.append({"id": "hdr_c", "type": "header", "data": {"text": "Estado del sistema", "col": 12}})
        b += _bloques_de_cifras(WS, "in")
    b.append({"id": "hdr_b", "type": "header", "data": {"text": "Áreas", "col": 12}})
    for i, (_modulo, (nombre, _cards)) in enumerate(AREAS.items()):
        b.append({"id": f"cd{i}", "type": "card", "data": {"card_name": nombre, "col": 4}})
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

    # Una tarjeta por área, con el nombre del área y todas sus pantallas.
    for _modulo, (nombre_area, cards) in AREAS.items():
        ws.append("links", {"type": "Card Break", "label": nombre_area})
        for card in cards:
            for item in TARJETAS[card]:
                tipo, nombre = _destino(item)
                if _disponible(tipo, nombre, existe):
                    ws.append("links", {"type": "Link", "link_type": tipo,
                                        "link_to": nombre,
                                        "label": ETIQUETAS.get(nombre, nombre)})
    _anadir_cifras(ws, WS)

    ws.insert(ignore_permissions=True)
    frappe.db.commit()

    # Frappe 16 dejó de armar el MENÚ lateral del Desk desde el Workspace: usa un
    # doctype nuevo, "Workspace Sidebar". El Workspace de arriba solo alimenta la
    # RUTA directa /desk/<name>; sin el Workspace Sidebar, la home del Desk sale en
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

    _portadas_de_area(existe)
    _desktop_icon()
    _iconos_de_miga()
    _sidebars_por_modulo()

    print(f"Workspace '{WS}' creado — {len(SHORTCUTS)} accesos, {len(AREAS)} áreas, "
          f"{len(CIFRAS.get(WS, []))} cifras en el inicio")


def _portadas_de_area(existe):
    """Una portada (Workspace) por área, con las tarjetas de esa área.

    Se recrean en cada despliegue, como la general: lo que manda es este código.
    """
    tarjetas = TARJETAS
    for i, (modulo, (nombre, cards)) in enumerate(AREAS.items(), start=2):
        try:
            if frappe.db.exists("Workspace", modulo):
                frappe.delete_doc("Workspace", modulo, force=1, ignore_permissions=True)
            ws = frappe.new_doc("Workspace")
            ws.name = ws.title = ws.label = modulo
            ws.public = 1
            ws.module = modulo
            ws.icon = "tool"
            ws.sequence_id = i
            bloques = [{"id": "hdr", "type": "header", "data": {"text": nombre, "col": 12}}]
            bloques += _bloques_de_cifras(modulo, "p")
            _anadir_cifras(ws, modulo)
            for j, card in enumerate(cards):
                bloques.append({"id": f"cd{j}", "type": "card", "data": {"card_name": card, "col": 4}})
                ws.append("links", {"type": "Card Break", "label": card})
                for item in tarjetas.get(card, []):
                    tipo, destino = _destino(item)
                    if _disponible(tipo, destino, existe):
                        ws.append("links", {"type": "Link", "link_type": tipo, "link_to": destino,
                                            "label": ETIQUETAS.get(destino, destino)})
            ws.content = json.dumps(bloques, ensure_ascii=False)
            ws.insert(ignore_permissions=True)
        except Exception as e:  # la portada es navegación; no debe tumbar el deploy
            frappe.logger().warning(f"f18: no se pudo crear la portada {modulo}: {e}")
    frappe.db.commit()


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
        label = app.get("title") or "SGC"
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
# `set_workspace_breadcrumb`). Van ocultos: existen para resolver la miga, no para
# aparecer como aplicaciones en el conmutador del Desk.
ICONOS_DE_MIGA = [WS, *AREAS]


def _barras():
    """Barras laterales: la general (solo navega entre áreas) y una por área.

    Se generan de AREAS + TARJETAS, en el mismo orden que la portada: lo que ve la
    persona en el menú es exactamente lo que ve en la portada del área. Frappe
    autogenera una barra por módulo si no existe el registro, pero con los TRES
    primeros doctypes por fecha de creación y su nombre técnico; declararlas aquí la
    sustituye.

    La barra general NO repite pantallas de las áreas: si una pantalla está en dos
    barras, Frappe elige la barra por historial (`sidebar.js`, resolve_sidebar) y la
    miga cambia según el camino.
    """
    barras = {WS: [("Inicio", "Workspace", WS)] + [
        (nombre, "Workspace", modulo) for modulo, (nombre, _c) in AREAS.items()]}
    for modulo, (_nombre, cards) in AREAS.items():
        items = [("Portada del área", "Workspace", modulo)]
        for card in cards:
            for item in TARJETAS[card]:
                tipo, destino = _destino(item)
                items.append((ETIQUETAS.get(destino, destino), tipo, destino))
        items.append(("Volver al inicio", "Workspace", WS))
        barras[modulo] = items
    return barras


SIDEBARS = _barras()

# Módulo de cada barra: el de su área; la general pertenece al núcleo, como su workspace.
MODULO_DE_BARRA = {WS: "SGC Nucleo"}


def _iconos_de_miga():
    """Crea o corrige los iconos que la miga de pan necesita. Idempotente.

    El enlace de cada uno es la portada de su área: pulsar «Auditoría» en la miga
    lleva al área de auditoría, no a la portada general (hasta el 27-sep los seis
    enlazaban a /desk/sgc).
    """
    for label in ICONOS_DE_MIGA:
        try:
            enlace = ruta_area(label) if label in AREAS else "/desk/sgc"
            existente = frappe.db.get_value("Desktop Icon", {"label": label}, "name")
            if existente:
                if frappe.db.get_value("Desktop Icon", existente, "link") != enlace:
                    frappe.db.set_value("Desktop Icon", existente, "link", enlace)
                continue
            icon = frappe.new_doc("Desktop Icon")
            icon.label = label
            icon.link_type = "External"
            icon.link = enlace
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
            # Se recrea, no se conserva. Con `continue`, una barra creada en un
            # despliegue viejo quedaba congelada para siempre: añadir un módulo
            # o corregir un rótulo aquí no llegaba a producción, y el código
            # decía una cosa mientras la pantalla mostraba otra.
            if frappe.db.exists("Workspace Sidebar", titulo):
                frappe.delete_doc("Workspace Sidebar", titulo, force=1, ignore_permissions=True)
            barra = frappe.new_doc("Workspace Sidebar")
            barra.title = titulo
            barra.module = MODULO_DE_BARRA.get(titulo, titulo)
            # Sin `app`, Frappe descarta la barra al elegir cuál mostrar: filtra las
            # candidatas por la app del módulo (`sidebar.js`, filter_sidebars_from_app)
            # y cae en la barra de un módulo arrastrado de la pantalla anterior. Los
            # informes de auditoría y riesgos salían bajo «Marcos y estructura».
            barra.app = "sgc"
            barra.header_icon = "tool"
            for etiqueta, tipo, destino in items:
                if tipo == "DocType" and not frappe.db.exists("DocType", destino):
                    continue
                if tipo == "Report" and not frappe.db.exists("Report", destino):
                    continue
                if tipo == "Workspace" and not frappe.db.exists("Workspace", destino):
                    continue
                barra.append("items", {
                    "label": etiqueta, "link_type": tipo,
                    "type": "Link", "link_to": destino, "collapsible": 1,
                })
            barra.insert(ignore_permissions=True)
        except Exception as e:  # el menú es cosmético; no debe tumbar el deploy
            frappe.logger().warning(f"f18: no se pudo crear la barra {titulo}: {e}")
    frappe.db.commit()
