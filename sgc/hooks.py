# El canónico no nombra a ninguna institución (#65). `hooks.py` se lee al CARGAR
# la app, antes de que exista un sitio, así que no puede consultar `site_config`:
# por eso estos valores son neutros y no parametrizables como los de #40. Lo que
# el usuario ve en el Desk lo pisa `f3b_branding` desde `site_config`.
app_name = "sgc"
app_title = "SGC"
app_publisher = "SciBack"
app_description = "Sistema de Gestion de la Calidad"
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
		"title": "SGC",
		"route": "/desk/sgc",
		"logo": app_logo_url,
	}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/sgc/css/sgc.css"
# Ficheros planos (no .bundle.) -> se sirven sin build. La entrada al Desk y la miga
# de pan las resuelve Frappe con los ficheros estándar (sgc/escritorio.py).
app_include_js = [
	"/assets/sgc/js/latido_scheduler.js",
	"/assets/sgc/js/soporte.js",
]

# Canal de soporte (#56): «Reportar un problema» en el menú de Ayuda, SOLO si hay un
# helpdesk configurado (`condition` se evalúa en el navegador contra el boot).
extend_bootinfo = ["sgc.soporte.boot"]
# El manual de usuario se sirve en /manual detrás de la sesión del SGC
# (`sgc.manual_auth`). Un Route que empieza por «/» y no por «/desk» lo abre el
# navegador en la misma pestaña. Una instancia sin manual lo oculta en Navbar
# Settings (casilla «Oculto»): el migrate respeta lo que ya existe.
standard_help_items = [
	{
		"item_label": "Manual de usuario",
		"item_type": "Route",
		"route": "/manual/",
		"is_standard": 1,
	},
	{
		"item_label": "Reportar un problema",
		"item_type": "Action",
		"action": "sgc.soporte.abrir()",
		"condition": "frappe.boot.sgc_soporte && frappe.boot.sgc_soporte.activo",
		"is_standard": 1,
	},
]

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

# La identidad de la institución, leída al imprimir por los formatos estándar (sgc/identidad.py).
jinja = {"methods": ["sgc.identidad.sgc_identidad"]}

# Fixtures
# ------------------
# Lo que el SGC trae para cualquier institución y Frappe no guarda en la carpeta del módulo:
# workflows, sus estados y acciones, roles, perfiles de rol y el permiso de los roles del SGC
# sobre el historial de cambios (`Version`, que es de Frappe). Se importan en cada `migrate`
# (sync_fixtures). Solo datos válidos para cualquier institución (#102): el tesauro, por
# ejemplo, lo carga cada institución desde su capa con `import-doc`.
_ROLES_SGC = [
	"DPGC",
	"Analista de Calidad (DPGC)",
	"Coordinador de Calidad de Facultad",
	"Responsable de Calidad de Programa",
	"Miembro de Comité de Calidad",
	"Dueño de Proceso",
	"Data Steward",
	"Auditor Interno",
	"Rectorado/VR (lectura)",
	"Decano/Director (lectura)",
	"Responsable de Sede",
	"Lector Externo",
	"Autoridad Aprobadora",
	"Colaborador",
]

