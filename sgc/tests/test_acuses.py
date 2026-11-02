# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests del acuse de lectura (`sgc/acuses.py`).

Cubre:
- Al publicar un documento que pide acuse, cada destinatario (difusión y dueño del proceso)
  recibe un acuse pendiente suyo, con su tarea; uno que no lo pide no crea nada; y no se
  puede publicar pidiendo acuse sin destinatarios.
- Confirmar sin preguntas exige la declaración y cierra la tarea.
- Con preguntas: el diálogo no recibe las respuestas correctas, ni el formulario se las
  da a quien solo lee; fallar deja el acuse pendiente y cuenta el intento; acertar lo cierra.
- Nadie confirma el acuse de otra persona.
- Una versión nueva deja sin efecto los pendientes (tarea cancelada) y se piden otra vez
  al publicarla.
"""

import frappe
from frappe.tests import IntegrationTestCase

from sgc import acuses, tareas
from sgc.tests import factories

DT = "Documento Controlado"
ADMIN = "Administrator"
DOMINIO = "sgc-prueba-acuse.example.com"
DUENO = f"dueno@{DOMINIO}"
LECTOR = f"lector@{DOMINIO}"
OTRO = f"otro@{DOMINIO}"
ARCHIVO = "/files/documento-prueba.pdf"
PREGUNTA = {"pregunta": "¿Quién aprueba el documento?", "opcion_a": "La DPGC", "opcion_b": "Cualquiera",
			"correcta": "A"}


def _usuario(correo, *roles):
	if frappe.db.exists("User", correo):
		return
	u = frappe.get_doc({"doctype": "User", "email": correo, "first_name": correo.split("@")[0],
						"send_welcome_email": 0})
	for rol in roles:
		u.append("roles", {"role": rol})
	u.insert(ignore_permissions=True)


class IntegrationTestAcuseLectura(IntegrationTestCase):
	def setUp(self):
		for correo, rol in ((DUENO, "Dueño de Proceso"), (LECTOR, "Decano/Director (lectura)"),
							(OTRO, "Decano/Director (lectura)")):
			_usuario(correo, rol)
		factories.desactivar_workflow(DT)
		self.addCleanup(frappe.set_user, ADMIN)
		self.proceso = factories.crear_proceso(prefijo="ACUP", responsable=DUENO).name

	# -- ayudas -------------------------------------------------------------------------------
	def _documento(self, requiere_acuse=1, difundir=(LECTOR,), preguntas=()):
		doc = factories.crear_documento_controlado(proceso=self.proceso, archivo=ARCHIVO, elaborado_por=ADMIN,
												   requiere_acuse=requiere_acuse)
		for usuario in difundir:
			doc.append("difundir_a", {"usuario": usuario})
		for p in preguntas:
			doc.append("preguntas_acuse", p)
		doc.save(ignore_permissions=True)
		return doc

	def _publicar(self, doc, descripcion=None):
		if descripcion:
			doc.descripcion_cambio = descripcion
		for estado, extra in (("En revision", {}), ("Aprobado", {"revisado_por": ADMIN}),
							  ("Publicado", {"aprobado_por": ADMIN})):
			doc.update({"estado": estado, **extra})
			doc.save(ignore_permissions=True)
		return doc

	def _acuse(self, doc, usuario):
		return frappe.get_doc("Acuse Lectura", {"documento": doc.name, "version": doc.version, "usuario": usuario})

	def _como(self, usuario):
		frappe.set_user(usuario)

	# -- pedir ---------------------------------------------------------------------------------
	def test_publicar_pide_el_acuse_a_cada_destinatario(self):
		doc = self._publicar(self._documento())
		pedidos = frappe.get_all("Acuse Lectura", filters={"documento": doc.name},
								 fields=["usuario", "owner", "estado", "version", "name"])
		self.assertEqual({p.usuario for p in pedidos}, {LECTOR, DUENO})
		for p in pedidos:
			self.assertEqual((p.owner, p.estado, p.version), (p.usuario, acuses.PENDIENTE, doc.version))
			abiertas = tareas.tareas_abiertas("Acuse Lectura", p.name)
			self.assertEqual([t.allocated_to for t in abiertas], [p.usuario])

	def test_un_documento_que_no_lo_pide_no_crea_acuses(self):
		doc = self._publicar(self._documento(requiere_acuse=0))
		self.assertFalse(frappe.db.exists("Acuse Lectura", {"documento": doc.name}))

	def test_no_se_publica_pidiendo_acuse_sin_destinatarios(self):
		frappe.db.set_value("Proceso", self.proceso, "responsable", None)
		doc = self._documento(difundir=())
		with self.assertRaises(frappe.ValidationError):
			self._publicar(doc)

	def test_el_formulario_lleva_a_quien_debe_confirmar(self):
		doc = self._publicar(self._documento())
		self._como(LECTOR)
		self.assertEqual(acuses.pendiente_de(frappe.get_doc(DT, doc.name)), self._acuse(doc, LECTOR).name)
		self._como(OTRO)
		self.assertIsNone(acuses.pendiente_de(frappe.get_doc(DT, doc.name)))

	# -- confirmar ------------------------------------------------------------------------------
	def test_sin_preguntas_basta_la_declaracion_y_cierra_la_tarea(self):
		doc = self._publicar(self._documento())
		acuse = self._acuse(doc, LECTOR)
		self._como(LECTOR)
		with self.assertRaises(frappe.ValidationError):
			acuses.acusar(acuse.name, declaro=0)
		resultado = acuses.acusar(acuse.name, declaro=1)
		self.assertTrue(resultado["aprobado"])
		acuse.reload()
		self.assertEqual(acuse.estado, acuses.ACUSADO)
		self.assertTrue(acuse.fecha_acuse)
		self.assertEqual(tareas.tareas_abiertas("Acuse Lectura", acuse.name), [])

	def test_nadie_confirma_el_acuse_de_otro(self):
		doc = self._publicar(self._documento())
		self._como(OTRO)
		with self.assertRaises(frappe.PermissionError):
			acuses.acusar(self._acuse(doc, LECTOR).name, declaro=1)

	def test_las_respuestas_correctas_no_llegan_a_quien_acusa(self):
		doc = self._publicar(self._documento(preguntas=[PREGUNTA]))
		self._como(LECTOR)
		datos = acuses.preguntas(self._acuse(doc, LECTOR).name)
		self.assertEqual(datos["preguntas"][0]["opciones"], [["A", "La DPGC"], ["B", "Cualquiera"]])
		self.assertNotIn("correcta", frappe.as_json(datos))

		cargado = frappe.get_doc(DT, doc.name)
		cargado.apply_fieldlevel_read_permissions()
		self.assertIsNone(cargado.preguntas_acuse[0].get("correcta"))

	def test_fallar_deja_el_acuse_pendiente_y_acertar_lo_cierra(self):
		otra = {"pregunta": "¿Cada cuánto se revisa?", "opcion_a": "Cada año", "opcion_b": "Nunca", "correcta": "A"}
		doc = self._publicar(self._documento(preguntas=[PREGUNTA, otra]))
		acuse = self._acuse(doc, LECTOR)
		self._como(LECTOR)

		mal = acuses.acusar(acuse.name, respuestas={"1": "A", "2": "B"}, declaro=1)
		self.assertEqual((mal["aprobado"], mal["puntaje"], mal["aciertos"]), (False, 50.0, 1))
		acuse.reload()
		self.assertEqual((acuse.estado, acuse.intentos), (acuses.PENDIENTE, 1))
		self.assertTrue(tareas.tareas_abiertas("Acuse Lectura", acuse.name))

		bien = acuses.acusar(acuse.name, respuestas='{"1": "A", "2": "A"}', declaro=1)
		self.assertTrue(bien["aprobado"])
		acuse.reload()
		self.assertEqual((acuse.estado, acuse.intentos, acuse.puntaje), (acuses.ACUSADO, 2, 100))

	def test_la_respuesta_correcta_tiene_que_ser_una_opcion_escrita(self):
		mala = dict(PREGUNTA, correcta="C")
		with self.assertRaises(frappe.ValidationError):
			self._documento(preguntas=[mala])

	# -- versiones ------------------------------------------------------------------------------
	def test_una_version_nueva_deja_sin_efecto_y_vuelve_a_pedir(self):
		doc = self._publicar(self._documento())
		viejo = self._acuse(doc, LECTOR)

		doc.estado = "Borrador"  # «Nueva version»
		doc.save(ignore_permissions=True)
		viejo.reload()
		self.assertEqual(viejo.estado, acuses.SIN_EFECTO)
		self.assertEqual(tareas.tareas_abiertas("Acuse Lectura", viejo.name), [])
		self.assertEqual(frappe.db.get_value("ToDo", {"reference_type": "Acuse Lectura", "reference_name": viejo.name},
											 "status"), tareas.CANCELADA)

		doc = self._publicar(doc, descripcion="Se aclara quién aprueba.")
		self.assertEqual(doc.version, 2)
		nuevo = self._acuse(doc, LECTOR)
		self.assertEqual(nuevo.estado, acuses.PENDIENTE)
		self.assertNotEqual(nuevo.name, viejo.name)

	def test_lo_acusado_de_una_version_anterior_se_conserva(self):
		doc = self._publicar(self._documento())
		acuse = self._acuse(doc, LECTOR)
		self._como(LECTOR)
		acuses.acusar(acuse.name, declaro=1)
		self._como(ADMIN)

		doc.reload()
		doc.estado = "Borrador"
		doc.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("Acuse Lectura", acuse.name, "estado"), acuses.ACUSADO)
