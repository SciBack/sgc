"""Crea los módulos de las áreas nuevas ANTES de sincronizar los DocTypes (12-oct-2026).

Los menús del SGC pasaron de agruparse por módulo técnico a agruparse por tarea, y para
eso varias pantallas cambian de módulo: entran «SGC Documental», «SGC Indicadores» y
«SGC Acreditacion». Frappe crea los `Module Def` solo al INSTALAR una app
(`installer.add_module_defs`), no en `migrate`. Un sitio existente que sincroniza un
DocType cuyo módulo aún no existe falla: `DocType.module` es un Link a `Module Def`.

Va en `pre_model_sync` por eso: tiene que existir el módulo antes de que `sync_all`
importe el JSON movido.

También reconstruye el mapa de módulos. Frappe lo lee al arrancar de la caché de Redis
(`setup_module_map`), donde sigue la lista de la imagen anterior, y el `clear_cache`
del migrate llega después. Con el mapa viejo, el JSON de un módulo nuevo no se puede
resolver a su carpeta. Así se cayó el despliegue de la v173 al retirar «SGC UPeU».
"""

import frappe


def execute():
	frappe.cache.delete_value("app_modules")
	frappe.client_cache.delete_value("installed_app_modules")
	frappe.setup_module_map(include_all_apps=True)
	frappe.setup_module_map(include_all_apps=False)

	for modulo in frappe.get_module_list("sgc"):
		if not frappe.db.exists("Module Def", modulo):
			frappe.get_doc({"doctype": "Module Def", "module_name": modulo, "app_name": "sgc"}).insert(
				ignore_permissions=True
			)
			print(f"Module Def «{modulo}»: creado")
