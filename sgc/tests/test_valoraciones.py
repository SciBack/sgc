# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests de la valoración de la atención por quien reclamó (`sgc/valoraciones.py`).

Cubre:
- Cerrar una salida no conforme que vino de un reclamo con correo crea la solicitud (clave,
  caducidad y la salida fijada en `doc_values`) y envía el enlace SIN referencia al documento;
  si el correo sale, queda «Valoración solicitada».
- No se pide si no es un reclamo, si no hay correo o si ya se pidió; y si la lista blanca o el
  modo de ensayo retienen el correo, no se marca como solicitada.
- El formulario web, como invitado y con la clave, crea la valoración enlazada a SU salida
  (aunque el formulario intente mandar otra); la clave sirve una vez; sin clave no entra.
- La tarjeta da N/A sin valoraciones y la media en porcentaje con ellas.
- La valoración entra en la revisión por la dirección como entrada de §9.3.2 c).
"""

import json
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import get_datetime, now_datetime
from frappe.website.doctype.web_form.web_form import accept

from sgc import dashboards, valoraciones
from sgc.sgc_gobierno.doctype.revision_direccion.revision_direccion import FUENTES_DE_ENTRADA
from sgc.tests import factories

DT = "Salida No Conforme"
ADMIN = "Administrator"
RECLAMANTE = "reclamante@sgc-prueba-valoracion.example.com"
ENVIADO = {"enviados": [RECLAMANTE], "retenidos": []}


class IntegrationTestValoracionAtencion(IntegrationTestCase):
	def setUp(self):
		factories.desactivar_workflow(DT)
		self.addCleanup(frappe.set_user, ADMIN)
		self.proceso = factories.crear_proceso(prefijo="VALP").name
		self.evidencia = factories.crear_evidencia().name

	# -- ayudas -------------------------------------------------------------------------------
	def _salida(self, origen=valoraciones.ORIGEN_RECLAMO, correo=RECLAMANTE):
		doc = frappe.get_doc({
			"doctype": DT, "titulo": "Constancia entregada con datos errados", "origen": origen,
			"proceso": self.proceso, "descripcion": "La constancia salió con el DNI equivocado.",
			"requisito_incumplido": "Datos personales correctos.", "correo_reclamante": correo,
		}).insert(ignore_permissions=True)
		frappe.db.set_value(DT, doc.name, {
			"estado": "Verificada", "responsable": ADMIN, "decision": "Corregir",
			"acciones_tomadas": "Se emitió una constancia nueva.", "verificacion_conformidad": 1,
			"evidencia_tratamiento": self.evidencia,
		}, update_modified=False)
		return frappe.get_doc(DT, doc.name)

	def _cerrar(self, salida):
		salida.estado = "Cerrada"
		salida.save(ignore_permissions=True)
		return salida

	def _solicitud(self, salida):
		nombre = frappe.db.get_value("Web Form Request", {"web_form": valoraciones.FORMULARIO,
														 "doc_values": ["like", f"%{salida.name}%"]})
		return frappe.get_doc("Web Form Request", nombre) if nombre else None

	def _responder(self, key, **datos):
		frappe.set_user("Guest")
		try:
			return accept(valoraciones.FORMULARIO, json.dumps(datos), web_form_request_key=key)
		finally:
			frappe.set_user(ADMIN)

	# -- pedir ---------------------------------------------------------------------------------
	def test_cerrar_un_reclamo_pide_la_valoracion_sin_dejar_el_enlace_en_el_documento(self):
		with patch.object(valoraciones.correo, "enviar", return_value=ENVIADO) as enviar:
			salida = self._cerrar(self._salida())
		solicitud = self._solicitud(salida)
		self.assertTrue(solicitud and solicitud.key)
		self.assertEqual(json.loads(solicitud.doc_values), {"salida_no_conforme": salida.name})
		self.assertGreater(get_datetime(solicitud.expires_on), now_datetime())

		args, kwargs = enviar.call_args
		self.assertEqual(args[0], [RECLAMANTE])
		self.assertIn(solicitud.key, args[2])
		self.assertNotIn("documento", kwargs)
		self.assertNotIn("documento_tipo", kwargs)
		self.assertTrue(frappe.db.get_value(DT, salida.name, "valoracion_solicitada"))

	def test_no_se_pide_si_no_es_reclamo_o_no_hay_correo(self):
		with patch.object(valoraciones.correo, "enviar", return_value=ENVIADO) as enviar:
			interna = self._cerrar(self._salida(origen="Interno"))
			sin_correo = self._cerrar(self._salida(correo=None))
		enviar.assert_not_called()
		self.assertIsNone(self._solicitud(interna))
		self.assertIsNone(self._solicitud(sin_correo))

	def test_si_el_correo_queda_retenido_no_se_marca_como_solicitada(self):
		retenido = {"enviados": [], "retenidos": [(RECLAMANTE, "Omitido")]}
		with patch.object(valoraciones.correo, "enviar", return_value=retenido):
			salida = self._cerrar(self._salida())
		self.assertFalse(frappe.db.get_value(DT, salida.name, "valoracion_solicitada"))

	def test_no_se_pide_dos_veces(self):
		with patch.object(valoraciones.correo, "enviar", return_value=ENVIADO) as enviar:
			salida = self._cerrar(self._salida())
			salida.reload()
			self.assertIsNone(valoraciones.pedir(salida))
		self.assertEqual(enviar.call_count, 1)

	# -- responder ------------------------------------------------------------------------------
	def test_el_reclamante_valora_su_salida_y_la_clave_sirve_una_vez(self):
		with patch.object(valoraciones.correo, "enviar", return_value=ENVIADO):
			salida = self._cerrar(self._salida())
			otra = self._cerrar(self._salida())
		key = self._solicitud(salida).key

		# Aunque el formulario mande otra salida, manda la que fijó el servidor.
		self._responder(key, valoracion=0.8, resuelto="Sí", comentario="Rápido y amable.",
						salida_no_conforme=otra.name)
		valoracion = frappe.get_doc("Valoracion Atencion", {"salida_no_conforme": salida.name})
		self.assertEqual((float(valoracion.valoracion), valoracion.resuelto), (0.8, "Sí"))
		self.assertEqual(valoracion.proceso, self.proceso)
		self.assertFalse(frappe.db.exists("Valoracion Atencion", {"salida_no_conforme": otra.name}))

		with self.assertRaises(frappe.exceptions.LinkExpired):
			self._responder(key, valoracion=0.2, resuelto="No")

	def test_la_pagina_del_formulario_se_ve_con_la_clave(self):
		"""Renderiza la página como invitado: así se vio el 417 de `condition_json` en PostgreSQL."""
		from frappe.website.serve import get_response
		from werkzeug.test import EnvironBuilder
		from werkzeug.wrappers import Request

		with patch.object(valoraciones.correo, "enviar", return_value=ENVIADO):
			salida = self._cerrar(self._salida())
		key = self._solicitud(salida).key
		ruta = f"{valoraciones.FORMULARIO}/new"
		anterior = getattr(frappe.local, "request", None)
		# `set_user` vacía `form_dict` (frappe/__init__.py::set_user): la clave va después.
		frappe.set_user("Guest")
		frappe.local.request = Request(EnvironBuilder(path=f"/{ruta}", query_string={"web_form_request_key": key}).get_environ())
		frappe.local.form_dict = frappe._dict(web_form_request_key=key)
		try:
			respuesta = get_response(ruta)
		finally:
			# Sin devolver la petición, el limitador de `accept` se activa en los tests siguientes.
			frappe.local.request = anterior
			frappe.set_user(ADMIN)
		self.assertEqual(respuesta.status_code, 200)

	def test_sin_clave_no_entra(self):
		with self.assertRaises(frappe.PermissionError):
			self._responder(None, valoracion=1, resuelto="Sí")

	def test_no_se_valora_sin_salida_ni_dos_veces(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "Valoracion Atencion", "valoracion": 1, "resuelto": "Sí"}).insert(
				ignore_permissions=True)
		salida = self._salida()
		frappe.get_doc({"doctype": "Valoracion Atencion", "salida_no_conforme": salida.name, "valoracion": 1,
						"resuelto": "Sí"}).insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "Valoracion Atencion", "salida_no_conforme": salida.name,
							"valoracion": 0.4, "resuelto": "No"}).insert(ignore_permissions=True)

	# -- cifras y revisión ----------------------------------------------------------------------
	def test_la_tarjeta_da_na_y_la_media_en_porcentaje(self):
		frappe.db.delete("Valoracion Atencion")
		self.assertEqual(dashboards.satisfaccion_reclamos(), {"value": None, "fieldtype": "Percent"})
		for valor in (1, 0.6):
			frappe.get_doc({"doctype": "Valoracion Atencion", "salida_no_conforme": self._salida().name,
							"valoracion": valor, "resuelto": "Sí"}).insert(ignore_permissions=True)
		self.assertEqual(dashboards.satisfaccion_reclamos()["value"], 80.0)

	def test_entra_en_la_revision_por_la_direccion(self):
		self.assertEqual(FUENTES_DE_ENTRADA["Valoracion Atencion"], "Desempeno y eficacia del SGC")

	def test_el_formulario_exige_clave_y_no_pide_cuenta(self):
		formulario = frappe.get_doc("Web Form", valoraciones.FORMULARIO)
		self.assertEqual((formulario.key_required, formulario.login_required, formulario.published), (1, 0, 1))
		self.assertNotIn("salida_no_conforme", [f.fieldname for f in formulario.web_form_fields])
		# Con «[]», en PostgreSQL la página falla al renderizarse (ver sgc/valoraciones.py).
		self.assertFalse(formulario.condition_json)
