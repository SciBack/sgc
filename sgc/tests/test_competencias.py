# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests de las competencias y la calificación de auditores (`sgc/competencias.py`).

Cubre:
- La calificación: quién la otorga lo sella el sistema, nadie se califica a sí mismo, vence
  según la vigencia de la competencia, y revocarla exige motivo y sella quién la revocó.
- La tarea diaria pasa a «Vencida» lo vencido y deja en paz lo que no vence.
- La auditoría: sin competencias que habiliten el rol, entra en ejecución como antes; con
  ellas, no entra si un miembro no está calificado (o su calificación venció o se revocó), y
  sí cuando lo está. Una calificación que vence durante la ejecución no la bloquea.
- Las opciones de rol de la competencia son las del equipo auditor.
"""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, add_months, getdate, nowdate

from sgc import competencias
from sgc.tests import factories

ADMIN = "Administrator"
DOMINIO = "sgc-prueba-competencia.example.com"
AUDITOR = f"auditor@{DOMINIO}"
EVALUADOR = f"evaluador@{DOMINIO}"


def _usuario(correo, *roles):
	if frappe.db.exists("User", correo):
		return
	u = frappe.get_doc({"doctype": "User", "email": correo, "first_name": correo.split("@")[0],
						"send_welcome_email": 0})
	for rol in roles:
		u.append("roles", {"role": rol})
	u.insert(ignore_permissions=True)


class IntegrationTestCompetencias(IntegrationTestCase):
	def setUp(self):
		_usuario(AUDITOR, "Auditor Interno")
		_usuario(EVALUADOR, "DPGC")
		factories.desactivar_workflow("Auditoria")
		self.addCleanup(frappe.set_user, ADMIN)
		frappe.db.delete("Calificacion Personal")
		frappe.db.delete("Competencia")

	# -- ayudas -------------------------------------------------------------------------------
	def _competencia(self, rol="Auditor", vigencia=24, nombre="Auditor interno ISO 9001"):
		return frappe.get_doc({"doctype": "Competencia", "nombre": nombre, "habilita_rol": rol,
							   "vigencia_meses": vigencia}).insert(ignore_permissions=True)

	def _calificar(self, competencia, usuario=AUDITOR, fecha=None, **extra):
		frappe.set_user(EVALUADOR)
		try:
			return frappe.get_doc({
				"doctype": "Calificacion Personal", "usuario": usuario, "competencia": competencia,
				"base": "Formación", "sustento": "Curso de auditor interno ISO 19011 (40 h).",
				"fecha_otorgamiento": fecha or nowdate(), **extra,
			}).insert(ignore_permissions=True)
		finally:
			frappe.set_user(ADMIN)

	def _auditoria(self, rol="Auditor"):
		return frappe.get_doc({
			"doctype": "Auditoria", "titulo": "Auditoría de prueba de competencias", "tipo": "Interna",
			"estado": "Planificada",
			"equipo": [{"usuario": AUDITOR, "rol": rol, "independiente_del_area": 1}],
			"criterios": [{"tipo_criterio": "Clausula norma", "referencia": "ISO 9001 9.2"}],
		}).insert(ignore_permissions=True)

	def _iniciar(self, auditoria):
		auditoria.estado = "En ejecucion"
		auditoria.save(ignore_permissions=True)

	# -- calificación ---------------------------------------------------------------------------
	def test_quien_otorga_lo_sella_el_sistema_y_vence_segun_la_vigencia(self):
		cal = self._calificar(self._competencia(vigencia=24).name, otorgada_por=AUDITOR)
		self.assertEqual(cal.otorgada_por, EVALUADOR)
		self.assertEqual(getdate(cal.vence), getdate(add_months(nowdate(), 24)))
		self.assertEqual(cal.estado, competencias.VIGENTE)

	def test_sin_vigencia_no_vence(self):
		cal = self._calificar(self._competencia(vigencia=0).name)
		self.assertIsNone(cal.vence)
		self.assertEqual(cal.estado, competencias.VIGENTE)

	def test_nadie_se_califica_a_si_mismo(self):
		with self.assertRaises(frappe.ValidationError):
			self._calificar(self._competencia().name, usuario=EVALUADOR)

	def test_una_calificacion_antigua_nace_vencida(self):
		cal = self._calificar(self._competencia(vigencia=12).name, fecha=add_months(nowdate(), -13))
		self.assertEqual(cal.estado, competencias.VENCIDA)

	def test_revocar_exige_motivo_y_sella_quien(self):
		cal = self._calificar(self._competencia().name)
		cal.revocada = 1
		with self.assertRaises(frappe.ValidationError):
			cal.save(ignore_permissions=True)
		cal.reload()
		cal.revocada = 1
		cal.motivo_revocacion = "Dejó de cumplir el requisito de formación continua."
		cal.save(ignore_permissions=True)
		self.assertEqual((cal.estado, cal.revocada_por), (competencias.REVOCADA, ADMIN))

	def test_la_tarea_diaria_marca_lo_vencido_y_no_lo_que_no_vence(self):
		vence = self._calificar(self._competencia(vigencia=12, nombre="Con vigencia").name)
		no_vence = self._calificar(self._competencia(vigencia=0, nombre="Sin vigencia").name)
		frappe.db.set_value("Calificacion Personal", vence.name, "vence", add_days(nowdate(), -1), update_modified=False)
		with patch.object(frappe.db, "commit"):  # la tarea hace commit; el test no debe
			competencias.marcar_vencidas()
		self.assertEqual(frappe.db.get_value("Calificacion Personal", vence.name, "estado"), competencias.VENCIDA)
		self.assertEqual(frappe.db.get_value("Calificacion Personal", no_vence.name, "estado"), competencias.VIGENTE)

	# -- auditoría -------------------------------------------------------------------------------
	def test_sin_competencias_definidas_la_auditoria_entra_como_antes(self):
		auditoria = self._auditoria()
		self._iniciar(auditoria)
		self.assertEqual(auditoria.estado, "En ejecucion")

	def test_un_miembro_sin_calificar_no_deja_iniciar(self):
		self._competencia(rol="Auditor")
		with self.assertRaises(frappe.ValidationError):
			self._iniciar(self._auditoria())

	def test_calificado_entra_y_un_rol_no_exigido_tampoco_bloquea(self):
		self._calificar(self._competencia(rol="Auditor").name)
		auditoria = self._auditoria()
		self._iniciar(auditoria)
		self.assertEqual(auditoria.estado, "En ejecucion")
		# El observador no necesita calificación si ninguna competencia habilita ese rol.
		self._iniciar(self._auditoria(rol="Observador"))

	def test_vencida_o_revocada_no_vale(self):
		comp = self._competencia(rol="Auditor", vigencia=12)
		self._calificar(comp.name, fecha=add_months(nowdate(), -13))
		with self.assertRaises(frappe.ValidationError):
			self._iniciar(self._auditoria())

		frappe.db.delete("Calificacion Personal")
		self._calificar(comp.name, revocada=1, motivo_revocacion="Prueba.")
		with self.assertRaises(frappe.ValidationError):
			self._iniciar(self._auditoria())

	def test_una_competencia_inactiva_no_se_exige(self):
		comp = self._competencia(rol="Auditor")
		frappe.db.set_value("Competencia", comp.name, "activa", 0)
		auditoria = self._auditoria()
		self._iniciar(auditoria)
		self.assertEqual(auditoria.estado, "En ejecucion")

	def test_si_vence_durante_la_ejecucion_no_bloquea_la_auditoria(self):
		cal = self._calificar(self._competencia(rol="Auditor").name)
		auditoria = self._auditoria()
		self._iniciar(auditoria)
		frappe.db.set_value("Calificacion Personal", cal.name, "estado", competencias.VENCIDA, update_modified=False)
		auditoria.objetivo = "Se precisa el objetivo."
		auditoria.save(ignore_permissions=True)  # sigue en ejecución; no se vuelve a exigir

	# -- declaración -----------------------------------------------------------------------------
	def test_los_roles_de_la_competencia_son_los_del_equipo_auditor(self):
		equipo = set(frappe.get_meta("Equipo Auditoria").get_field("rol").options.split("\n")) - {""}
		competencia = set(frappe.get_meta("Competencia").get_field("habilita_rol").options.split("\n")) - {""}
		self.assertEqual(competencia, equipo)
