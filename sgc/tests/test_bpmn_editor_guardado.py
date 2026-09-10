# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Guardar un .bpmn no puede renombrar el adjunto.

El editor guardaba borrando el adjunto y creando otro. Eso hacía que el nombre
CRECIERA en cada guardado, porque `file_manager.save_file` pasa siempre por
`get_file_name`, que añade `content_hash[-6:]` si existe **cualquier** File
llamado igual — sin mirar a qué documento está adjunto.

No era teórico: en producción el mismo diagrama está adjunto al Procedimiento y a
la ficha del proceso, así que la colisión es permanente y el nombre se degradaba
guardado a guardado:

    18-mantenimiento-equipos-dti.bpmn
    18-mantenimiento-equipos-dtie65eede65eed.bpmn
    18-mantenimiento-equipos-dtie65eede65eed6a79bd.bpmn

⚠️ `guardar_bpmn` hace `frappe.db.commit()`, así que lo que estos tests creen
sobrevive al rollback. De ahí el `tearDown` explícito.
"""
import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, now_datetime

from sgc import bpmn_editor as be
from sgc.tests import factories

XML_A = '<?xml version="1.0"?><bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" id="A"/>'
XML_B = '<?xml version="1.0"?><bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" id="B"/>'
NOMBRE = "test-diagrama-guardado.bpmn"


class IntegrationTestGuardadoBPMN(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.procesos = []
        self.ficheros = []

    def tearDown(self):
        for f in frappe.get_all("File", filters={"file_name": ["like", "test-diagrama-guardado%"]}, pluck="name"):
            frappe.delete_doc("File", f, ignore_permissions=True, force=True)
        for p in self.procesos:
            if frappe.db.exists("Proceso", p):
                frappe.delete_doc("Proceso", p, ignore_permissions=True, force=True)
        frappe.db.commit()

    def _proceso(self):
        p = factories.crear_proceso().name
        self.procesos.append(p)
        return p

    def test_guardar_dos_veces_conserva_el_nombre(self):
        p = self._proceso()
        r1 = be.guardar_bpmn("Proceso", p, NOMBRE, XML_A)
        r2 = be.guardar_bpmn("Proceso", p, r1["file_name"], XML_B)
        self.assertEqual(r1["file_name"], r2["file_name"], "el adjunto no puede cambiar de nombre al guardarlo")
        self.assertEqual(r1["file_url"], r2["file_url"], "quien tuviera la URL abierta no debe perderla")

    def test_el_contenido_si_se_actualiza(self):
        p = self._proceso()
        be.guardar_bpmn("Proceso", p, NOMBRE, XML_A)
        r = be.guardar_bpmn("Proceso", p, NOMBRE, XML_B)
        doc = frappe.get_doc("File", frappe.get_all("File", filters={"file_name": r["file_name"]}, pluck="name")[0])
        self.assertIn('id="B"', doc.get_content(), "conservar el nombre no puede significar conservar el contenido")

    def test_la_version_de_cache_cambia_al_guardar(self):
        """Conservar el nombre dejó la URL fija, y con ella la copia del navegador:
        la vista previa seguía dibujando el diagrama anterior. `version` es lo que
        permite invalidarla, así que TIENE que moverse cuando el diagrama cambia."""
        p = self._proceso()
        be.guardar_bpmn("Proceso", p, NOMBRE, XML_A)
        antes = be.listar_bpmn("Proceso", p)[0]
        self.assertIn("version", antes, "el visor no puede invalidar lo que no recibe")

        # El `modified` tiene resolución de segundo: sin este empujón, dos guardados
        # seguidos en el mismo segundo darían la misma versión y el test no probaría nada.
        nombre = frappe.get_all("File", filters={"file_name": antes["file_name"]}, pluck="name")[0]
        # `update_modified=False` es imprescindible: sin él, set_value pisa el valor
        # que le acabamos de dar con la hora actual, y la versión no se mueve.
        frappe.db.set_value(
            "File", nombre, "modified", add_to_date(now_datetime(), seconds=5), update_modified=False
        )
        frappe.db.commit()

        despues = be.listar_bpmn("Proceso", p)[0]
        self.assertEqual(antes["file_url"], despues["file_url"], "la URL sigue siendo la misma")
        self.assertNotEqual(
            antes["version"], despues["version"], "sin cambio de versión, el navegador sirve el dibujo viejo"
        )

    def test_no_deja_adjuntos_duplicados(self):
        p = self._proceso()
        be.guardar_bpmn("Proceso", p, NOMBRE, XML_A)
        be.guardar_bpmn("Proceso", p, NOMBRE, XML_B)
        self.assertEqual(len(be.listar_bpmn("Proceso", p)), 1, "cada guardado debe dejar UN adjunto, no acumular")

    def test_el_nombre_aguanta_aunque_otro_documento_tenga_uno_igual(self):
        # Es el caso real que destapó el bug: el mismo diagrama adjunto al
        # procedimiento y a la ficha del proceso.
        otro = self._proceso()
        be.guardar_bpmn("Proceso", otro, NOMBRE, XML_A)
        p = self._proceso()
        r1 = be.guardar_bpmn("Proceso", p, NOMBRE, XML_A)
        r2 = be.guardar_bpmn("Proceso", p, r1["file_name"], XML_B)
        self.assertEqual(r1["file_name"], r2["file_name"], "la colisión con otro documento no debe renombrar nada")

    def test_reconoce_el_adjunto_aunque_frappe_le_haya_puesto_sufijo(self):
        # Sin esto, el segundo guardado no reconoce su propio adjunto y crea otro.
        self.assertTrue(be._mismo_diagrama("18-proceso.bpmn", "18-procesoa1b2c3.bpmn"))
        self.assertTrue(be._mismo_diagrama("18-procesoa1b2c3.bpmn", "18-procesoa1b2c3d4e5f6.bpmn"))
        self.assertFalse(be._mismo_diagrama("18-proceso.bpmn", "19-otro-proceso.bpmn"))
        self.assertFalse(be._mismo_diagrama("", "18-proceso.bpmn"))

    def test_el_mismo_contenido_en_dos_documentos_se_escribe_en_los_dos(self):
        """El caso de sincronizar un diagrama entre el procedimiento y la ficha.

        `File.save_file` deduplica por `content_hash`: si ya existe otro File con ese
        contenido, da el fichero por escrito y no escribe. El registro se quedaba
        diciendo que tenía la versión nueva mientras el disco conservaba la vieja.
        """
        from frappe.core.doctype.file.utils import get_content_hash

        a, b = self._proceso(), self._proceso()
        be.guardar_bpmn("Proceso", a, NOMBRE, XML_A)   # A tiene el contenido nuevo
        be.guardar_bpmn("Proceso", b, NOMBRE, XML_B)   # B parte de otro distinto
        r = be.guardar_bpmn("Proceso", b, NOMBRE, XML_A)   # ahora B se sincroniza con A

        doc = frappe.get_doc("File", frappe.get_all("File", filters={"file_name": r["file_name"]}, pluck="name")[0])
        contenido = doc.get_content()
        self.assertIn('id="A"', contenido, "el fichero de B debe tener de verdad el contenido de A")
        self.assertEqual(
            doc.content_hash,
            get_content_hash(contenido.encode()),
            "el hash del registro tiene que describir el fichero que hay en disco",
        )
        self.assertEqual(doc.file_size, len(contenido.encode()), "el tamaño del registro también")
