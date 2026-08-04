# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Tests del motor lector de indicadores de acreditación medidos.

Cubre las cuatro reglas de diseño de `sgc/indicadores_acreditacion.py`, que son
las que hacen que la cifra mostrada sea la del productor y no una inventada por
la vista:

  1. El enganche se resuelve por (programa_sede, periodo_academico) y NO por el
     Link `autoevaluacion`, que los conectores dejan vacío a propósito.
  2. Nunca se mezclan fuentes: dos productores del mismo indicador no se suman
     ni se promedian; el que no se muestra se reporta en `otras_fuentes()`.
  3. Nunca se mezclan granos: el valor institucional (sin programa_sede) no
     entra en la vista de un programa.
  4. Nunca se infiere el cumplimiento: sin declaración del productor, `cumple`
     queda en None aunque el valor supere la meta.

Convenciones (ver test_www.py): IntegrationTestCase con rollback por test,
factories idempotentes, y toda operación de doc con ignore_permissions=True.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc import indicadores_acreditacion as ia
from sgc.tests import factories

# Convención real de los conectores, tal como llega en `valor_texto`.
TEXTO_CUMPLE = "DW v1-norma Coneau 2026 · n=452 · meta 80% (cumple)"
TEXTO_NO_CUMPLE = "DW v1-norma Coneau 2026 · n=25 · meta 20% (NO cumple)"
TEXTO_PROVISIONAL = (
    "DW v1-norma Coneau 2026 · n=1200 · meta 80% (NO cumple) · PROVISIONAL (cobertura 77.6%)"
)


