# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Gestión documental: los cinco requisitos que estaban a medias.

  Carpetas       — árbol libre, el documento se archiva en una carpeta
  Relacionados   — documentos vinculados entre sí, sin autovínculo ni repetidos
  Observaciones  — observar exige texto; queda sellado (quién, cuándo, paso, versión)
  Revisión       — tarea al responsable antes de que venza la vigencia; «revisión
                   sin cambios» renueva la vigencia, deja constancia y cierra la tarea
  Difusión       — la publicación avisa también al dueño del proceso y a quien
                   el documento nombra

Todo se deshace al final de la clase (rollback de IntegrationTestCase).
"""

import frappe
from frappe.email.doctype.notification.notification import get_context
from frappe.model.workflow import apply_workflow
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, add_years, getdate, nowdate

from sgc import tareas
from sgc.setup import f5_workflow_documental as f5
from sgc.setup import f15_notificaciones_workflow as f15
from sgc.sgc_nucleo.doctype.documento_controlado.documento_controlado import (
    DIAS_TAREA_REVISION,
    tareas_revision_diaria,
)
from sgc.tests import factories

DT = "Documento Controlado"
DOMINIO = "sgc-prueba-doc.example.com"
DUENO = f"dueno@{DOMINIO}"
ELABORA = f"elabora@{DOMINIO}"
DPGC = f"dpgc@{DOMINIO}"
INTERESADO = f"interesado@{DOMINIO}"
OTRO = f"otro@{DOMINIO}"
R_PUBLICADO = "SGC - Documento Controlado publicado"


def _usuario(correo, *roles):
    if frappe.db.exists("User", correo):
        return
    u = frappe.get_doc({"doctype": "User", "email": correo, "first_name": correo.split("@")[0],
                        "send_welcome_email": 0})
    for rol in roles:
        u.append("roles", {"role": rol})
    u.insert(ignore_permissions=True)


class _Base(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        f5.run()
        f15.run()
        frappe.flags.in_patch = False

    def setUp(self):
        for correo, rol in ((DUENO, "Dueño de Proceso"), (ELABORA, "Dueño de Proceso"),
                            (DPGC, "DPGC"), (INTERESADO, "Decano/Director (lectura)"),
                            (OTRO, "Decano/Director (lectura)")):
            _usuario(correo, rol)
        self.proceso = factories.crear_proceso(prefijo="DOCP", responsable=DUENO).name

    def tearDown(self):
        frappe.set_user("Administrator")

    def _como(self, usuario):
        frappe.set_user(usuario)
        self.addCleanup(frappe.set_user, "Administrator")

    def _sin_workflow(self):
        factories.desactivar_workflow(DT)
        self.addCleanup(frappe.clear_cache, doctype=DT)
        self.addCleanup(frappe.db.set_value, "Workflow", f5.WF_DOCUMENTO["name"], "is_active", 1)

    def _documento(self, **extra):
        return factories.crear_documento_controlado(proceso=self.proceso, elaborado_por=ELABORA, **extra)

    def _publicado(self, vence_en=None):
        doc = self._documento()
        valores = {"estado": "Publicado", "archivo": "/private/files/prueba-doc.pdf", "aprobado_por": DPGC,
                   "revisado_por": DPGC}
        if vence_en is not None:
            valores["fecha_proxima_revision"] = add_days(nowdate(), vence_en)
        frappe.db.set_value(DT, doc.name, valores, update_modified=False)
        return frappe.get_doc(DT, doc.name)


class IntegrationTestCarpetasYRelaciones(_Base):
    def test_el_documento_se_archiva_en_una_carpeta_del_arbol(self):
        raiz = frappe.get_doc({"doctype": "Carpeta Documental", "nombre": "Documentos DTI", "is_group": 1}).insert()
        hija = frappe.get_doc({"doctype": "Carpeta Documental", "nombre": "Formatos",
                               "parent_carpeta_documental": raiz.name, "is_group": 0}).insert()
        doc = self._documento(carpeta=hija.name)
        self.assertEqual(doc.carpeta, hija.name)
        self.assertEqual(frappe.db.get_value("Carpeta Documental", hija.name, "parent_carpeta_documental"), raiz.name)
        self.assertTrue(frappe.get_meta("Carpeta Documental").is_tree)

    def test_documentos_relacionados(self):
        a, b = self._documento(), self._documento()
        a.append("documentos_relacionados", {"documento": b.name, "relacion": "Complementa"})
        a.save(ignore_permissions=True)
        self.assertEqual(a.documentos_relacionados[0].titulo, b.titulo)

        a.append("documentos_relacionados", {"documento": b.name, "relacion": "Complementa"})
        with self.assertRaises(frappe.ValidationError):
            a.save(ignore_permissions=True)

        c = self._documento()
        c.append("documentos_relacionados", {"documento": c.name, "relacion": "Referencia"})
        with self.assertRaises(frappe.ValidationError):
            c.save(ignore_permissions=True)


class IntegrationTestObservaciones(_Base):
    def _en_revision(self):
        doc = self._documento()
        frappe.db.set_value(DT, doc.name, {"estado": "En revision", "archivo": "/private/files/x.pdf"},
                            update_modified=False)
        return frappe.get_doc(DT, doc.name)

    def test_observar_exige_el_texto_y_lo_sella(self):
        self._sin_workflow()
        doc = self._en_revision()
        doc.estado = "Observado"
        with self.assertRaises(frappe.ValidationError):
            doc.save(ignore_permissions=True)

        doc = frappe.get_doc(DT, doc.name)
        doc.estado = "Observado"
        doc.observacion = "Falta el diagrama del procedimiento."
        self._como(DPGC)
        doc.save(ignore_permissions=True)
        fila = doc.observaciones_revision[-1]
        self.assertEqual((fila.revisor, fila.paso, fila.version), (DPGC, "En revision → Observado", doc.version))
        self.assertEqual(fila.observacion, "Falta el diagrama del procedimiento.")
        self.assertFalse(doc.observacion)

    def test_por_el_motor_del_workflow(self):
        doc = self._en_revision()
        self._como(DPGC)
        d = frappe.get_doc(DT, doc.name)
        d.preparar_observacion("Corregir el alcance.")
        d = apply_workflow(frappe.get_doc(DT, doc.name), "Observar")
        self.assertEqual(d.estado, "Observado")
        self.assertEqual(d.observaciones_revision[-1].observacion, "Corregir el alcance.")
        self.assertEqual(d.observaciones_revision[-1].revisor, DPGC)

    def test_solo_prepara_la_observacion_quien_puede_observar(self):
        doc = self._en_revision()
        self._como(OTRO)
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc(DT, doc.name).preparar_observacion("No me corresponde.")


class IntegrationTestRevisionDeVigencia(_Base):
    def _abiertas(self, doc):
        return {t.allocated_to for t in tareas.tareas_abiertas(DT, doc.name)}

    def test_la_tarea_se_abre_al_entrar_en_plazo_y_va_al_dueno(self):
        lejos = self._publicado(vence_en=DIAS_TAREA_REVISION + 30)
        cerca = self._publicado(vence_en=DIAS_TAREA_REVISION - 5)
        tareas_revision_diaria()
        self.assertEqual(self._abiertas(lejos), set())
        self.assertEqual(self._abiertas(cerca), {DUENO})

    def test_revision_sin_cambios_renueva_la_vigencia_y_cierra_la_tarea(self):
        doc = self._publicado(vence_en=3)
        tareas_revision_diaria()
        self.assertEqual(self._abiertas(doc), {DUENO})

        self._como(DUENO)
        nueva = frappe.get_doc(DT, doc.name).registrar_revision("Sigue siendo válido.")
        frappe.set_user("Administrator")

        self.assertEqual(getdate(nueva), getdate(add_years(nowdate(), 1)))
        doc = frappe.get_doc(DT, doc.name)
        self.assertEqual(getdate(doc.fecha_proxima_revision), getdate(add_years(nowdate(), 1)))
        self.assertIn("Revisión sin cambios", doc.historial_cambios[-1].descripcion)
        self.assertEqual(doc.historial_cambios[-1].autor, DUENO)
        self.assertEqual(self._abiertas(doc), set())

    def test_no_la_registra_cualquiera(self):
        doc = self._publicado(vence_en=3)
        self._como(OTRO)
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc(DT, doc.name).registrar_revision()

    def test_un_documento_obsoleto_cierra_su_tarea(self):
        doc = self._publicado(vence_en=3)
        tareas_revision_diaria()
        frappe.db.set_value(DT, doc.name, "estado", "Obsoleto", update_modified=False)
        tareas_revision_diaria()
        self.assertEqual(self._abiertas(doc), set())


class IntegrationTestDifusion(_Base):
    def _para(self, doc):
        n = frappe.get_doc("Notification", R_PUBLICADO)
        para, _cc, _cco = n.get_list_of_recipients(doc, get_context(doc))
        return {c for c in para if c.endswith("@" + DOMINIO)}

    def test_el_dueno_del_proceso_se_toma_del_proceso(self):
        self.assertEqual(self._documento().dueno_proceso, DUENO)

    def test_la_publicacion_llega_a_los_involucrados(self):
        doc = self._documento()
        doc.append("difundir_a", {"usuario": INTERESADO})
        doc.save(ignore_permissions=True)
        doc.estado = "Publicado"
        doc.aprobado_por = DPGC
        self.assertEqual(self._para(doc), {ELABORA, DPGC, DUENO, INTERESADO})