fixtures = [
	{"dt": "Role", "filters": [["name", "in", _ROLES_SGC]]},
	{"dt": "Role Profile", "filters": [["name", "in", [
		"Administrador SGC",
		"Auditoría Interna",
		"Autoridad Rectoral",
		"Coordinador de Calidad (Facultad)",
		"Coordinador de Calidad (Programa)",
		"Evaluador Externo",
		"Jefe de Escuela",
	]]]},
	{"dt": "Workflow State", "filters": [["name", "in", [
		"Abierta",
		"Abierto",
		"Aprobado",
		"Borrador",
		"Cerrada",
		"Cerrada eficaz",
		"Cerrada no eficaz",
		"Cerrado",
		"Cerrado eficaz",
		"Cerrado no eficaz",
		"Confirmado",
		"Consolidada",
		"Descartado",
		"Detectada",
		"Distribuido",
		"Ejecutada",
		"En analisis",
		"En campo",
		"En curso",
		"En ejecucion",
		"En evaluacion",
		"En revision",
		"En revisión",
		"En tratamiento",
		"En verificacion",
		"Escalado a NC",
		"Evaluado",
		"Identificado",
		"Implementado",
		"Informe emitido",
		"Materializado",
		"Monitoreado",
		"Observada",
		"Observado",
		"Obsoleto",
		"Pendiente",
		"Planificada",
		"Planificado",
		"Presentado a SUNEDU",
		"Publicado",
		"Realizada",
		"Reportado",
		"Subsanada",
		"Tratada",
		"Valida",
		"Verificacion",
		"Verificada",
		"Verificada eficaz",
		"Verificada no eficaz",
		"Verificado",
	]]]},
	{"dt": "Workflow Action Master", "filters": [["name", "in", [
		"Analizar causa",
		"Aprobar",
		"Aprobar programa",
		"Aprobar y ejecutar",
		"Cerrar",
		"Cerrar aplicacion",
		"Cerrar auditoria",
		"Cerrar eficaz",
		"Cerrar no eficaz",
		"Cerrar plan",
		"Cerrar programa",
		"Cerrar revision",
		"Confirmar",
		"Consolidar",
		"Corregir",
		"Derogar",
		"Descartar",
		"Devolver a borrador",
		"Devolver a ejecucion",
		"Devolver a evaluacion",
		"Devolver a planificada",
		"Devolver a tratamiento",
		"Distribuir",
		"Emitir informe",
		"Enviar a revision",
		"Enviar a verificacion",
		"Escalar a NC",
		"Evaluar",
		"Iniciar",
		"Iniciar auditoria",
		"Iniciar campo",
		"Iniciar ejecucion",
		"Iniciar evaluacion",
		"Iniciar tratamiento",
		"Marcar ejecutada",
		"Marcar implementado",
		"Materializar",
		"Monitorear",
		"Observar",
		"Presentar a SUNEDU",
		"Publicar",
		"Reabrir",
		"Reabrir escalado",
		"Reabrir revision",
		"Reabrir tratamiento",
		"Realizar revision",
		"Registrar tratamiento",
		"Subsanar",
		"Tratar",
		"Validar",
		"Verificar",
		"Verificar eficaz",
		"Verificar no eficaz",
		"Nueva version",
	]]]},
	{"dt": "Workflow", "filters": [["name", "in", [
		"Accion de Mejora SGC",
		"Aplicacion Instrumento SGC",
		"Auditoria SGC",
		"Autoevaluacion SGC",
		"Documento Controlado SGC",
		"Evento Riesgo SGC",
		"Evidencia SGC",
		"Ficha Caracterizacion SGC",
		"Hallazgo Auditoria SGC",
		"Hallazgo SGC",
		"Informe Auditoria SGC",
		"Informe Cumplimiento SGC",
		"No Conformidad SGC",
		"Plan de Mejora SGC",
		"Procedimiento SGC",
		"Programa Auditoria SGC",
		"Revision Direccion SGC",
		"Riesgo SGC",
		"Salida No Conforme SGC",
		"Tratamiento Riesgo SGC",
	]]]},
	{"dt": "Custom DocPerm", "filters": [["parent", "=", "Version"], ["role", "in", _ROLES_SGC]]},
]

# Installation
# ------------

# Lo que depende de cada institución (marcos, identidad, SSO) sale de su
# site_config: también al instalar. Lo demás lo sincroniza Frappe (nativo-frappe.md).
after_install = "sgc.setup.f_deploy_run_all.run"