class IntegrationTestIndicadoresAcreditacion(IntegrationTestCase):
    """Lectura de `Valor Indicador` resuelta contra una Autoevaluacion."""

    def setUp(self):
        frappe.set_user("Administrator")
        self.marco = factories.crear_marco_prueba(n_estandares=1, n_criterios=1)["marco"]
        self.ps = factories.crear_programa_sede().name
        self.periodo = factories.crear_periodo_academico().name
        self.ae = factories.crear_autoevaluacion(
            self.marco, programa_sede=self.ps, periodo_academico=self.periodo
        ).name

    def _publicar(self, codigo, **kwargs):
        """Publica una medición del indicador `codigo` en el par de la AE."""
        ind = factories.crear_indicador(codigo=codigo)
        kwargs.setdefault("programa_sede", self.ps)
        kwargs.setdefault("periodo_academico", self.periodo)
        return factories.crear_valor_indicador(ind, **kwargs)

    # ======================================================================
    # Regla 1 — el enganche es por (programa_sede, periodo), no por el Link
    # ======================================================================
    def test_lee_mediciones_con_autoevaluacion_vacia(self):
        """El valor se muestra aunque el conector no haya poblado `autoevaluacion`."""
        vi = self._publicar("TEST-ID10", valor_num=88.22, valor_texto=TEXTO_CUMPLE)
        self.assertFalse(vi.get("autoevaluacion"))   # como publica el conector real

        res = ia.indicadores_de_autoevaluacion(self.ae)

        self.assertIsNone(res["motivo"])
        self.assertEqual(len(res["filas"]), 1)
        fila = res["filas"][0]
        self.assertEqual(fila["indicador"], "TEST-ID10")
        self.assertEqual(fila["valor_num"], 88.22)

    def test_ignora_mediciones_de_otro_programa_o_periodo(self):
        """Otro programa u otro periodo no entran en la vista de esta AE."""
        self._publicar("TEST-ID10", valor_num=88.22, valor_texto=TEXTO_CUMPLE)
        otro_ps = factories.crear_programa_sede().name
        otro_periodo = factories.crear_periodo_academico().name
        self._publicar("TEST-ID20", valor_num=10.0, programa_sede=otro_ps)
        self._publicar("TEST-ID30", valor_num=20.0, periodo_academico=otro_periodo)

        codigos = [f["indicador"] for f in ia.indicadores_de_autoevaluacion(self.ae)["filas"]]
        self.assertEqual(codigos, ["TEST-ID10"])

    def test_ae_sin_programa_o_sin_periodo_reporta_el_motivo(self):
        """Sin par resoluble no se adivina: se devuelve vacío con el motivo."""
        ae_sin_ps = factories.crear_autoevaluacion(
            self.marco, periodo_academico=self.periodo
        ).name
        res = ia.indicadores_de_autoevaluacion(ae_sin_ps)
        self.assertEqual(res["filas"], [])
        self.assertEqual(res["motivo"], ia.SIN_PROGRAMA)

        ae_sin_periodo = factories.crear_autoevaluacion(self.marco, programa_sede=self.ps).name
        res = ia.indicadores_de_autoevaluacion(ae_sin_periodo)
        self.assertEqual(res["motivo"], ia.SIN_PERIODO)

    def test_par_sin_mediciones_reporta_el_motivo(self):
        """Un par válido pero sin publicaciones se distingue de un par irresoluble."""
        res = ia.indicadores_de_autoevaluacion(self.ae)
        self.assertEqual(res["filas"], [])
        self.assertEqual(res["motivo"], ia.SIN_MEDICIONES)

    # ======================================================================
    # Regla 2 — una fuente a la vez; las demás se reportan, no se ocultan
    # ======================================================================
    def test_no_mezcla_fuentes_del_mismo_indicador(self):
        """Dos productores del mismo indicador -> solo el de la fuente pedida."""
        ind = factories.crear_indicador(codigo="TEST-ID10")
        factories.crear_valor_indicador(
            ind, self.ps, self.periodo, valor_num=88.22, fuente="dw"
        )
        factories.crear_valor_indicador(
            ind, self.ps, self.periodo, valor_num=71.40, fuente="lamb"
        )

        res = ia.indicadores_de_autoevaluacion(self.ae, fuente="dw")
        self.assertEqual(len(res["filas"]), 1)
        self.assertEqual(res["filas"][0]["valor_num"], 88.22)

        res_lamb = ia.indicadores_de_autoevaluacion(self.ae, fuente="lamb")
        self.assertEqual(res_lamb["filas"][0]["valor_num"], 71.40)

    def test_otras_fuentes_reporta_los_productores_no_mostrados(self):
        """La vista puede advertir que hay otra cifra publicada del mismo par."""
        ind = factories.crear_indicador(codigo="TEST-ID10")
        factories.crear_valor_indicador(ind, self.ps, self.periodo, valor_num=88.2, fuente="dw")
        factories.crear_valor_indicador(ind, self.ps, self.periodo, valor_num=71.4, fuente="lamb")
        otro = factories.crear_indicador(codigo="TEST-ID11")
        factories.crear_valor_indicador(otro, self.ps, self.periodo, valor_num=5.0, fuente="lamb")

        otras = ia.otras_fuentes(self.ae, excepto="dw")

        self.assertEqual(otras, [{"fuente": "lamb", "n_indicadores": 2}])

    def test_otras_fuentes_agrupa_las_publicaciones_sin_fuente(self):
        """Un valor sin `fuente` se agrupa como '(sin fuente)', no se descarta."""
        ind = factories.crear_indicador(codigo="TEST-ID10")
        factories.crear_valor_indicador(ind, self.ps, self.periodo, valor_num=1.0, fuente="")

        otras = ia.otras_fuentes(self.ae, excepto="dw")
        self.assertEqual(otras, [{"fuente": "(sin fuente)", "n_indicadores": 1}])

    # ======================================================================
    # Regla 3 — un solo grano de desagregación
    # ======================================================================
    def test_no_mezcla_el_grano_institucional(self):
        """El valor institucional (sin programa_sede) no entra en la vista del programa."""
        ind = factories.crear_indicador(codigo="TEST-INST-ID11")
        # Institucional: el conector publica sin programa_sede ni unidad_organica.
        factories.crear_valor_indicador(ind, None, self.periodo, valor_num=36.0)
        # Mismo indicador, grano programa-sede.
        factories.crear_valor_indicador(ind, self.ps, self.periodo, valor_num=41.5)

        res = ia.indicadores_de_autoevaluacion(self.ae)
        self.assertEqual(len(res["filas"]), 1)
        self.assertEqual(res["filas"][0]["valor_num"], 41.5)

    def test_una_fila_por_indicador_la_mas_reciente(self):
        """Varias publicaciones del mismo indicador -> se muestra la última."""
        ind = factories.crear_indicador(codigo="TEST-ID10")
        factories.crear_valor_indicador(
            ind, self.ps, self.periodo, valor_num=70.0, fecha="2026-07-01 05:00:00"
        )
        factories.crear_valor_indicador(
            ind, self.ps, self.periodo, valor_num=88.22, fecha="2026-08-04 05:00:00"
        )

        res = ia.indicadores_de_autoevaluacion(self.ae)
        self.assertEqual(len(res["filas"]), 1)
        self.assertEqual(res["filas"][0]["valor_num"], 88.22)

    # ======================================================================
    # Regla 4 — el cumplimiento se lee, no se deduce
    # ======================================================================
    def test_no_infiere_cumplimiento_sin_declaracion(self):
        """Sin '(cumple)' en el texto, `cumple` es None aunque supere la meta."""
        self._publicar("TEST-ID10", valor_num=99.0, valor_texto="Calculado desde el DW")

        fila = ia.indicadores_de_autoevaluacion(self.ae)["filas"][0]
        self.assertIsNone(fila["cumple"])

    def test_no_cumple_no_se_lee_como_cumple(self):
        """'NO cumple' contiene 'cumple': el negativo debe ganar."""
        self._publicar("TEST-ID13", valor_num=0.0, valor_texto=TEXTO_NO_CUMPLE)

        fila = ia.indicadores_de_autoevaluacion(self.ae)["filas"][0]
        self.assertIs(fila["cumple"], False)
        self.assertEqual(fila["meta"], 20.0)
        self.assertEqual(fila["n"], 25.0)

    # ======================================================================
    # Parseo del texto del productor (contrato tolerante)
    # ======================================================================
    def test_parseo_del_contrato_completo(self):
        """La convención del conector se descompone en sus metadatos."""
        m = ia._parsear_valor_texto(TEXTO_PROVISIONAL)

        self.assertTrue(m["contrato_reconocido"])
        self.assertEqual(m["n"], 1200.0)
        self.assertEqual(m["meta"], 80.0)
        self.assertEqual(m["meta_sufijo"], "%")
        self.assertIs(m["cumple"], False)
        self.assertTrue(m["provisional"])
        self.assertEqual(m["cobertura"], 77.6)

    def test_parseo_tolera_texto_libre_y_texto_vacio(self):
        """Un texto fuera de convención no rompe: queda crudo y sin reconocer."""
        m = ia._parsear_valor_texto("Cargado a mano por la DPGC")
        self.assertFalse(m["contrato_reconocido"])
        self.assertEqual(m["texto"], "Cargado a mano por la DPGC")
        self.assertIsNone(m["meta"])

        vacio = ia._parsear_valor_texto(None)
        self.assertFalse(vacio["contrato_reconocido"])
        self.assertEqual(vacio["texto"], "")

    def test_parseo_lee_meta_con_operador_y_coma_decimal(self):
        """'meta ≥ 80,5%' se lee con su operador y su coma decimal."""
        m = ia._parsear_valor_texto("n=10 · meta ≥ 80,5% (cumple)")
        self.assertEqual(m["meta"], 80.5)
        self.assertEqual(m["meta_operador"], "≥")
        self.assertIs(m["cumple"], True)

    # ======================================================================
    # Presentación derivada del catálogo (nombre, unidad, orden)
    # ======================================================================
    def test_toma_nombre_del_catalogo_y_unidad_de_la_ficha(self):
        """El nombre viene de `Indicador` y la unidad de su `Ficha Indicador`."""
        ind = factories.crear_indicador(
            codigo="TEST-ID10", nombre="% de estudiantes aprobados por asignatura"
        )
        frappe.get_doc({
            "doctype": "Ficha Indicador",
            "indicador": ind.name,
            "unidad": "Porcentaje",
        }).insert(ignore_permissions=True)
        factories.crear_valor_indicador(ind, self.ps, self.periodo, valor_num=88.22)

        fila = ia.indicadores_de_autoevaluacion(self.ae)["filas"][0]
        self.assertEqual(fila["nombre"], "% de estudiantes aprobados por asignatura")
        self.assertEqual(fila["unidad"], "Porcentaje")
        self.assertEqual(fila["sufijo"], "%")

    def test_sufijo_de_unidad_solo_pega_lo_corto(self):
        """'Porcentaje' y '%' pegan al número; una frase larga, no."""
        self.assertEqual(ia._sufijo_de_unidad("%"), "%")
        self.assertEqual(ia._sufijo_de_unidad("Porcentaje"), "%")
        self.assertEqual(ia._sufijo_de_unidad("hrs"), "hrs")
        self.assertEqual(ia._sufijo_de_unidad("Docentes a tiempo completo"), "")
        self.assertEqual(ia._sufijo_de_unidad(None), "")

    def test_orden_natural_de_codigos(self):
        """ID6 antes que ID10; los INST-* después, por prefijo."""
        for codigo in ("TEST-ID10", "TEST-ID6", "TEST-INST-ID11"):
            self._publicar(codigo, valor_num=1.0)

        codigos = [f["indicador"] for f in ia.indicadores_de_autoevaluacion(self.ae)["filas"]]
        self.assertEqual(codigos, ["TEST-ID6", "TEST-ID10", "TEST-INST-ID11"])

    # ======================================================================
    # Contador de portada
    # ======================================================================
    def test_contador_cuenta_indicadores_distintos_entre_fuentes(self):
        """Dos fuentes midiendo el mismo indicador siguen siendo un indicador."""
        ind = factories.crear_indicador(codigo="TEST-ID10")
        factories.crear_valor_indicador(ind, self.ps, self.periodo, valor_num=88.2, fuente="dw")
        factories.crear_valor_indicador(ind, self.ps, self.periodo, valor_num=71.4, fuente="lamb")
        otro = factories.crear_indicador(codigo="TEST-ID11")
        factories.crear_valor_indicador(otro, self.ps, self.periodo, valor_num=36.0, fuente="dw")

        self.assertEqual(ia.contar_indicadores_medidos(self.ae), 2)

    def test_contador_es_cero_si_el_par_no_resuelve(self):
        """Sin programa o sin periodo el contador es 0, no una excepción."""
        ae = factories.crear_autoevaluacion(self.marco).name
        self.assertEqual(ia.contar_indicadores_medidos(ae), 0)

    # ======================================================================
    # Fuente preferida (configurable por institución)
    # ======================================================================
    def test_fuente_preferida_usa_el_default_del_sitio(self):
        """La fuente por defecto se cambia por default de sitio, sin tocar código."""
        self.assertEqual(ia.fuente_preferida(), ia.FUENTE_POR_DEFECTO)

        frappe.db.set_default(ia.CLAVE_DEFAULT_FUENTE, "etl-academico")
        try:
            self.assertEqual(ia.fuente_preferida(), "etl-academico")
            # Y la lectura sin `fuente` explícita respeta ese default.
            self.assertEqual(
                ia.indicadores_de_autoevaluacion(self.ae)["fuente"], "etl-academico"
            )
        finally:
            frappe.db.set_default(ia.CLAVE_DEFAULT_FUENTE, ia.FUENTE_POR_DEFECTO)
