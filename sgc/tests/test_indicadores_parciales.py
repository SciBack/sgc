# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Indicadores: los cuatro requisitos que estaban a medias.

  Análisis por periodo — si la ficha lo exige, lo tecleado llega con su análisis;
      lo que llega por ingesta deja una tarea al responsable; el análisis se
      escribe aunque la medición esté protegida, y lo sella el sistema
  Peso de las áreas   — sin repetir área, y suman 100 %
  Informe por familia — agrupa por categoría, marco o proceso, con el semáforo
      de la última medición
  Avisos por correo   — medición vencida (incumplimiento de fecha) y alerta nueva

Todo se deshace al final de la clase (rollback de IntegrationTestCase).
"""

import frappe
from frappe.email.doctype.notification.notification import get_context
from frappe.tests import IntegrationTestCase

from sgc import tareas
from sgc.ingesta import _escritura
from sgc.setup import f7_notificaciones as f7
from sgc.setup import f15_notificaciones_workflow as f15
from sgc.sgc_estructura.report.indicadores_por_familia import indicadores_por_familia as informe
from sgc.tests import factories

DOMINIO = "sgc-prueba-ind.example.com"
RESP = f"responsable@{DOMINIO}"
ANALISTA = f"analista@{DOMINIO}"


def _usuario(correo, rol="DPGC"):
    if not frappe.db.exists("User", correo):
        u = frappe.get_doc({"doctype": "User", "email": correo, "first_name": correo.split("@")[0],
                            "send_welcome_email": 0})
        u.append("roles", {"role": rol})
        u.insert(ignore_permissions=True)


class _Base(IntegrationTestCase):
    def setUp(self):
        _usuario(RESP)
        _usuario(ANALISTA)
        self.periodo = factories.crear_periodo_academico(prefijo="IND").name

    def tearDown(self):
        frappe.set_user("Administrator")

    def _ficha(self, **extra):
        ind = factories.crear_indicador(prefijo="INDP", **extra.pop("indicador_extra", {})).name
        ficha = frappe.get_doc({"doctype": "Ficha Indicador", "indicador": ind, "frecuencia": "anual",
                                "responsable": RESP, **extra}).insert(ignore_permissions=True)
        return ficha

    def _valor(self, indicador, **extra):
        return frappe.get_doc({"doctype": "Valor Indicador", "indicador": indicador, "valor_num": 80,
                               "periodo_academico": self.periodo, **extra}).insert(ignore_permissions=True)


class IntegrationTestAnalisisPorPeriodo(_Base):
    def test_lo_tecleado_exige_el_analisis_si_la_ficha_lo_pide(self):
        ficha = self._ficha(exige_analisis=1)
        with self.assertRaises(frappe.ValidationError):
            self._valor(ficha.indicador)
        frappe.set_user(ANALISTA)
        v = self._valor(ficha.indicador, analisis="Subió por el nuevo proceso de matrícula.")
        self.assertEqual(v.analizado_por, ANALISTA)
        self.assertTrue(v.fecha_analisis)

    def test_sin_exigencia_no_se_pide(self):
        ficha = self._ficha()
        self.assertTrue(self._valor(ficha.indicador).name)

    def test_lo_que_llega_por_ingesta_deja_la_tarea_y_se_cierra_al_analizar(self):
        ficha = self._ficha(exige_analisis=1)
        with _escritura():
            v = frappe.get_doc({"doctype": "Valor Indicador", "indicador": ficha.indicador, "valor_num": 70,
                                "periodo_academico": self.periodo, "ingesta_clave": frappe.generate_hash(length=12)}
                               ).insert(ignore_permissions=True)
        abiertas = {t.allocated_to for t in tareas.tareas_abiertas("Valor Indicador", v.name)}
        self.assertEqual(abiertas, {RESP})

        # La medición está protegida (viene de la ingesta), pero el análisis se escribe.
        frappe.set_user(ANALISTA)
        v = frappe.get_doc("Valor Indicador", v.name)
        v.analisis = "Bajó por el cambio de calendario."
        v.save(ignore_permissions=True)
        self.assertEqual(v.analizado_por, ANALISTA)
        self.assertEqual(tareas.tareas_abiertas("Valor Indicador", v.name), [])

    def test_la_medicion_protegida_sigue_sin_poder_editarse(self):
        ficha = self._ficha()
        with _escritura():
            v = frappe.get_doc({"doctype": "Valor Indicador", "indicador": ficha.indicador, "valor_num": 70,
                                "periodo_academico": self.periodo, "ingesta_clave": frappe.generate_hash(length=12)}
                               ).insert(ignore_permissions=True)
        v = frappe.get_doc("Valor Indicador", v.name)
        v.valor_num = 99
        with self.assertRaises(frappe.ValidationError):
            v.save(ignore_permissions=True)

    def test_el_sello_no_se_teclea(self):
        ficha = self._ficha()
        v = self._valor(ficha.indicador, analisis="x", analizado_por=RESP)
        self.assertEqual(v.analizado_por, "Administrator")


class IntegrationTestPesoDeAreas(_Base):
    def _areas(self, n):
        return [factories._ensure_named("Unidad Organica", f"IND-AREA-{i}", {"nombre": f"Área {i}", "tipo": "Oficina"}).name
                for i in range(n)]

    def test_los_pesos_suman_cien(self):
        a, b = self._areas(2)
        ficha = self._ficha()
        ficha.append("participacion_areas", {"unidad_organica": a, "peso": 60})
        ficha.append("participacion_areas", {"unidad_organica": b, "peso": 30})
        with self.assertRaises(frappe.ValidationError):
            ficha.save(ignore_permissions=True)
        ficha = frappe.get_doc("Ficha Indicador", ficha.name)
        ficha.append("participacion_areas", {"unidad_organica": a, "peso": 60})
        ficha.append("participacion_areas", {"unidad_organica": b, "peso": 40})
        ficha.save(ignore_permissions=True)
        self.assertEqual(len(ficha.participacion_areas), 2)

    def test_sin_area_repetida(self):
        (a,) = self._areas(1)
        ficha = self._ficha()
        ficha.append("participacion_areas", {"unidad_organica": a, "peso": 50})
        ficha.append("participacion_areas", {"unidad_organica": a, "peso": 50})
        with self.assertRaises(frappe.ValidationError):
            ficha.save(ignore_permissions=True)


class IntegrationTestInformePorFamilia(_Base):
    def test_agrupa_y_cuenta_el_semaforo(self):
        categoria = frappe.get_meta("Indicador").get_field("categoria").options.split("\n")[0]
        con = self._ficha(indicador_extra={"categoria": categoria})
        sin = self._ficha(indicador_extra={"categoria": categoria})
        self._valor(con.indicador, semaforo="Verde")
        columnas, data, _msg, grafico = informe.execute({"agrupar_por": "Categoría"})
        fila = next(g for g in data if g["familia"] == categoria)
        self.assertGreaterEqual(fila["indicadores"], 2)
        self.assertGreaterEqual(fila["sin_medicion"], 1)
        self.assertEqual(columnas[0]["fieldname"], "familia")
        self.assertIsNotNone(grafico)
        self.assertTrue(frappe.db.exists("Indicador", sin.indicador))

    def test_admite_las_tres_agrupaciones(self):
        for agrupar in ("Categoría", "Marco normativo", "Proceso"):
            with self.subTest(agrupar=agrupar):
                columnas, _data, _m, _g = informe.execute({"agrupar_por": agrupar})
                self.assertEqual(columnas[0]["label"], agrupar)


class IntegrationTestAvisosDeIndicadores(_Base):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        f7.run()
        f15.run()
        frappe.flags.in_patch = False

    def _para(self, regla, doc):
        n = frappe.get_doc("Notification", regla)
        para, _cc, _cco = n.get_list_of_recipients(doc, get_context(doc))
        return {c for c in para if c.endswith("@" + DOMINIO)}

    def test_los_pasos_no_dejan_el_meta_sin_la_matriz(self):
        """f7/f15 guardan reglas con `in_patch`; el meta de esos DocTypes no puede quedar
        cacheado sin los Custom DocPerm (le quitaba a la DPGC el «report»)."""
        for dt in ("Salida No Conforme", "Accion Mejora", "Documento Controlado", "Ficha Indicador"):
            with self.subTest(doctype=dt):
                roles = {p.role for p in frappe.get_meta(dt).permissions}
                self.assertIn("DPGC", roles)
        self.assertFalse(frappe.flags.in_patch)

    def test_medicion_vencida_avisa_al_dia_siguiente(self):
        n = frappe.db.get_value("Notification", "SGC - Medicion de indicador vencida",
                                ["event", "date_changed", "days_in_advance", "channel"], as_dict=True)
        self.assertEqual((n.event, n.date_changed, n.days_in_advance, n.channel),
                         ("Days After", "proxima_medicion", 1, "Email"))
        ficha = frappe.get_doc({"doctype": "Ficha Indicador", "responsable": RESP})
        self.assertIn(RESP, self._para("SGC - Medicion de indicador vencida", ficha))

    def test_alerta_nueva_avisa_al_responsable_o_a_la_dpgc(self):
        alerta = frappe.get_doc({"doctype": "Alerta Indicador", "responsable": RESP, "estado": "Abierta"})
        self.assertEqual(self._para("SGC - Alerta de indicador", alerta), {RESP})
        huerfana = frappe.get_doc({"doctype": "Alerta Indicador", "estado": "Abierta"})
        # Sin responsable, a la DPGC (los usuarios de prueba tienen ese rol).
        self.assertEqual(self._para("SGC - Alerta de indicador", huerfana), {RESP, ANALISTA})
