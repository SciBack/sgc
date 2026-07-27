# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Suite de tests del M12 — Resultado de Instrumento.

Verifica el controlador (`resultado_instrumento.py`):
  validate():
    n negativo                          -> ValidationError
    unidad "%" con valor fuera de [0,100] -> ValidationError
    fecha_corte vacía                   -> hereda fecha_fin de la aplicación (o hoy)

La aplicación padre tiene Workflow; se desactiva en setUp para poder prepararla
con fechas sin transicionar.

Además prueba el PUENTE Encuestas -> Indicadores
(`publicar_valores_indicador`): agrupación por indicador EXPLÍCITO, herencia
desde `Instrumento.indicador`, omisión (nunca inferencia) de las filas sin
indicador declarado, promedio ponderado por `n`, back-link
`Resultado Instrumento.valor_indicador` e idempotencia del upsert.
"""
import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from sgc.sgc_gobierno.doctype.resultado_instrumento.resultado_instrumento import (
    publicar_valores_indicador,
)
from sgc.tests import factories

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []

PREF = "TESTM12R"

_seq_ind = iter(range(1, 10000))


def _crear_indicador(categoria="Satisfaccion"):
    """Indicador mínimo (autoname field:codigo; solo codigo+nombre son reqd).

    Se crea aquí y no en `sgc/tests/factories.py` porque ese archivo es
    compartido y queda fuera del alcance de este cambio.
    """
    codigo = f"{PREF}-IND-{next(_seq_ind)}"
    if frappe.db.exists("Indicador", codigo):
        return codigo
    doc = frappe.get_doc({
        "doctype": "Indicador",
        "codigo": codigo,
        "nombre": f"Indicador de prueba {codigo}",
        "categoria": categoria,
    })
    doc.insert(ignore_permissions=True)
    return doc.name


class IntegrationTestResultadoInstrumento(IntegrationTestCase):
    """Validaciones del Resultado de Instrumento (M12)."""

    def setUp(self):
        factories.desactivar_workflow("Aplicacion Instrumento")
        self.apl = factories.crear_aplicacion_instrumento(prefijo=PREF)

    def test_n_negativo_falla(self):
        with self.assertRaises(frappe.ValidationError):
            factories.crear_resultado_instrumento(
                self.apl, dimension="Trato", valor=3.0, n=-1, prefijo=PREF
            )

    def test_porcentaje_fuera_de_rango_falla(self):
        with self.assertRaises(frappe.ValidationError):
            factories.crear_resultado_instrumento(
                self.apl, dimension="Satisfacción", valor=150.0, unidad="%", n=10, prefijo=PREF
            )

    def test_porcentaje_en_rango_ok(self):
        res = factories.crear_resultado_instrumento(
            self.apl, dimension="Satisfacción", valor=87.5, unidad="%", n=10, prefijo=PREF
        )
        self.assertEqual(res.valor, 87.5)

    def test_fecha_corte_hereda_fecha_fin_de_aplicacion(self):
        fin = nowdate()
        self.apl.fecha_inicio = add_days(fin, -10)
        self.apl.fecha_fin = fin
        self.apl.flags.ignore_permissions = True
        self.apl.save(ignore_permissions=True)
        res = factories.crear_resultado_instrumento(
            self.apl, dimension="Trato", valor=4.0, n=5, prefijo=PREF
        )
        self.assertEqual(str(res.fecha_corte), fin)

    def test_fecha_corte_explicita_se_respeta(self):
        corte = add_days(nowdate(), -3)
        res = factories.crear_resultado_instrumento(
            self.apl, dimension="Trato", valor=4.0, n=5, fecha_corte=corte, prefijo=PREF
        )
        self.assertEqual(str(res.fecha_corte), corte)

    # ======================================================================
    # Puente Encuestas -> Indicadores (publicar_valores_indicador)
    # ======================================================================
    def test_publicar_sin_indicador_declarado_omite_todo(self):
        """Regla dura: sin enlace explícito NO se adivina por el texto de la
        dimensión — la fila se omite y se cuenta."""
        factories.crear_resultado_instrumento(
            self.apl, dimension="Satisfacción general", valor=4.0, n=10, prefijo=PREF
        )
        res = publicar_valores_indicador(self.apl.name)
        self.assertEqual(res["n_publicados"], 0)
        self.assertEqual(res["publicados"], [])
        self.assertEqual(res["omitidas"], 1)
        self.assertEqual(res["dimensiones_omitidas"], ["Satisfacción general"])

    def test_publicar_agrupa_por_indicador_explicito_con_ponderado(self):
        """Dos dimensiones que tributan al MISMO indicador se fusionan en un
        único Valor Indicador con el promedio ponderado por n."""
        ind = _crear_indicador()
        factories.crear_resultado_instrumento(
            self.apl, dimension="Trato", valor=4.0, n=10, indicador=ind, prefijo=PREF
        )
        factories.crear_resultado_instrumento(
            self.apl, dimension="Aulas", valor=2.0, n=30, indicador=ind, prefijo=PREF
        )
        res = publicar_valores_indicador(self.apl.name)

        self.assertEqual(res["n_publicados"], 1)
        self.assertEqual(res["omitidas"], 0)
        pub = res["publicados"][0]
        self.assertEqual(pub["indicador"], ind)
        self.assertEqual(pub["n"], 40)
        self.assertEqual(pub["n_filas"], 2)
        # Ponderado: (4*10 + 2*30) / 40 = 2.5 (el simple sería 3.0).
        self.assertEqual(pub["valor_num"], 2.5)
        self.assertEqual(
            frappe.db.get_value("Valor Indicador", pub["valor_indicador"], "valor_num"), 2.5
        )

    def test_publicar_separa_indicadores_distintos(self):
        ind_a = _crear_indicador()
        ind_b = _crear_indicador()
        factories.crear_resultado_instrumento(
            self.apl, dimension="Trato", valor=4.0, n=10, indicador=ind_a, prefijo=PREF
        )
        factories.crear_resultado_instrumento(
            self.apl, dimension="Aulas", valor=2.0, n=10, indicador=ind_b, prefijo=PREF
        )
        res = publicar_valores_indicador(self.apl.name)
        self.assertEqual(res["n_publicados"], 2)
        por_ind = {p["indicador"]: p for p in res["publicados"]}
        self.assertEqual(por_ind[ind_a]["valor_num"], 4.0)
        self.assertEqual(por_ind[ind_b]["valor_num"], 2.0)

    def test_publicar_hereda_indicador_del_instrumento(self):
        """La fila sin `indicador` hereda el de la plantilla `Instrumento`."""
        ind = _crear_indicador()
        instrumento = factories.crear_instrumento(prefijo=PREF, indicador=ind).name
        apl = factories.crear_aplicacion_instrumento(instrumento=instrumento, prefijo=PREF)
        factories.crear_resultado_instrumento(
            apl, dimension="Trato", valor=3.0, n=5, prefijo=PREF
        )
        res = publicar_valores_indicador(apl.name)
        self.assertEqual(res["omitidas"], 0)
        self.assertEqual(res["publicados"][0]["indicador"], ind)

    def test_publicar_la_fila_gana_sobre_la_plantilla(self):
        ind_plantilla = _crear_indicador()
        ind_fila = _crear_indicador()
        instrumento = factories.crear_instrumento(prefijo=PREF, indicador=ind_plantilla).name
        apl = factories.crear_aplicacion_instrumento(instrumento=instrumento, prefijo=PREF)
        factories.crear_resultado_instrumento(
            apl, dimension="Trato", valor=3.0, n=5, indicador=ind_fila, prefijo=PREF
        )
        res = publicar_valores_indicador(apl.name)
        self.assertEqual([p["indicador"] for p in res["publicados"]], [ind_fila])

    def test_publicar_mezcla_declaradas_y_omitidas(self):
        ind = _crear_indicador()
        factories.crear_resultado_instrumento(
            self.apl, dimension="Trato", valor=4.0, n=10, indicador=ind, prefijo=PREF
        )
        factories.crear_resultado_instrumento(
            self.apl, dimension="Huérfana", valor=1.0, n=99, prefijo=PREF
        )
        res = publicar_valores_indicador(self.apl.name)
        self.assertEqual(res["n_publicados"], 1)
        self.assertEqual(res["omitidas"], 1)
        self.assertEqual(res["dimensiones_omitidas"], ["Huérfana"])
        # La fila omitida NO contamina el n del valor publicado.
        self.assertEqual(res["publicados"][0]["n"], 10)

    def test_publicar_sin_n_cae_a_promedio_simple(self):
        ind = _crear_indicador()
        factories.crear_resultado_instrumento(
            self.apl, dimension="Trato", valor=5.0, indicador=ind, prefijo=PREF
        )
        factories.crear_resultado_instrumento(
            self.apl, dimension="Aulas", valor=2.0, indicador=ind, prefijo=PREF
        )
        res = publicar_valores_indicador(self.apl.name)
        # n total = 0 -> no hay ponderación posible: (5+2)/2 = 3.5
        self.assertEqual(res["publicados"][0]["valor_num"], 3.5)

    def test_publicar_omite_grupo_sin_valor_numerico(self):
        ind = _crear_indicador()
        factories.crear_resultado_instrumento(
            self.apl, dimension="Trato", n=10, indicador=ind, prefijo=PREF
        )
        res = publicar_valores_indicador(self.apl.name)
        self.assertEqual(res["n_publicados"], 0)
        self.assertEqual(res["omitidas"], 1)

    def test_publicar_escribe_el_back_link_en_las_filas(self):
        ind = _crear_indicador()
        r1 = factories.crear_resultado_instrumento(
            self.apl, dimension="Trato", valor=4.0, n=10, indicador=ind, prefijo=PREF
        )
        r2 = factories.crear_resultado_instrumento(
            self.apl, dimension="Aulas", valor=2.0, n=10, indicador=ind, prefijo=PREF
        )
        res = publicar_valores_indicador(self.apl.name)
        vi = res["publicados"][0]["valor_indicador"]
        self.assertEqual(
            frappe.db.get_value("Resultado Instrumento", r1.name, "valor_indicador"), vi
        )
        self.assertEqual(
            frappe.db.get_value("Resultado Instrumento", r2.name, "valor_indicador"), vi
        )

    def test_publicar_marca_fuente_encuesta_y_calculado(self):
        ind = _crear_indicador()
        self.apl.fecha_inicio = add_days(nowdate(), -10)
        self.apl.fecha_fin = nowdate()
        self.apl.save(ignore_permissions=True)
        factories.crear_resultado_instrumento(
            self.apl, dimension="Trato", valor=4.0, n=10, indicador=ind, prefijo=PREF
        )
        res = publicar_valores_indicador(self.apl.name)
        vi = frappe.get_doc("Valor Indicador", res["publicados"][0]["valor_indicador"])
        self.assertEqual(vi.fuente, "encuesta")
        self.assertEqual(vi.calculado, 1)
        self.assertEqual(vi.indicador, ind)
        self.assertIn(self.apl.name, vi.valor_texto)
        # La fecha del valor es el corte real del campo (fin de la aplicación).
        self.assertEqual(str(vi.fecha)[:10], nowdate())

    def test_publicar_copia_el_ambito_de_la_aplicacion(self):
        ind = _crear_indicador()
        codigo_periodo = f"{PREF}-PER-1"
        if not frappe.db.exists("Periodo Academico", codigo_periodo):
            frappe.get_doc({
                "doctype": "Periodo Academico",
                "codigo": codigo_periodo,
                "anio": 2026,
                "semestre": "I",
            }).insert(ignore_permissions=True)
        apl = factories.crear_aplicacion_instrumento(
            prefijo=PREF, periodo_academico=codigo_periodo
        )
        factories.crear_resultado_instrumento(
            apl, dimension="Trato", valor=4.0, n=10, indicador=ind, prefijo=PREF
        )
        res = publicar_valores_indicador(apl.name)
        self.assertEqual(
            frappe.db.get_value(
                "Valor Indicador", res["publicados"][0]["valor_indicador"], "periodo_academico"
            ),
            codigo_periodo,
        )

    def test_publicar_es_idempotente(self):
        """Re-publicar no duplica: actualiza el mismo Valor Indicador."""
        ind = _crear_indicador()
        r1 = factories.crear_resultado_instrumento(
            self.apl, dimension="Trato", valor=4.0, n=10, indicador=ind, prefijo=PREF
        )
        primera = publicar_valores_indicador(self.apl.name)
        vi = primera["publicados"][0]["valor_indicador"]

        # Cambia el dato de origen y vuelve a publicar.
        frappe.db.set_value("Resultado Instrumento", r1.name, "valor", 2.0)
        segunda = publicar_valores_indicador(self.apl.name)

        self.assertEqual(segunda["publicados"][0]["valor_indicador"], vi)
        self.assertEqual(
            frappe.db.count("Valor Indicador", {"indicador": ind, "fuente": "encuesta"}), 1
        )
        self.assertEqual(frappe.db.get_value("Valor Indicador", vi, "valor_num"), 2.0)

    def test_publicar_auto_sana_valores_duplicados(self):
        """Si el grupo apunta a más de un Valor Indicador (publicaciones
        concurrentes), se conserva el más antiguo y se reapuntan las filas."""
        ind = _crear_indicador()
        r1 = factories.crear_resultado_instrumento(
            self.apl, dimension="Trato", valor=4.0, n=10, indicador=ind, prefijo=PREF
        )
        r2 = factories.crear_resultado_instrumento(
            self.apl, dimension="Aulas", valor=4.0, n=10, indicador=ind, prefijo=PREF
        )
        vi_original = publicar_valores_indicador(self.apl.name)["publicados"][0][
            "valor_indicador"
        ]

        # Simula el duplicado: un segundo Valor Indicador del mismo motor al que
        # apunta una de las filas.
        duplicado = frappe.get_doc({
            "doctype": "Valor Indicador",
            "indicador": ind,
            "valor_num": 99.0,
            "fuente": "encuesta",
            "calculado": 1,
        })
        duplicado.insert(ignore_permissions=True)
        frappe.db.set_value(
            "Resultado Instrumento", r2.name, "valor_indicador", duplicado.name,
            update_modified=False,
        )

        res = publicar_valores_indicador(self.apl.name)
        self.assertEqual(res["publicados"][0]["valor_indicador"], vi_original)
        self.assertFalse(frappe.db.exists("Valor Indicador", duplicado.name))
        for r in (r1, r2):
            self.assertEqual(
                frappe.db.get_value("Resultado Instrumento", r.name, "valor_indicador"),
                vi_original,
            )

    def test_republicar_tras_corregir_el_indicador_no_pisa_el_valor_anterior(self):
        """Regresión: corregir el Indicador de una fila ya publicada NO puede
        colapsar dos grupos sobre el mismo Valor Indicador.

        El back-link de la fila corregida sigue apuntando al Valor Indicador del
        indicador ANTERIOR. Si la identidad se resolviera solo por `name`, el
        grupo nuevo reutilizaría ese documento y lo pisaría: quedaría UN solo
        Valor Indicador y el del indicador viejo desaparecería en silencio, sin
        auto-sanarse nunca. Es el caso de uso que documenta `publicar_indicadores`
        ("si se corrige el Indicador declarado, Calidad puede re-publicar").
        """
        ind_a = _crear_indicador()
        ind_b = _crear_indicador()
        r1 = factories.crear_resultado_instrumento(
            self.apl, dimension="Trato", valor=80.0, n=100, indicador=ind_a, prefijo=PREF
        )
        r2 = factories.crear_resultado_instrumento(
            self.apl, dimension="Aulas", valor=60.0, n=100, indicador=ind_a, prefijo=PREF
        )
        primera = publicar_valores_indicador(self.apl.name)
        self.assertEqual(primera["n_publicados"], 1)  # ambas filas -> un indicador
        vi_a = primera["publicados"][0]["valor_indicador"]

        # Calidad corrige: la 2ª fila en realidad tributa a otro indicador.
        frappe.db.set_value("Resultado Instrumento", r2.name, "indicador", ind_b,
                            update_modified=False)

        res = publicar_valores_indicador(self.apl.name)
        self.assertEqual(res["n_publicados"], 2)

        por_ind = {p["indicador"]: p for p in res["publicados"]}
        self.assertEqual(sorted(por_ind), sorted([ind_a, ind_b]))
        # Dos documentos DISTINTOS: ninguno pisó al otro.
        self.assertNotEqual(por_ind[ind_a]["valor_indicador"],
                            por_ind[ind_b]["valor_indicador"])
        # El valor de cada indicador es el de su propia fila, sin mezclarse.
        self.assertEqual(
            frappe.db.get_value("Valor Indicador", por_ind[ind_a]["valor_indicador"],
                                "valor_num"), 80.0)
        self.assertEqual(
            frappe.db.get_value("Valor Indicador", por_ind[ind_b]["valor_indicador"],
                                "valor_num"), 60.0)
        # El Valor Indicador original sigue vivo y sigue siendo el de ind_a.
        self.assertTrue(frappe.db.exists("Valor Indicador", vi_a))
        self.assertEqual(
            frappe.db.get_value("Valor Indicador", vi_a, "indicador"), ind_a)
        self.assertEqual(
            frappe.db.get_value("Resultado Instrumento", r1.name, "valor_indicador"), vi_a)

    def test_publicar_no_pisa_un_valor_indicador_de_otra_fuente(self):
        """Regresión: `Resultado Instrumento.valor_indicador` es un Link EDITABLE
        (DPGC/Analista/Data Steward tienen escritura). Si alguien lo apunta a un
        Valor Indicador cargado por los conectores MidPoint/Oracle, este motor no
        puede reescribirlo: crearía un valor de encuesta encima de una medición
        institucional, y `ignore_version` borraría hasta el rastro en el historial.
        """
        ind = _crear_indicador()
        ajeno = frappe.get_doc({
            "doctype": "Valor Indicador",
            "indicador": ind,
            "valor_num": 1234.0,
            "fuente": "midpoint",
            "calculado": 1,
        })
        ajeno.insert(ignore_permissions=True)

        r1 = factories.crear_resultado_instrumento(
            self.apl, dimension="Trato", valor=5.0, n=10, indicador=ind, prefijo=PREF
        )
        frappe.db.set_value("Resultado Instrumento", r1.name, "valor_indicador",
                            ajeno.name, update_modified=False)

        res = publicar_valores_indicador(self.apl.name)

        # Se publicó en un documento NUEVO, no en el ajeno.
        self.assertEqual(res["n_publicados"], 1)
        self.assertNotEqual(res["publicados"][0]["valor_indicador"], ajeno.name)
        # El ajeno quedó intacto: mismo valor, misma fuente, no fue borrado.
        self.assertTrue(frappe.db.exists("Valor Indicador", ajeno.name))
        ajeno_ahora = frappe.db.get_value(
            "Valor Indicador", ajeno.name, ["valor_num", "fuente"], as_dict=True)
        self.assertEqual(ajeno_ahora.valor_num, 1234.0)
        self.assertEqual(ajeno_ahora.fuente, "midpoint")

    def test_publicar_sin_n_en_una_fila_usa_promedio_simple(self):
        """Regresión: `n` es Int (NOT NULL DEFAULT 0), así que "no lo llenaron"
        es indistinguible de 0. Ponderar con un `n` faltante le daría peso CERO a
        esa fila, borrándola del promedio en silencio. Si a alguna fila con valor
        le falta `n`, el grupo entero cae a promedio simple.
        """
        ind = _crear_indicador()
        factories.crear_resultado_instrumento(
            self.apl, dimension="Trato", valor=10.0, n=1000, indicador=ind, prefijo=PREF
        )
        factories.crear_resultado_instrumento(
            self.apl, dimension="Aulas", valor=20.0, indicador=ind, prefijo=PREF
        )  # sin n

        res = publicar_valores_indicador(self.apl.name)

        # Ponderado habría dado ~10.0 (la 2ª fila pesaría 0); simple da 15.0.
        self.assertEqual(
            frappe.db.get_value(
                "Valor Indicador", res["publicados"][0]["valor_indicador"], "valor_num"),
            15.0,
        )

    def test_publicar_aplicacion_inexistente_falla(self):
        with self.assertRaises(frappe.ValidationError):
            publicar_valores_indicador("APL-9999-99999")

    def test_publicar_aplicacion_vacia_no_crea_nada(self):
        res = publicar_valores_indicador(self.apl.name)
        self.assertEqual(res["n_publicados"], 0)
        self.assertEqual(res["omitidas"], 0)
