# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Suite de tests para el M05 — No Conformidad (RF-B05).

El controlador (`no_conformidad.py`) aplica validaciones INCREMENTALES por etapa:
cada estado del ciclo de vida exige, de forma acumulativa, lo que esa etapa
requiere. El orden lo fija el dict `ORDEN`:

    Abierta(0) -> En analisis(1) -> En tratamiento(2) -> En verificacion(3)
                                              -> Cerrada eficaz / no eficaz(4)

Reglas verificadas:
  validate() (side-effects):
    tipo == "No conformidad mayor"      -> fuerza requiere_analisis_causa = 1
    fecha_deteccion vacia               -> se autocompleta con nowdate()
  Validaciones que deben FALLAR (frappe.ValidationError):
    nivel >= 1 (En analisis+)           sin responsable
    nivel >= 2 (En tratamiento+)        requiere_analisis_causa y sin analisis_causa
    nivel >= 3 (En verificacion+)       sin fecha_compromiso
    nivel >= 3 (En verificacion+)       sin plan_mejora y sin correccion_inmediata
    Cerrada*                            sin evidencia_cierre
    Cerrada*                            sin verificada_por
  Camino feliz:
    cada etapa pasa cuando aporta lo que exige (y hereda lo de las anteriores).

Hereda de `frappe.tests.IntegrationTestCase`: cada test corre en su propia
transaccion con rollback automatico.
"""
import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from sgc.tests import factories

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []

# Usuario siempre presente en Frappe; sirve de Link para responsable/verificada_por.
ADMIN = "Administrator"


class IntegrationTestNoConformidad(IntegrationTestCase):
    """Validaciones incrementales por etapa del M05 (No Conformidad)."""

    def setUp(self):
        # Evidencia reutilizable como soporte del cierre (M09 le da un enlace_url).
        self.evidencia = factories.crear_evidencia().name

    # -- helper de construccion --------------------------------------------
    def _nc(self, **overrides):
        """Crea e inserta una No Conformidad con defaults sensatos.

        Por defecto tipo="No conformidad menor" (asi requiere_analisis_causa=0
        y se pueden aislar las demas reglas) y estado="Abierta".
        """
        vals = {
            "doctype": "No Conformidad",
            "titulo": "NC de prueba M05",
            "tipo": "No conformidad menor",
            "estado": "Abierta",
        }
        vals.update(overrides)
        doc = frappe.get_doc(vals)
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc

    # ======================================================================
    # Side-effects de validate()
    # ======================================================================
    def test_nc_mayor_fuerza_requiere_analisis_causa(self):
        # Una NC mayor SIEMPRE queda marcada como requiere_analisis_causa,
        # aunque no se pase el flag. En "Abierta" (nivel 0) aun no exige el texto.
        nc = self._nc(tipo="No conformidad mayor")
        self.assertEqual(nc.requiere_analisis_causa, 1)

    def test_nc_menor_no_fuerza_analisis_causa(self):
        # Una NC menor no adquiere el flag por si sola.
        nc = self._nc(tipo="No conformidad menor")
        self.assertFalse(nc.requiere_analisis_causa)

    def test_fecha_deteccion_se_autocompleta(self):
        # Sin fecha_deteccion explicita, validate() la fija a hoy.
        nc = self._nc()
        self.assertEqual(str(nc.fecha_deteccion), nowdate())

    # ======================================================================
    # nivel >= 1 — En analisis exige responsable
    # ======================================================================
    def test_en_analisis_sin_responsable_falla(self):
        with self.assertRaises(frappe.ValidationError):
            self._nc(estado="En analisis")

    def test_en_analisis_con_responsable_ok(self):
        nc = self._nc(estado="En analisis", responsable=ADMIN)
        self.assertEqual(nc.estado, "En analisis")
        self.assertEqual(nc.responsable, ADMIN)

    # ======================================================================
    # nivel >= 2 — En tratamiento exige analisis de causa si la NC lo requiere
    # ======================================================================
    def test_en_tratamiento_mayor_sin_analisis_falla(self):
        # tipo mayor -> requiere_analisis_causa=1 automatico -> en tratamiento
        # exige el texto del analisis, que no se aporta.
        with self.assertRaises(frappe.ValidationError):
            self._nc(
                tipo="No conformidad mayor",
                estado="En tratamiento",
                responsable=ADMIN,
            )

    def test_en_tratamiento_mayor_con_analisis_ok(self):
        nc = self._nc(
            tipo="No conformidad mayor",
            estado="En tratamiento",
            responsable=ADMIN,
            analisis_causa="Causa raiz: falta de procedimiento documentado.",
        )
        self.assertEqual(nc.estado, "En tratamiento")

    def test_en_tratamiento_menor_sin_analisis_ok(self):
        # tipo menor no requiere analisis: puede pasar a tratamiento sin el texto.
        nc = self._nc(estado="En tratamiento", responsable=ADMIN)
        self.assertEqual(nc.estado, "En tratamiento")
        self.assertFalse(nc.requiere_analisis_causa)

    def test_analisis_causa_solo_espacios_no_cuenta(self):
        # Un analisis_causa en blanco (solo espacios) no satisface la exigencia.
        with self.assertRaises(frappe.ValidationError):
            self._nc(
                tipo="No conformidad mayor",
                estado="En tratamiento",
                responsable=ADMIN,
                analisis_causa="   ",
            )

    # ======================================================================
    # nivel >= 3 — En verificacion exige plazo + accion correctiva
    # ======================================================================
    def test_en_verificacion_sin_fecha_compromiso_falla(self):
        with self.assertRaises(frappe.ValidationError):
            self._nc(
                estado="En verificacion",
                responsable=ADMIN,
                correccion_inmediata="Se rehizo el registro.",
            )

    def test_en_verificacion_sin_accion_falla(self):
        # Con plazo pero sin plan_mejora ni correccion_inmediata -> falla.
        with self.assertRaises(frappe.ValidationError):
            self._nc(
                estado="En verificacion",
                responsable=ADMIN,
                fecha_compromiso=add_days(nowdate(), 30),
            )

    def test_en_verificacion_con_plazo_y_correccion_ok(self):
        nc = self._nc(
            estado="En verificacion",
            responsable=ADMIN,
            fecha_compromiso=add_days(nowdate(), 30),
            correccion_inmediata="Contencion: se aisla el lote afectado.",
        )
        self.assertEqual(nc.estado, "En verificacion")

    # ======================================================================
    # nivel == 4 — Cierre exige evidencia + verificador
    # ======================================================================
    def test_cierre_sin_evidencia_falla(self):
        with self.assertRaises(frappe.ValidationError):
            self._nc(
                estado="Cerrada eficaz",
                responsable=ADMIN,
                fecha_compromiso=add_days(nowdate(), 30),
                correccion_inmediata="Correccion aplicada.",
                verificada_por=ADMIN,
            )

    def test_cierre_sin_verificador_falla(self):
        with self.assertRaises(frappe.ValidationError):
            self._nc(
                estado="Cerrada eficaz",
                responsable=ADMIN,
                fecha_compromiso=add_days(nowdate(), 30),
                correccion_inmediata="Correccion aplicada.",
                evidencia_cierre=self.evidencia,
            )

    def test_cierre_eficaz_completo_ok(self):
        # Camino feliz de extremo a extremo: se cumplen TODAS las exigencias
        # acumuladas (responsable + plazo + accion + evidencia + verificador).
        nc = self._nc(
            tipo="No conformidad mayor",
            estado="Cerrada eficaz",
            responsable=ADMIN,
            analisis_causa="Causa raiz identificada y tratada.",
            fecha_compromiso=add_days(nowdate(), 15),
            correccion_inmediata="Correccion inmediata registrada.",
            evidencia_cierre=self.evidencia,
            verificada_por=ADMIN,
        )
        self.assertEqual(nc.estado, "Cerrada eficaz")
        self.assertEqual(nc.evidencia_cierre, self.evidencia)
        self.assertEqual(nc.verificada_por, ADMIN)
        # la NC mayor arrastro su flag hasta el cierre
        self.assertEqual(nc.requiere_analisis_causa, 1)