# Migration
# ------------
# Solo los pasos que dependen de cada institución (ver f_deploy_run_all). Permisos,
# roles, flujos, avisos, formatos y portadas los aplica Frappe en el propio migrate.
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
# M07 — Visibilidad por programa y por sede (opt-in, seguro). Ver sgc/permissions.py.
# Acota SOLO a usuarios con User Permission sobre "Programa Sede" o sobre su sede
# y sin rol exento. Sin User Permission sembrada, el mecanismo queda INACTIVO
# (todos ven todo). Solo se acotan DocTypes con derivación de programa NO ambigua.
permission_query_conditions = {
	"Autoevaluacion": "sgc.permissions.pqc_autoevaluacion",
	"Hallazgo": "sgc.permissions.pqc_hallazgo",
	"No Conformidad": "sgc.permissions.pqc_no_conformidad",
	"Salida No Conforme": "sgc.permissions.pqc_salida_no_conforme",
	"Valor Indicador": "sgc.permissions.pqc_valor_indicador",
	"Alerta Indicador": "sgc.permissions.pqc_alerta_indicador",
	"Auditoria": "sgc.permissions.pqc_auditoria",
	"Comite": "sgc.permissions.pqc_comite",
	"Valoracion Criterio": "sgc.permissions.pqc_valoracion_criterio",
	"Valoracion Estandar": "sgc.permissions.pqc_valoracion_estandar",
	"Plan Mejora": "sgc.permissions.pqc_plan_mejora",
}

has_permission = {
	"Autoevaluacion": "sgc.permissions.has_permission",
	"Hallazgo": "sgc.permissions.has_permission",
	"No Conformidad": "sgc.permissions.has_permission",
	"Salida No Conforme": "sgc.permissions.has_permission",
	"Valor Indicador": "sgc.permissions.has_permission",
	"Alerta Indicador": "sgc.permissions.has_permission",
	"Auditoria": "sgc.permissions.has_permission",
	"Comite": "sgc.permissions.has_permission",
	"Valoracion Criterio": "sgc.permissions.has_permission",
	"Valoracion Estandar": "sgc.permissions.has_permission",
	"Plan Mejora": "sgc.permissions.has_permission",
}

# DocType Class
# ---------------
# Deuda nativa conocida (docs/desarrollo/nativo-frappe.md): el adjunto de un
# documento de solo consulta no se entrega a quien solo puede leerlo, por ninguna
# puerta (#36). Ver sgc/documentos.py. No añadir otras sin pasar por esa política.
override_doctype_class = {
	"File": "sgc.documentos.FicheroSGC",
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
	# Contraseña con elementos seguros (B4): ver sgc/contrasena.py.
	"User": {"before_validate": "sgc.contrasena.antes_de_validar_usuario"},
	# Todo correo pasa por la cola: ahí se aplican el modo de ensayo, la lista blanca y
	# los adjuntos de solo consulta (sgc/correo.py).
	"Email Queue": {"before_insert": "sgc.correo.filtrar_cola"},
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
# Si el scheduler se para, estas tareas dejan de correr sin error: lo vigila
# `sgc.latido` desde el Desk y desde `sgc.verificacion`, no desde aquí (#42).
scheduler_events = {
	"daily": [
		"sgc.tasks.marcar_evidencias_vencidas",
		"sgc.tasks.marcar_acuerdos_vencidos",
		"sgc.sgc_documental.doctype.documento_controlado.documento_controlado.tareas_revision_diaria",
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
# `zip_files` entrega ficheros comprobando solo la lectura del `File`, no si se
# pueden descargar: sin esto, un documento de solo consulta saldría en un ZIP (#36).
override_whitelisted_methods = {
	"frappe.core.api.file.zip_files": "sgc.documentos.zip_files",
	# Restablecer/cambiar la contraseña y su medidor, con la regla de clases (B4).
	"frappe.core.doctype.user.user.update_password": "sgc.contrasena.update_password",
	"frappe.core.doctype.user.user.test_password_strength": "sgc.contrasena.test_password_strength",
}
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
