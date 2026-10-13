# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Verificación de instancia (#50): ¿qué falta para que esta instancia esté operable?

Cada test reproduce el estado que quiere comprobar —una instancia sin estructura,
sin periodo, sin permisos— borrando o cambiando datos DENTRO de un savepoint que
se deshace al terminar. Así se prueba contra la base real, con sus datos, y
nada de lo borrado sobrevive al test (el rollback del IntegrationTestCase es por
clase, y una clase que deja el sitio sin permisos tumba las siguientes).
"""

import contextlib
import io
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from sgc.setup.f3b_rbac import MATRIZ
from sgc.tests import factories
from sgc.verificacion import AVISO, BLOQUEANTE, INFO, despliegue, run, verificar

SAVEPOINT = "verificar_instancia"


class _ConSavepoint(IntegrationTestCase):
    def setUp(self):
        frappe.db.savepoint(SAVEPOINT)
        self.addCleanup(frappe.db.rollback, save_point=SAVEPOINT)

    def _hallazgos(self, solo):
        return {h.codigo: h for h in verificar(solo=solo)}

    def _codigos(self, solo=None, nivel=None):
        return {h.codigo for h in verificar(solo=solo) if nivel is None or h.nivel == nivel}

    # --- estados de partida ----------------------------------------------

    def _sin_estructura(self):
        frappe.db.delete("Unidad Organica")

    def _sin_periodos(self):
        frappe.db.delete("Periodo Academico")

    def _una_unidad(self, codigo="VI-RAIZ", padre=None):
        return factories._ensure_named("Unidad Organica", codigo, {
            "nombre": f"Unidad {codigo}", "tipo": "Oficina", "parent_unidad_organica": padre,
        })

    def _periodo_en_curso(self, codigo="VI-EN-CURSO", **extra):
        valores = {"fecha_inicio": add_days(today(), -30), "fecha_fin": add_days(today(), 60)}
        valores.update(extra)
        return factories.crear_periodo_academico(codigo=codigo, **valores)

    def _dada_de_alta(self):
        """Lo mínimo que una institución da de alta: un árbol con una raíz y su periodo en curso."""
        self._sin_estructura()
        raiz = self._una_unidad()
        self._una_unidad("VI-HIJA", padre=raiz.name)
        self._sin_periodos()
        self._periodo_en_curso()


class IntegrationTestEstructura(_ConSavepoint):
    def test_sin_unidades_es_bloqueante(self):
        self._sin_estructura()
        h = self._hallazgos("estructura_organizativa")["sin-estructura"]
        self.assertEqual(h.nivel, BLOQUEANTE)

    def test_un_arbol_con_una_raiz_no_da_hallazgos(self):
        self._sin_estructura()
        raiz = self._una_unidad()
        self._una_unidad("VI-HIJA", padre=raiz.name)
        self.assertEqual(self._codigos("estructura_organizativa"), set())

    def test_varias_raices_se_nombran(self):
        self._sin_estructura()
        self._una_unidad("VI-RAIZ-A")
        self._una_unidad("VI-RAIZ-B")
        h = self._hallazgos("estructura_organizativa")["estructura-varias-raices"]
        self.assertEqual(h.nivel, INFO)
        self.assertEqual(h.detalle, ["VI-RAIZ-A", "VI-RAIZ-B"])


class IntegrationTestPeriodo(_ConSavepoint):
    def test_sin_periodos_es_bloqueante(self):
        self._sin_periodos()
        self.assertEqual(self._hallazgos("periodo_vigente")["sin-periodo-vigente"].nivel, BLOQUEANTE)

    def test_solo_periodos_cerrados_es_bloqueante(self):
        self._sin_periodos()
        self._periodo_en_curso(estado="cerrado")
        self.assertIn("sin-periodo-vigente", self._codigos("periodo_vigente", BLOQUEANTE))

    def test_un_periodo_abierto_en_curso_no_da_hallazgos(self):
        self._sin_periodos()
        self._periodo_en_curso()
        self.assertEqual(self._codigos("periodo_vigente"), set())

    def test_abierto_con_la_fecha_de_fin_pasada_avisa(self):
        self._sin_periodos()
        self._periodo_en_curso("VI-PASADO", fecha_inicio=add_days(today(), -200), fecha_fin=add_days(today(), -10))
        h = self._hallazgos("periodo_vigente")["periodo-vencido-abierto"]
        self.assertEqual((h.nivel, h.detalle), (AVISO, ["VI-PASADO"]))

    def test_abierto_sin_fechas_avisa_porque_no_se_puede_comprobar(self):
        self._sin_periodos()
        factories.crear_periodo_academico(codigo="VI-SIN-FECHAS")
        h = self._hallazgos("periodo_vigente")["periodo-sin-fechas"]
        self.assertEqual((h.nivel, h.detalle), (AVISO, ["VI-SIN-FECHAS"]))


class IntegrationTestProcesos(_ConSavepoint):
    def test_un_proceso_vigente_sin_responsable_se_nombra(self):
        # Los demás vigentes, con responsable: el detalle se recorta a 15 nombres
        # y en una copia de producción hay más procesos sin él.
        frappe.db.set_value("Proceso", {"estado": "Vigente"}, "responsable", "Administrator")
        proceso = factories.crear_proceso(codigo="VI-P-SIN")
        frappe.db.set_value("Proceso", proceso.name, {"estado": "Vigente", "responsable": None})
        h = self._hallazgos("procesos_sin_responsable")["procesos-sin-responsable"]
        self.assertEqual((h.nivel, h.detalle), (AVISO, ["VI-P-SIN"]))

    def test_con_responsable_no_aparece(self):
        proceso = factories.crear_proceso(codigo="VI-P-CON")
        frappe.db.set_value("Proceso", proceso.name, {"estado": "Vigente", "responsable": "Administrator"})
        h = self._hallazgos("procesos_sin_responsable").get("procesos-sin-responsable")
        self.assertFalse(h and "VI-P-CON" in h.detalle)


class IntegrationTestDespliegue(_ConSavepoint):
    def _quitar_permisos(self, doctypes):
        for dt in doctypes:
            frappe.db.delete("Custom DocPerm", {"parent": dt, "role": ["in", list(MATRIZ[dt])]})

    def test_con_la_matriz_aplicada_no_hay_hallazgos(self):
        self.assertEqual(self._codigos("permisos_aplicados"), set())

    def test_sin_ningun_permiso_del_sgc_es_bloqueante(self):
        self._quitar_permisos([dt for dt in MATRIZ if frappe.db.exists("DocType", dt)])
        self.assertEqual(self._hallazgos("permisos_aplicados")["rbac-no-aplicado"].nivel, BLOQUEANTE)

    def test_un_doctype_sin_permisos_se_nombra(self):
        self._quitar_permisos(["Proceso"])
        h = self._hallazgos("permisos_aplicados")["rbac-incompleto"]
        self.assertEqual((h.nivel, h.detalle), (AVISO, ["Proceso"]))

    def test_los_workflows_se_leen_de_los_pasos_del_despliegue(self):
        nombres = {s["name"] for s in despliegue._workflows_declarados()}
        self.assertIn("Autoevaluacion SGC", nombres)
        self.assertGreaterEqual(len(nombres), 15)

    def test_con_los_workflows_aplicados_no_hay_hallazgos(self):
        self.assertEqual(self._codigos("workflows_aplicados"), set())

    def test_un_workflow_desactivado_se_nombra(self):
        frappe.db.set_value("Workflow", "Autoevaluacion SGC", "is_active", 0)
        h = self._hallazgos("workflows_aplicados")["workflows-incompletos"]
        self.assertEqual(h.nivel, AVISO)
        self.assertTrue(any(linea.startswith("Autoevaluacion SGC") for linea in h.detalle))

    def test_sin_ningun_workflow_es_bloqueante(self):
        frappe.db.delete("Workflow", {"name": ["in", [s["name"] for s in despliegue._workflows_declarados()]]})
        self.assertEqual(self._hallazgos("workflows_aplicados")["workflows-no-aplicados"].nivel, BLOQUEANTE)


class IntegrationTestMarcos(_ConSavepoint):
    def test_sin_marcos_vigentes_avisa(self):
        frappe.db.set_value("Marco Normativo", {"estado": "vigente"}, "estado", "derogado")
        self.assertEqual(self._hallazgos("marcos_vigentes")["sin-marcos"].nivel, AVISO)

    def test_un_marco_vigente_con_la_vigencia_vencida_avisa(self):
        marco = factories.crear_marco_prueba(1, 1, prefijo="VI-M1", con_escala=False)["marco"]
        frappe.db.set_value("Marco Normativo", marco,
                            {"estado": "vigente", "alcance": "Gestión interna", "vigente_hasta": add_days(today(), -1)})
        h = self._hallazgos("marcos_vigentes")["marco-caducado"]
        self.assertEqual(h.nivel, AVISO)
        self.assertIn(marco, h.detalle)

    def test_sin_alcance_es_informativo(self):
        marco = factories.crear_marco_prueba(1, 1, prefijo="VI-M2", con_escala=False)["marco"]
        frappe.db.set_value("Marco Normativo", marco, {"estado": "vigente", "alcance": None})
        h = self._hallazgos("marcos_vigentes")["marco-sin-alcance"]
        self.assertEqual(h.nivel, INFO)
        self.assertIn(marco, h.detalle)


class IntegrationTestIdentidad(_ConSavepoint):
    def _con_conf(self, **conf):
        claves = ("sgc_app_name", "sgc_institucion", "sgc_logo")
        base = {k: "" for k in claves}
        base.update(conf)
        return patch.dict(frappe.local.conf, base)

    def test_identidad_neutra_avisa_y_nombra_las_claves(self):
        with self._con_conf(), patch.object(frappe.db, "get_default", return_value=None):
            hallazgos = self._hallazgos("identidad")
        h = hallazgos["identidad-sin-declarar"]
        self.assertEqual(h.nivel, AVISO)
        self.assertTrue(any(linea.startswith("sgc_institucion") for linea in h.detalle))
        self.assertEqual(hallazgos["identidad-sin-logo"].nivel, INFO)

    def test_identidad_declarada_no_da_hallazgos(self):
        with self._con_conf(sgc_app_name="SGC Prueba", sgc_institucion="Universidad de Prueba",
                            sgc_logo="/files/logo.png"):
            self.assertEqual(self._codigos("identidad"), set())


class IntegrationTestCorreoSaliente(_ConSavepoint):
    def _sin_cuenta(self):
        frappe.db.set_value("Email Account", {"default_outgoing": 1}, "default_outgoing", 0)

    def test_sin_cuenta_saliente_avisa(self):
        self._sin_cuenta()
        with patch.dict(frappe.local.conf, {"mail_server": None, "mute_emails": 0}):
            h = self._hallazgos("cuenta_saliente")["correo-sin-cuenta-saliente"]
        self.assertEqual(h.nivel, AVISO)

    def test_con_servidor_declarado_no_avisa(self):
        self._sin_cuenta()
        with patch.dict(frappe.local.conf, {"mail_server": "smtp.example.org", "mute_emails": 0}):
            self.assertEqual(self._codigos("cuenta_saliente"), set())

    def test_correo_silenciado_avisa(self):
        with patch.dict(frappe.local.conf, {"mail_server": "smtp.example.org", "mute_emails": 1}):
            self.assertEqual(self._hallazgos("cuenta_saliente")["correo-silenciado"].nivel, AVISO)


class IntegrationTestSso(_ConSavepoint):
    def test_sin_sso_avisa_y_dice_como_resolverlo(self):
        frappe.db.set_value("Social Login Key", {"enable_social_login": 1}, "enable_social_login", 0)
        sin_sso = {k: None for k in frappe.local.conf if k.startswith("sgc_sso_")}
        with patch.dict(frappe.local.conf, sin_sso):
            h = self._hallazgos("sso")["sso-no-configurado"]
        self.assertEqual(h.nivel, AVISO)
        self.assertIn("#46", h.remedio)


class IntegrationTestInstancia(_ConSavepoint):
    """Los escenarios del issue: la instancia entera, y lo que el comando le dice al despliegue."""

    def _run(self, **kwargs):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            resultado = run(**kwargs)
        return resultado, salida.getvalue()

    def test_recien_instalada_sin_dar_de_alta_bloquea_por_estructura_y_periodo(self):
        self._sin_estructura()
        self._sin_periodos()
        self.assertTrue({"sin-estructura", "sin-periodo-vigente"} <= self._codigos(nivel=BLOQUEANTE))

    def test_dada_de_alta_no_tiene_bloqueantes(self):
        self._dada_de_alta()
        self.assertEqual(self._codigos(nivel=BLOQUEANTE), set())

    def test_con_un_bloqueante_termina_con_codigo_1(self):
        self._sin_periodos()
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida), self.assertRaises(SystemExit) as fin:
            run()
        self.assertEqual(fin.exception.code, 1)
        self.assertIn("[BLOQUEANTE] sin-periodo-vigente", salida.getvalue())

    def test_sin_bloqueantes_termina_bien_y_lista_lo_comprobado(self):
        self._dada_de_alta()
        resultado, salida = self._run(solo="estructura")  # salir=True: no termina
        self.assertIsNone(resultado)
        self.assertIn("✓ estructura_organizativa", salida)
        # En un sitio limpio no hay ningún hallazgo («Sin hallazgos»); en una copia de
        # producción, avisos. En ninguno de los dos puede haber un bloqueante.
        self.assertNotIn("[BLOQUEANTE]", salida)

    def test_cada_chequeo_se_puede_correr_por_separado(self):
        self._sin_estructura()
        self._sin_periodos()
        self.assertEqual(self._codigos("periodo_vigente"), {"sin-periodo-vigente"})
        self.assertEqual(self._codigos("estructura_organizativa,periodo_vigente"),
                         {"sin-estructura", "sin-periodo-vigente"})

    def test_un_nombre_que_no_existe_no_pasa_por_un_informe_limpio(self):
        with self.assertRaises(ValueError):
            verificar(solo="no_existe")
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida), self.assertRaises(SystemExit) as fin:
            run(solo="no_existe")
        self.assertEqual(fin.exception.code, 2)
        self.assertIn("estructura", salida.getvalue())

    def test_salir_false_devuelve_los_hallazgos_sin_terminar(self):
        self._sin_periodos()
        resultado, _ = self._run(salir=False)
        self.assertIn("sin-periodo-vigente", {h["codigo"] for h in resultado})
