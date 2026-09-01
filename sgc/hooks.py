app_name = "sgc"
app_title = "SGC UPeU"
app_publisher = "SciBack"
app_description = "Sistema de Gestion de la Calidad - UPeU (SciBack)"
app_email = "atisbo78@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Logo del app (apps screen del Desk + sidebar). Se deja el de Frappe porque el
# canónico es agnóstico y ese asset siempre existe; el branding institucional se
# aplica en la capa instituciones/, no aquí.
app_logo_url = "/assets/frappe/images/frappe-framework-logo.svg"

# Each item in the list will be shown as an app in the apps page.
# OJO v16: la clave "logo" es OBLIGATORIA. frappe/desk/doctype/desktop_icon/
# desktop_icon.py::create_desktop_icons_from_installed_apps hace app_details[0]["logo"]
# con acceso DURO; si falta, lanza KeyError y aborta la creación del Desktop Icon del
# app. Sin ese icono, /desk pelado (apps screen) queda EN BLANCO para usuarios que no
# son System Manager (solo ven el workspace SGC y ningún icono estándar sobrevive el
# filtro de permisos de get_desktop_icons). "route" apunta directo al workspace SGC.
add_to_apps_screen = [
	{
		"name": "sgc",
		"title": "SGC UPeU",
		"route": "/desk/sgc",
		"logo": app_logo_url,
	}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/sgc/css/sgc.css"
# desk_home.js: redirige la entrada pelada al Desk (/desk) directo al workspace
# SGC saltando el apps screen. Archivo plano (no .bundle.) -> se sirve sin build.
app_include_js = ["/assets/sgc/js/desk_home.js"]

# include js, css files in header of web template
# web_include_css = "/assets/sgc/css/sgc.css"
# web_include_js = "/assets/sgc/js/sgc.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "sgc/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "sgc/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Website Route Rules
# --------------------
# website_route_rules = [
# 	{"from_route": "/notes/<path:app_path>", "to_route": "Note"},
# ]

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "sgc.utils.jinja_methods",
# 	"filters": "sgc.utils.jinja_filters"
# }

# Fixtures
# ------------------
# Termino Tesauro: catálogo de lenguaje controlado sincronizado desde el Tesauro
# Institucional UPeU (VocBench/SKOS). Frappe lo importa en cada `bench migrate`.
# La fuente de verdad es VocBench (LAN, requiere VPN); este fixture es una copia
# versionada. Para re-sincronizar: deploy/sync_tesauro_vocbench.py
fixtures = [
	{"dt": "Termino Tesauro", "order_by": "codigo asc"},
]

# Installation
# ------------

# Un site nuevo debe quedar con el mismo contrato funcional que uno migrado.
# Sin este hook, `bench new-site --install-app sgc` sincroniza los DocTypes pero
# deja los workflows/RBAC sin crear; cualquier `apply_workflow()` obtiene nombre
# vacío y falla con `Workflow  not found` hasta ejecutar un migrate adicional.
after_install = "sgc.setup.f_deploy_run_all.run"

# Migration
# ------------
# Fase 1 (2026-07-19, hallazgo H8): antes de esto, `bench migrate` NO aplicaba
# RBAC ni workflows — un site nuevo o recuperado en DR quedaba con System
# Manager teniendo create/read/write/delete en los 68 DocTypes y ningún rol SGC
# funcional, hasta que alguien corriera a mano 6+ `bench execute` en el orden
# correcto (nunca documentado más que como comentario suelto). Todos los pasos
# de f_deploy_run_all son idempotentes — reejecutar en cada migrate es seguro.
after_migrate = "sgc.setup.f_deploy_run_all.run"

# Uninstallation
# ------------

# before_uninstall = "sgc.uninstall.before_uninstall"
# after_uninstall = "sgc.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "sgc.utils.before_app_install"
# after_app_install = "sgc.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "sgc.utils.before_app_uninstall"
# after_app_uninstall = "sgc.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "sgc.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "sgc.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways
#
# M07 — Visibilidad por programa (opt-in, seguro). Ver sgc/permissions.py.
# Acota SOLO a usuarios con User Permission sobre "Programa Sede" y sin rol
# exento. Sin User Permission sembrada, el mecanismo queda INACTIVO (todos ven
# todo). Solo se acotan DocTypes con derivación de programa NO ambigua.
permission_query_conditions = {
	"Autoevaluacion": "sgc.permissions.pqc_autoevaluacion",
	"Hallazgo": "sgc.permissions.pqc_hallazgo",
	"No Conformidad": "sgc.permissions.pqc_no_conformidad",
	"Valoracion Criterio": "sgc.permissions.pqc_valoracion_criterio",
	"Valoracion Estandar": "sgc.permissions.pqc_valoracion_estandar",
	"Plan Mejora": "sgc.permissions.pqc_plan_mejora",
}

has_permission = {
	"Autoevaluacion": "sgc.permissions.has_permission",
	"Hallazgo": "sgc.permissions.has_permission",
	"No Conformidad": "sgc.permissions.has_permission",
	"Valoracion Criterio": "sgc.permissions.has_permission",
	"Valoracion Estandar": "sgc.permissions.has_permission",
	"Plan Mejora": "sgc.permissions.has_permission",
}

# Document Events
# ---------------
# Hook on document methods and events

# Correlativos que cuentan lo que dicen contar.
#
# Estos DocTypes se autonombran con `format:XXX-{YYYY}-{#####}`, y ahí Frappe
# tiene una trampa: resuelve cada `{parámetro}` por separado, así que el bloque
# de almohadillas acaba pidiendo `getseries("")` — un contador GLOBAL del sitio
# que comparten TODOS. Por eso los códigos salían consecutivos entre tipos
# distintos (`RSK-2026-00034`, `NC-2026-00035`, `TRR-2026-00036`) y el número
# no significaba lo que aparentaba.
#
# `set_new_name` ejecuta `doc.run_method("autoname")` antes de mirar el patrón
# del DocType y respeta el nombre que se haya puesto ahí, así que basta este
# gancho: el patrón sigue mandando en la FORMA del código, y solo cambia de
# dónde sale el número. Ver `sgc/naming.py`.
# Buscar enlaces sin pelearse con las tildes. En castellano casi todo lleva, y
# la búsqueda de Frappe compara el texto tal cual: «gestion» no encuentra
# «Gestión». Es el mecanismo estándar de Frappe para esto (`standard_queries`),
# con su misma firma y respetando permisos por fila. Ver `sgc/buscar.py`.
#
# Se registra para los DocTypes cuyo título dice algo distinto del código, que
# son justo aquellos en los que alguien escribe palabras para buscar.
standard_queries = {
	"Acuerdo": "sgc.buscar.enlaces",
	"Aplicacion Instrumento": "sgc.buscar.enlaces",
	"Auditoria": "sgc.buscar.enlaces",
	"Autoevaluacion": "sgc.buscar.enlaces",
	"Comite": "sgc.buscar.enlaces",
	"Documento Controlado": "sgc.buscar.enlaces",
	"Elemento Marco": "sgc.buscar.enlaces",
	"Ente Externo": "sgc.buscar.enlaces",
	"Escala Valoracion": "sgc.buscar.enlaces",
	"Evidencia": "sgc.buscar.enlaces",
	"Ficha Caracterizacion Proceso": "sgc.buscar.enlaces",
	"Ficha Indicador": "sgc.buscar.enlaces",
	"Grupo Interes": "sgc.buscar.enlaces",
	"Indicador": "sgc.buscar.enlaces",
	"Informe Cumplimiento": "sgc.buscar.enlaces",
	"Instrumento": "sgc.buscar.enlaces",
	"Interaccion Proceso": "sgc.buscar.enlaces",
	"Marco Normativo": "sgc.buscar.enlaces",
	"Matriz Riesgo": "sgc.buscar.enlaces",
	"No Conformidad": "sgc.buscar.enlaces",
	"Objetivo Calidad": "sgc.buscar.enlaces",
	"Obligacion Ente": "sgc.buscar.enlaces",
	"Plan Mejora": "sgc.buscar.enlaces",
	"Politica Calidad": "sgc.buscar.enlaces",
	"Procedimiento": "sgc.buscar.enlaces",
	"Proceso": "sgc.buscar.enlaces",
	"Programa": "sgc.buscar.enlaces",
	"Programa Auditoria": "sgc.buscar.enlaces",
	"Resultado Instrumento": "sgc.buscar.enlaces",
	"Reunion": "sgc.buscar.enlaces",
	"Revision Direccion": "sgc.buscar.enlaces",
	"Riesgo": "sgc.buscar.enlaces",
	"Trazabilidad": "sgc.buscar.enlaces",
	"Unidad Organica": "sgc.buscar.enlaces",
	"Valor Indicador": "sgc.buscar.enlaces",
	"Valoracion Criterio": "sgc.buscar.enlaces",
	"Valoracion Estandar": "sgc.buscar.enlaces",
}

doc_events = {
	"Acuerdo": {"autoname": "sgc.naming.correlativo_por_prefijo"},
	"Aplicacion Instrumento": {"autoname": "sgc.naming.correlativo_por_prefijo"},
	"Auditoria": {"autoname": "sgc.naming.correlativo_por_prefijo"},
	"Entrega Obligacion": {"autoname": "sgc.naming.correlativo_por_prefijo"},
	"Evaluacion Riesgo": {"autoname": "sgc.naming.correlativo_por_prefijo"},
	"Informe Cumplimiento": {"autoname": "sgc.naming.correlativo_por_prefijo"},
	"No Conformidad": {"autoname": "sgc.naming.correlativo_por_prefijo"},
	"Resultado Instrumento": {"autoname": "sgc.naming.correlativo_por_prefijo"},
	"Reunion": {"autoname": "sgc.naming.correlativo_por_prefijo"},
	"Revision Direccion": {"autoname": "sgc.naming.correlativo_por_prefijo"},
	"Riesgo": {"autoname": "sgc.naming.correlativo_por_prefijo"},
	"Tratamiento Riesgo": {"autoname": "sgc.naming.correlativo_por_prefijo"},
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"sgc.tasks.all"
# 	],
# 	"daily": [
# 		"sgc.tasks.daily"
# 	],
# 	"hourly": [
# 		"sgc.tasks.hourly"
# 	],
# 	"weekly": [
# 		"sgc.tasks.weekly"
# 	],
# 	"monthly": [
# 		"sgc.tasks.monthly"
# 	],
# }

# M09 (2026-07-19): cierra el gap de Evidencia.on_update -- una vigencia que
# expira sin que nadie guarde el documento debe marcarse Vencida igual.
scheduler_events = {
	"daily": [
		"sgc.tasks.marcar_evidencias_vencidas",
		"sgc.tasks.marcar_acuerdos_vencidos",
	],
}

# Testing
# -------

# before_tests = "sgc.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "sgc.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "sgc.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "sgc.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["sgc.utils.before_request"]
# after_request = ["sgc.utils.after_request"]

# Job Events
# ----------
# before_job = ["sgc.utils.before_job"]
# after_job = ["sgc.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"sgc.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []
