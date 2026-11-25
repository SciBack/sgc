# Copyright (c) 2026, SciBack and Contributors
# See license.txt

import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests import IntegrationTestCase

from sgc.tests import factories


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]

# Acciones del Workflow "Autoevaluacion SGC" en orden, hasta "Cerrada"
# (ver el workflow «Autoevaluacion SGC» de sgc/fixtures/workflow.json).
_CADENA_CIERRE = ("Iniciar evaluacion", "Enviar a revision", "Consolidar", "Cerrar")


def _cerrar_autoevaluacion(autoevaluacion):
	"""Recorre la cadena REAL de transiciones del workflow hasta dejar la
	Autoevaluacion en 'Cerrada' (docstatus=1).

	Un `.save()` normal con `estado` reasignado a mano NO dispara el submit --
	`Document.validate_workflow()` solo invoca `set_workflow_state_on_action`
	cuando `self._action != "save"` (confirmado leyendo
	frappe/model/workflow.py). El único camino real es
	`frappe.model.workflow.apply_workflow(doc, accion)`: para la transición
	cuyo next_state tiene doc_status="1" (aquí, "Cerrar" -> "Cerrada"), esa
	función llama `doc.submit()` explícitamente.

	Requiere que el Workflow 'Autoevaluacion SGC' siga ACTIVO (no llamar
	`factories.desactivar_workflow("Autoevaluacion")` antes de esto).
	Devuelve el doc recargado, ya con docstatus=1.
	"""
	name = autoevaluacion.name if hasattr(autoevaluacion, "name") else autoevaluacion
	# cerrar promueve la vigencia y esta exige todos los estandares confirmados
	# (Tabla 9 del modelo CONEAU): sin ellos el cierre falla.
	factories.confirmar_todo_para_cierre(name)
	doc = frappe.get_doc("Autoevaluacion", name)
	for accion in _CADENA_CIERRE:
		doc = apply_workflow(doc, accion)
	doc.reload()
	return doc


