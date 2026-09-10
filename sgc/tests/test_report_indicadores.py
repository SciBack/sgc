# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Tests del informe «Indicadores de Acreditacion».

El informe repone lo que se perdió al retirar la SPA: la lista de `Valor Indicador`
enseña las tres fuentes mezcladas y el texto en bruto del productor, y quien la abre
ve dos cifras del mismo indicador sin saber cuál mirar.

Se cubren las cuatro cosas que, si se rompen, convierten el informe en algo que miente:

  1. **Una sola fuente**, y las que quedan fuera se cuentan en el aviso — no se ocultan.
  2. **`valor_num` es el valor; el `n=` del texto es el tamaño de la muestra.** Son
     columnas distintas: 25 % de 12 docentes no es lo mismo que una muestra de 25.
  3. **El cumplimiento se lee, nunca se deduce.** Un valor que supera la meta pero sin
     declaración del productor sale como «—», no como «Sí»: el juicio depende del marco
     normativo, y el mismo número puede cumplir uno e incumplir otro.
  4. **No se totaliza.** Sumar porcentajes de programas distintos da una cifra que no
     existe en ninguno.

Convenciones (ver test_indicadores_acreditacion.py): IntegrationTestCase con rollback
por test y factories idempotentes.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc.sgc_nucleo.report.indicadores_de_acreditacion import indicadores_de_acreditacion as informe
from sgc.tests import factories

# Convención real de los conectores: el n= es la muestra, no el valor.
TEXTO_CUMPLE = "DW v1-norma Coneau 2026 · n=12 · meta >= 20% (cumple)"
TEXTO_NO_CUMPLE = "DW v1-norma Coneau 2026 · n=22 · meta >= 20% (NO cumple)"
TEXTO_SIN_JUICIO = "DW v1-norma Coneau 2026 · n=30 · meta >= 20%"


class IntegrationTestReportIndicadores(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.ps = factories.crear_programa_sede().name
        self.periodo = factories.crear_periodo_academico().name
        self.ind = factories.crear_indicador().name

    def _valor(self, texto, valor_num, fuente="dw", indicador=None):
        return factories.crear_valor_indicador(
            indicador or self.ind,
            programa_sede=self.ps,
            periodo_academico=self.periodo,
            valor_num=valor_num,
            valor_texto=texto,
            fuente=fuente,
        )

    def _ejecutar(self, **filtros):
        filtros.setdefault("periodo_academico", self.periodo)
        filtros.setdefault("programa_sede", self.ps)
        return informe.execute(filtros)

    def test_muestra_una_sola_fuente_y_cuenta_las_demas(self):
        self._valor(TEXTO_CUMPLE, 25.0, fuente="dw")
        self._valor(TEXTO_NO_CUMPLE, 18.18, fuente="lamb")
        _cols, filas, aviso, _chart, _resumen, _sin_total = self._ejecutar(fuente="dw")
        self.assertEqual([f["fuente"] for f in filas], ["dw"])
        self.assertIn("lamb", aviso or "", "la fuente que no se muestra debe declararse, no ocultarse")

    def test_sin_otras_fuentes_no_hay_aviso(self):
        self._valor(TEXTO_CUMPLE, 25.0, fuente="dw")
        _cols, _filas, aviso, _chart, _resumen, _sin_total = self._ejecutar(fuente="dw")
        self.assertIsNone(aviso, "no hay nada que advertir si solo existe una fuente")

    def test_el_valor_y_la_muestra_no_se_confunden(self):
        self._valor(TEXTO_CUMPLE, 25.0)
        _cols, filas, *_ = self._ejecutar(fuente="dw")
        self.assertEqual(filas[0]["valor"], 25.0, "el valor del indicador sale de valor_num")
        self.assertEqual(filas[0]["muestra"], 12.0, "la muestra es el n= del texto del productor")

    def test_el_cumplimiento_se_lee_no_se_deduce(self):
        # 30 supera de sobra la meta de 20 %, pero el productor no se pronunció.
        self._valor(TEXTO_SIN_JUICIO, 30.0)
        _cols, filas, *_ = self._ejecutar(fuente="dw")
        self.assertEqual(filas[0]["cumple"], "—", "sin declaración del productor no se inventa un juicio")

    def test_lee_el_juicio_declarado(self):
        self._valor(TEXTO_NO_CUMPLE, 18.18)
        _cols, filas, *_ = self._ejecutar(fuente="dw")
        self.assertEqual(filas[0]["cumple"], "No")
        self.assertEqual(filas[0]["meta"], ">= 20%")
        self.assertEqual(filas[0]["marco"], "Coneau 2026")

    def test_solo_incumplidos_deja_fuera_lo_que_cumple_y_lo_no_declarado(self):
        self._valor(TEXTO_CUMPLE, 25.0)
        self._valor(TEXTO_SIN_JUICIO, 30.0, indicador=factories.crear_indicador().name)
        self._valor(TEXTO_NO_CUMPLE, 18.18, indicador=factories.crear_indicador().name)
        _cols, filas, *_ = self._ejecutar(fuente="dw", solo_incumplidos=1)
        self.assertEqual([f["cumple"] for f in filas], ["No"])

    def test_no_totaliza(self):
        self._valor(TEXTO_CUMPLE, 25.0)
        resultado = self._ejecutar(fuente="dw")
        self.assertTrue(resultado[5], "sumar porcentajes de programas distintos da una cifra inexistente")

    def test_el_informe_esta_declarado_como_estandar(self):
        # Si el .json deja de ser estándar, migrate no lo crea y el panel queda con un
        # enlace muerto.
        import json
        import pathlib

        ruta = (
            pathlib.Path(frappe.get_app_path("sgc"))
            / "sgc_nucleo"
            / "report"
            / "indicadores_de_acreditacion"
            / "indicadores_de_acreditacion.json"
        )
        d = json.loads(ruta.read_text(encoding="utf-8"))
        self.assertEqual(d["is_standard"], "Yes")
        self.assertEqual(d["report_type"], "Script Report")
        self.assertEqual(d["ref_doctype"], "Valor Indicador")

    def test_el_panel_enlaza_el_informe(self):
        from sgc.setup import f18_workspace

        items = dict(f18_workspace.CARDS)["Marcos e indicadores"]
        self.assertIn(("Report", "Indicadores de Acreditacion"), items)
