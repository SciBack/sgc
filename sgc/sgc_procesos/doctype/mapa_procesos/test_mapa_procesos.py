# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests de `Mapa Procesos` — el cuadro institucional (#39).

Lo que se comprueba, y por qué cada cosa importa:

- **Un mapa vigente exige imagen y fecha.** Un "vigente" sin lámina no es el
  cuadro aprobado, es una ficha vacía ocupando el sitio del cuadro.
- **Solo hay un vigente.** Dos mapas en vigor a la vez es la forma más rápida de
  que dos áreas trabajen con cuadros distintos creyendo que es el mismo.
- **El aviso de desfase.** Es la contrapartida de guardar una imagen en vez de
  generarla: hay que detectar que el árbol avanzó por debajo. Se prueba en los
  dos sentidos, porque un aviso que salta siempre se ignora igual que uno que no
  salta nunca.
"""
import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from sgc.sgc_procesos.doctype.mapa_procesos.mapa_procesos import mapa_vigente

PREFIJO = "TEST-MAPA"


class IntegrationTestMapaProcesos(IntegrationTestCase):
    def setUp(self):
        # Cada test parte de que no hay ningún mapa en vigor: el invariante que
        # se prueba es "solo uno", y arrastrar el de otro test lo enmascara.
        frappe.db.delete("Mapa Procesos")

    def _mapa(self, version, **valores):
        doc = frappe.get_doc(
            {
                "doctype": "Mapa Procesos",
                "version": f"{PREFIJO}-{version}",
                "titulo": "Mapa de procesos institucional",
                "estado": valores.pop("estado", "Borrador"),
                **valores,
            }
        )
        doc.flags.ignore_permissions = True
        doc.insert()
        return doc

    # --- requisitos del mapa en vigor ---------------------------------------

    def test_borrador_no_exige_imagen(self):
        """Se empieza a preparar la versión antes de tener la lámina final."""
        doc = self._mapa("borrador")
        self.assertEqual(doc.estado, "Borrador")

    def test_vigente_sin_imagen_no_se_guarda(self):
        with self.assertRaises(frappe.ValidationError):
            self._mapa("sin-imagen", estado="Vigente", fecha_aprobacion=nowdate())

    def test_vigente_sin_fecha_de_aprobacion_no_se_guarda(self):
        with self.assertRaises(frappe.ValidationError):
            self._mapa("sin-fecha", estado="Vigente", imagen="/files/mapa.png")

    # --- solo uno en vigor --------------------------------------------------

    def test_aprobar_uno_jubila_al_anterior(self):
        anterior = self._mapa(
            "v1",
            estado="Vigente",
            imagen="/files/mapa-v1.png",
            fecha_aprobacion=add_days(nowdate(), -400),
        )
        self._mapa(
            "v2",
            estado="Vigente",
            imagen="/files/mapa-v2.png",
            fecha_aprobacion=nowdate(),
        )
        self.assertEqual(
            frappe.db.get_value("Mapa Procesos", anterior.name, "estado"), "Obsoleto"
        )
        vigentes = frappe.get_all("Mapa Procesos", filters={"estado": "Vigente"})
        self.assertEqual(len(vigentes), 1)

    def test_guardar_un_borrador_no_toca_al_vigente(self):
        vigente = self._mapa(
            "en-vigor",
            estado="Vigente",
            imagen="/files/mapa.png",
            fecha_aprobacion=nowdate(),
        )
        self._mapa("propuesta")
        self.assertEqual(
            frappe.db.get_value("Mapa Procesos", vigente.name, "estado"), "Vigente"
        )

    # --- lo que devuelve la consulta ----------------------------------------

    def test_sin_mapa_vigente_lo_dice_y_no_revienta(self):
        self._mapa("solo-borrador")
        self.assertEqual(mapa_vigente(), {"hay_mapa": False})

    def test_devuelve_el_vigente_con_su_ficha(self):
        self._mapa(
            "publicado",
            estado="Vigente",
            imagen="/files/mapa.png",
            fecha_aprobacion=nowdate(),
            aprobado_por="Consejo Universitario",
            resolucion="R.C.U. 123-2026",
        )
        mapa = mapa_vigente()
        self.assertTrue(mapa["hay_mapa"])
        self.assertEqual(mapa["version"], f"{PREFIJO}-publicado")
        self.assertEqual(mapa["resolucion"], "R.C.U. 123-2026")

    # --- el aviso de desfase ------------------------------------------------

    def test_avisa_si_el_arbol_cambio_despues_de_aprobarse(self):
        self._crear_proceso("TEST-MAPA-P1")
        self._mapa(
            "antigua",
            estado="Vigente",
            imagen="/files/mapa.png",
            fecha_aprobacion=add_days(nowdate(), -30),
        )
        self.assertTrue(mapa_vigente()["desfasado"])

    def test_no_avisa_si_se_aprobo_hoy(self):
        """Mismo día no es desfase: el árbol se toca justo al cargar el mapa."""
        self._crear_proceso("TEST-MAPA-P2")
        self._mapa(
            "recien",
            estado="Vigente",
            imagen="/files/mapa.png",
            fecha_aprobacion=nowdate(),
        )
        self.assertFalse(mapa_vigente()["desfasado"])

    def _crear_proceso(self, codigo):
        if frappe.db.exists("Proceso", codigo):
            doc = frappe.get_doc("Proceso", codigo)
            doc.save(ignore_permissions=True)
            return doc
        doc = frappe.get_doc(
            {
                "doctype": "Proceso",
                "codigo": codigo,
                "proceso": "Proceso de prueba del mapa",
                "nivel": "Soporte",
                "estado": "Vigente",
            }
        )
        doc.insert(ignore_permissions=True)
        return doc