class IntegrationTestValoracionCriterio(IntegrationTestCase):
	"""
	Integration tests for ValoracionCriterio.
	Use this class for testing interactions between multiple components.
	"""

	def test_estado_se_deriva_del_juicio_y_no_del_cliente(self):
		"""El cliente solo expresa el juicio; el servidor gobierna el estado.

		Una valoración con juicio queda ``Valorado`` aunque el navegador intente
		mandar otro estado. Al retirar el juicio vuelve a ``Pendiente``.
		"""
		prefijo = "TESTVC0"
		marco = factories.crear_marco_prueba(n_estandares=1, n_criterios=1, prefijo=prefijo)
		ae = factories.crear_autoevaluacion(marco, prefijo=prefijo)
		criterio = marco["criterios"][marco["estandares"][0]][0]

		vc = frappe.get_doc({
			"doctype": "Valoracion Criterio",
			"autoevaluacion": ae.name,
			"criterio": criterio,
			"cumple": "Cumple",
			"estado": "Revisado",
		}).insert(ignore_permissions=True)
		self.assertEqual(vc.estado, "Valorado")
		self.assertEqual(vc.valorado_por, "Administrator")
		self.assertTrue(vc.fecha)

		vc.cumple = None
		vc.estado = "En analisis"
		vc.save(ignore_permissions=True)
		self.assertEqual(vc.estado, "Pendiente")
		self.assertFalse(vc.valorado_por)
		self.assertFalse(vc.fecha)

	def test_valorar_criterio_en_borrador_funciona_normal(self):
		"""Con la Autoevaluacion en Planificada (docstatus=0), crear y editar una
		Valoracion Criterio funciona sin cambios de comportamiento (guard no aplica)."""
		prefijo = "TESTVC1"
		marco = factories.crear_marco_prueba(n_estandares=1, n_criterios=1, prefijo=prefijo)
		ae = factories.crear_autoevaluacion(marco, prefijo=prefijo)
		criterio = marco["criterios"][marco["estandares"][0]][0]

		vc = factories.valorar_criterio(ae, criterio, cumple="Cumple")
		self.assertEqual(vc.cumple, "Cumple")

		# Reeditar (sigue en Planificada) -> no debe lanzar.
		vc.cumple = "No cumple"
		vc.save()
		self.assertEqual(
			frappe.db.get_value("Valoracion Criterio", vc.name, "cumple"), "No cumple"
		)

	def test_valorar_un_criterio_actualiza_el_avance(self):
		"""El avance se ve mientras se valora, no solo al cerrar (25-nov-2026: con 5 de 53
		criterios valorados la autoevaluación marcaba 0 %)."""
		prefijo = "TESTVCAV"
		marco = factories.crear_marco_prueba(n_estandares=1, n_criterios=4, prefijo=prefijo)
		ae = factories.crear_autoevaluacion(marco, prefijo=prefijo)
		criterios = marco["criterios"][marco["estandares"][0]]

		factories.valorar_criterio(ae, criterios[0], cumple="Cumple")
		self.assertEqual(frappe.db.get_value("Autoevaluacion", ae.name, "avance_pct"), 25.0)

		factories.valorar_criterio(ae, criterios[1], cumple="Cumple parcial")
		self.assertEqual(frappe.db.get_value("Autoevaluacion", ae.name, "avance_pct"), 50.0)

		# «No aplica» no es un juicio de cumplimiento: no suma (misma regla que el motor).
		factories.valorar_criterio(ae, criterios[2], cumple="No aplica")
		self.assertEqual(frappe.db.get_value("Autoevaluacion", ae.name, "avance_pct"), 50.0)

	# ------------------------------------------------ valoración por evidencias (1.8.0)

	def _marco_con_evidencias(self, prefijo, codigos=("EV1", "EV2")):
		marco = factories.crear_marco_prueba(n_estandares=1, n_criterios=2, prefijo=prefijo)
		criterio = marco["criterios"][marco["estandares"][0]][0]
		em = frappe.get_doc("Elemento Marco", criterio)
		em.set("evidencias_esperadas", [{"codigo": c, "descripcion": f"Evidencia {c}"} for c in codigos])
		em.save(ignore_permissions=True)
		return marco, criterio

	def _valoracion(self, ae, criterio):
		return frappe.get_doc({"doctype": "Valoracion Criterio", "autoevaluacion": ae.name, "criterio": criterio,
							   "cumple": ""}).insert(ignore_permissions=True)

	def test_la_valoracion_trae_las_evidencias_esperadas_del_criterio(self):
		marco, criterio = self._marco_con_evidencias("TESTVE1")
		ae = factories.crear_autoevaluacion(marco, prefijo="TESTVE1")
		vc = self._valoracion(ae, criterio)
		self.assertEqual([f.codigo for f in vc.evidencias_valoradas], ["EV1", "EV2"])
		self.assertEqual({f.valoracion for f in vc.evidencias_valoradas}, {"Pendiente"})
		self.assertEqual(vc.cumple or "", "")  # con evidencias pendientes, el criterio no se valora
		self.assertEqual(vc.estado, "Pendiente")

		# Idempotente: guardar otra vez no duplica filas, y una evidencia nueva del marco se añade.
		vc.save()
		self.assertEqual(len(vc.evidencias_valoradas), 2)
		em = frappe.get_doc("Elemento Marco", criterio)
		em.append("evidencias_esperadas", {"codigo": "EV3", "descripcion": "Evidencia EV3"})
		em.save(ignore_permissions=True)
		vc.reload()
		vc.save()
		self.assertEqual([f.codigo for f in vc.evidencias_valoradas], ["EV1", "EV2", "EV3"])

	def test_el_avance_de_cada_evidencia_valora_la_evidencia_y_el_criterio(self):
		marco, criterio = self._marco_con_evidencias("TESTVE2")
		ae = factories.crear_autoevaluacion(marco, prefijo="TESTVE2")
		vc = self._valoracion(ae, criterio)

		vc.evidencias_valoradas[0].avance = 100
		vc.save()
		self.assertEqual(vc.evidencias_valoradas[0].valoracion, "Logrado")
		self.assertEqual(vc.cumple or "", "")  # EV2 sigue pendiente

		vc.evidencias_valoradas[1].avance = 50
		vc.save()
		self.assertEqual(vc.evidencias_valoradas[1].valoracion, "En proceso")
		self.assertEqual(vc.avance_criterio, 75)
		self.assertEqual(vc.cumple, "Cumple")  # promedio 75 % → logrado
		self.assertEqual(vc.estado, "Valorado")

		vc.evidencias_valoradas[0].avance = 20
		vc.save()
		self.assertEqual(vc.evidencias_valoradas[0].valoracion, "No logrado")
		self.assertEqual(vc.cumple, "Cumple parcial")  # promedio 35 %

	def test_cero_por_ciento_exige_la_brecha_y_no_aplica_no_cuenta(self):
		marco, criterio = self._marco_con_evidencias("TESTVE3")
		ae = factories.crear_autoevaluacion(marco, prefijo="TESTVE3")
		vc = self._valoracion(ae, criterio)

		# 0 % sin brecha es «sin valorar»; con la brecha escrita es un 0 % de verdad.
		vc.evidencias_valoradas[0].observacion = "No existe el documento"
		vc.evidencias_valoradas[1].no_aplica = 1
		vc.save()
		self.assertEqual(vc.evidencias_valoradas[0].valoracion, "No logrado")
		self.assertEqual(vc.evidencias_valoradas[1].valoracion, "No aplica")
		self.assertEqual(vc.cumple, "No cumple")

		vc.evidencias_valoradas[0].no_aplica = 1
		vc.save()
		self.assertEqual(vc.cumple, "No aplica")

	def test_el_avance_de_la_autoevaluacion_es_el_promedio_de_sus_evidencias(self):
		from sgc import scoring

		marco, criterio = self._marco_con_evidencias("TESTVE4", codigos=("EV1", "EV2", "EV3"))
		ae = factories.crear_autoevaluacion(marco, prefijo="TESTVE4")
		vc = self._valoracion(ae, criterio)
		vc.evidencias_valoradas[0].avance = 90
		vc.evidencias_valoradas[1].avance = 30
		vc.evidencias_valoradas[2].no_aplica = 1
		vc.save()
		# (90 + 30) / 2 aplicables: la que no aplica no cuenta.
		self.assertEqual(scoring.avance_por_evidencias(ae.name), 60.0)
		self.assertEqual(frappe.db.get_value("Autoevaluacion", ae.name, "avance_pct"), 60.0)

	def test_la_evidencia_aportada_en_una_fila_entra_en_la_trazabilidad(self):
		marco, criterio = self._marco_con_evidencias("TESTVE5")
		ae = factories.crear_autoevaluacion(marco, prefijo="TESTVE5")
		ev = factories.crear_evidencia(prefijo="TESTVE5")
		vc = self._valoracion(ae, criterio)
		vc.evidencias_valoradas[0].evidencia = ev.name
		vc.evidencias_valoradas[0].avance = 100
		vc.save()
		self.assertTrue(frappe.db.exists("Trazabilidad", {"evidencia": ev.name, "elemento_marco": criterio}))

	def test_los_informes_de_avance_cuentan_lo_valorado(self):
		from sgc.sgc_acreditacion.report.avance_de_autoevaluaciones import avance_de_autoevaluaciones
		from sgc.sgc_acreditacion.report.avance_por_estandar import avance_por_estandar

		marco, criterio = self._marco_con_evidencias("TESTVE6")
		ae = factories.crear_autoevaluacion(marco, prefijo="TESTVE6")
		frappe.db.set_value("Autoevaluacion", ae.name, "estado", "En curso")
		vc = self._valoracion(ae, criterio)
		vc.evidencias_valoradas[0].avance = 100
		vc.evidencias_valoradas[1].avance = 100
		vc.save()

		_c, filas, _m, grafico, resumen = avance_por_estandar.execute({"autoevaluacion": ae.name})
		self.assertEqual(len(filas), 1)
		self.assertEqual(filas[0]["avance"], 100.0)
		self.assertEqual(filas[0]["semaforo"], "Logrado")
		self.assertEqual(filas[0]["logrados"], 1)
		self.assertEqual(filas[0]["pendientes"], 1)  # el otro criterio del estándar no tiene evidencias ni juicio
		self.assertTrue(grafico and resumen)

		_c, filas, *_ = avance_de_autoevaluaciones.execute({"marco_normativo": marco["marco"]})
		fila = next(f for f in filas if f["autoevaluacion"] == ae.name)
		self.assertEqual(fila["avance"], 100.0)
		self.assertEqual(fila["logrados"], 1)

	def test_la_lista_de_valoraciones_dice_de_que_autoevaluacion_son(self):
		"""Las valoraciones se abren desde su autoevaluación y no están en el menú: la lista
		tiene que mostrar a cuál pertenecen, con enlace de vuelta (Frappe 16.60 no pinta esa
		miga: solo nombra la pantalla)."""
		for doctype in ("Valoracion Criterio", "Valoracion Estandar"):
			campo = frappe.get_meta(doctype).get_field("autoevaluacion")
			self.assertTrue(campo.in_list_view, doctype)

	def test_bloquea_edicion_de_valoracion_existente_tras_cierre(self):
		"""Tras recorrer la cadena real hasta 'Cerrada' (docstatus=1), editar una
		Valoracion Criterio ya existente de esa autoevaluacion lanza ValidationError."""
		prefijo = "TESTVC2"
		marco = factories.crear_marco_prueba(n_estandares=1, n_criterios=1, prefijo=prefijo)
		ae = factories.crear_autoevaluacion(marco, prefijo=prefijo)
		criterio = marco["criterios"][marco["estandares"][0]][0]

		vc = factories.valorar_criterio(ae, criterio, cumple="Cumple")

		_cerrar_autoevaluacion(ae)

		vc.reload()
		vc.cumple = "No cumple"
		with self.assertRaises(frappe.ValidationError):
			vc.save()

	def test_bloquea_creacion_de_valoracion_nueva_tras_cierre(self):
		"""Tras el cierre, crear una Valoracion Criterio NUEVA ligada a esa
		autoevaluacion también lanza ValidationError (insert pasa por validate()
		igual que save(), es el mismo guard)."""
		prefijo = "TESTVC3"
		marco = factories.crear_marco_prueba(n_estandares=1, n_criterios=1, prefijo=prefijo)
		ae = factories.crear_autoevaluacion(marco, prefijo=prefijo)
		criterio = marco["criterios"][marco["estandares"][0]][0]

		_cerrar_autoevaluacion(ae)

		nueva = frappe.get_doc({
			"doctype": "Valoracion Criterio",
			"autoevaluacion": ae.name,
			"criterio": criterio,
			"cumple": "Cumple",
		})
		with self.assertRaises(frappe.ValidationError):
			nueva.insert()

	# ------------------------------------------------------- puente Trazabilidad

	def test_vincular_evidencia_al_valorar_crea_trazabilidad(self):
		"""RNF09: el picklist `evidencia` de la valoración genera su Trazabilidad
		hacia el criterio, con origen 'Auto-sincronizado'."""
		prefijo = "TESTVC4"
		marco = factories.crear_marco_prueba(n_estandares=1, n_criterios=1, prefijo=prefijo)
		ae = factories.crear_autoevaluacion(marco, prefijo=prefijo)
		criterio = marco["criterios"][marco["estandares"][0]][0]
		ev = factories.crear_evidencia(prefijo=prefijo)

		# `factories.valorar_criterio` no acepta overrides -> se construye el doc.
		frappe.get_doc({
			"doctype": "Valoracion Criterio",
			"autoevaluacion": ae.name,
			"criterio": criterio,
			"cumple": "Cumple",
			"evidencia": [{"evidencia": ev.name}],
		}).insert(ignore_permissions=True)

		traza = frappe.db.get_value(
			"Trazabilidad",
			{"evidencia": ev.name, "elemento_marco": criterio},
			["name", "origen"],
			as_dict=True,
		)
		self.assertTrue(traza, "el puente autoevaluación -> Trazabilidad no creó el vínculo")
		self.assertEqual(traza.origen, "Auto-sincronizado")

	def test_sincronizacion_de_evidencia_es_idempotente(self):
		"""Re-guardar la valoración no duplica la Trazabilidad (patrón `db.exists`)."""
		prefijo = "TESTVC5"
		marco = factories.crear_marco_prueba(n_estandares=1, n_criterios=1, prefijo=prefijo)
		ae = factories.crear_autoevaluacion(marco, prefijo=prefijo)
		criterio = marco["criterios"][marco["estandares"][0]][0]
		ev = factories.crear_evidencia(prefijo=prefijo)

		vc = frappe.get_doc({
			"doctype": "Valoracion Criterio",
			"autoevaluacion": ae.name,
			"criterio": criterio,
			"cumple": "Cumple",
			"evidencia": [{"evidencia": ev.name}],
		}).insert(ignore_permissions=True)

		vc.observacion = "Se ajusta el sustento"
		vc.save(ignore_permissions=True)
		vc.observacion = "Se ajusta otra vez"
		vc.save(ignore_permissions=True)

		self.assertEqual(
			frappe.db.count("Trazabilidad", {"evidencia": ev.name, "elemento_marco": criterio}),
			1,
		)

	def test_evidencia_de_la_valoracion_llega_al_informe_sineace(self):
		"""El motor del informe (sgc.informe) lee la Trazabilidad del criterio y
		la muestra bajo su estándar padre — el puente completo, extremo a extremo."""
		from sgc import informe

		prefijo = "TESTVC6"
		marco = factories.crear_marco_prueba(n_estandares=1, n_criterios=1, prefijo=prefijo)
		ae = factories.crear_autoevaluacion(marco, prefijo=prefijo)
		criterio = marco["criterios"][marco["estandares"][0]][0]
		ev = factories.crear_evidencia(prefijo=prefijo)

		frappe.get_doc({
			"doctype": "Valoracion Criterio",
			"autoevaluacion": ae.name,
			"criterio": criterio,
			"cumple": "Cumple",
			"evidencia": [{"evidencia": ev.name}],
		}).insert(ignore_permissions=True)

		ctx = informe.consolidar(ae.name)
		codigos = {e["ev_id"] for e in ctx["todas_evidencias"]}
		self.assertIn(ev.codigo, codigos)
		# Y aparece en el bloque del estándar padre, no solo en el anexo global.
		por_estandar = {e["ev_id"] for est in ctx["estandares"] for e in est["evidencias"]}
		self.assertIn(ev.codigo, por_estandar)

	def test_autoevaluacion_cerrada_no_genera_trazabilidad_nueva(self):
		"""El sync corre DESPUÉS del guard de cierre: una autoevaluación cerrada
		ni siquiera llega a crear la Trazabilidad."""
		prefijo = "TESTVC7"
		marco = factories.crear_marco_prueba(n_estandares=1, n_criterios=1, prefijo=prefijo)
		ae = factories.crear_autoevaluacion(marco, prefijo=prefijo)
		criterio = marco["criterios"][marco["estandares"][0]][0]
		ev = factories.crear_evidencia(prefijo=prefijo)

		_cerrar_autoevaluacion(ae)

		nueva = frappe.get_doc({
			"doctype": "Valoracion Criterio",
			"autoevaluacion": ae.name,
			"criterio": criterio,
			"cumple": "Cumple",
			"evidencia": [{"evidencia": ev.name}],
		})
		with self.assertRaises(frappe.ValidationError):
			nueva.insert()

		self.assertFalse(
			frappe.db.exists("Trazabilidad", {"evidencia": ev.name, "elemento_marco": criterio})
		)
