# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Tests de integración de las páginas Jinja server-side del SGC (`sgc/www/*`).

Cada página expone `get_context(context)`, que arma el contexto que consume la
plantilla de la SPA/portal. Estos tests verifican, contra un árbol mínimo sembrado
con `sgc.tests.factories`, que:

  - `index.get_context`     — portal público: puebla las métricas vivas sin sesión.
  - `sgc.get_context`       — SPA: inyecta el boot context (csrf, usuario, rol).
  - `tablero.get_context`   — vista ejecutiva: elige la autoevaluación reciente,
                              arma el semáforo NL/L/LP y los contadores coherentes.
  - `estandar.get_context`  — detalle de estándar: criterios + nivel propuesto.
  - `criterio.get_context`  — detalle de criterio: valoración + hallazgos + evidencias.
  - `mejora.get_context`    — ciclo CAPA: hallazgos, planes y acciones.
  - `api.get_niveles_escala`— catálogo de la escala NL/L/LP en orden.

Convenciones (ver test_scoring.py): IntegrationTestCase con rollback por test,
factories idempotentes, y toda operación de doc con ignore_permissions=True.

Los `get_context` que leen parámetros de página los toman de `frappe.form_dict`;
aquí se simulan poblando `frappe.form_dict` antes de llamar y limpiándolo en
tearDown. El objeto `context` se simula con un `frappe._dict()` vacío.
"""
import inspect

import frappe
from frappe.tests import IntegrationTestCase

from sgc import api
from sgc.tests import factories
from sgc.www import criterio, estandar, index, mejora, sgc, tablero


class IntegrationTestWww(IntegrationTestCase):
    """Contexto server-side de las páginas a medida del SGC (`sgc/www`)."""

    def setUp(self):
        # Los get_context autenticados exigen una sesión != Guest; los tests
        # corren como Administrator (que además tiene System Manager).
        frappe.set_user("Administrator")

        # mejora.get_context siembra Plan/Accion Mejora con estados no iniciales;
        # ambos tienen Workflow activo en prod, así que se desactiva para el caso.
        factories.desactivar_workflow("Plan Mejora")
        factories.desactivar_workflow("Accion Mejora")

        # Árbol base: 3 estándares × 3 criterios + escala NL/L/LP.
        self.arbol = factories.crear_marco_prueba(n_estandares=3, n_criterios=3)
        self.marco = self.arbol["marco"]
        self.estandares = self.arbol["estandares"]     # ["TEST-E1", "TEST-E2", "TEST-E3"]
        self.criterios = self.arbol["criterios"]       # {est: [criterios]}
        self.ae = factories.crear_autoevaluacion(self.marco).name

    def tearDown(self):
        # Dejar limpio el form_dict para no filtrar parámetros a otros tests.
        frappe.local.form_dict = frappe._dict()

    # -- helpers ------------------------------------------------------------
    def _ctx(self, **form):
        """Simula un request: puebla form_dict y devuelve un context vacío."""
        if form:
            frappe.local.form_dict.update(form)
        return frappe._dict()

    def _crear_hallazgo(self, criterio_name, codigo, estado="Abierto"):
        doc = frappe.get_doc({
            "doctype": "Hallazgo",
            "codigo": codigo,
            "tipo": "Debilidad",
            "severidad": "Alta",
            "estado": estado,
            "autoevaluacion": self.ae,
            "criterio": criterio_name,
            "descripcion": "Hallazgo de prueba",
        })
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc

    def _crear_plan_con_accion(self, plan_codigo, accion_codigo, avance=50):
        plan = frappe.get_doc({
            "doctype": "Plan Mejora",
            "codigo": plan_codigo,
            "titulo": "Plan de prueba",
            "estado": "En ejecucion",
            "autoevaluacion": self.ae,
        })
        plan.flags.ignore_permissions = True
        plan.insert(ignore_permissions=True)

        accion = frappe.get_doc({
            "doctype": "Accion Mejora",
            "codigo": accion_codigo,
            "descripcion": "Accion de prueba",
            "tipo": "Correctiva",
            "estado": "En ejecucion",   # respeta el avance_pct manual
            "avance_pct": avance,
            "plan_mejora": plan.name,
        })
        accion.flags.ignore_permissions = True
        accion.insert(ignore_permissions=True)
        return plan, accion

    # ======================================================================
    # index.py — portal público (guest), métricas vivas
    # ======================================================================
    def test_index_portal_puebla_metricas_publicas(self):
        """El portal público expone contadores vivos y el enlace a datos abiertos."""
        ctx = self._ctx()
        index.get_context(ctx)

        self.assertEqual(ctx.body_class, "sgc-portal")
        self.assertTrue(ctx.title)
        # El árbol sembrado garantiza pisos mínimos en los contadores globales.
        self.assertGreaterEqual(ctx.n_modelos, 1)          # al menos TEST-MARCO
        self.assertGreaterEqual(ctx.n_estandares, 3)       # los 3 Estandar de prueba
        self.assertGreaterEqual(ctx.n_criterios, 9)        # 3×3 Criterio de prueba
        # Los contadores son enteros (no None), aunque el doctype no tenga filas.
        self.assertIsInstance(ctx.n_indicadores, int)
        self.assertIsInstance(ctx.n_programas, int)
        self.assertEqual(ctx.datos_url, index.DATOS_ABIERTOS_URL)

    # ======================================================================
    # sgc.py — boot context de la SPA (autenticada)
    # ======================================================================
    def test_sgc_spa_inyecta_boot_context(self):
        """La SPA recibe csrf_token, usuario y el flag de System Manager."""
        ctx = self._ctx()
        sgc.get_context(ctx)

        self.assertIn("csrf_token", ctx.boot)
        self.assertTrue(ctx.boot["csrf_token"])
        self.assertEqual(ctx.boot["user"], "Administrator")
        self.assertIn("user_fullname", ctx.boot)
        # Administrator tiene el rol System Manager -> ve el acceso al Escritorio.
        self.assertTrue(ctx.boot["is_system_manager"])

    # ======================================================================
    # tablero.py — vista ejecutiva de la autoevaluación reciente
    # ======================================================================
    def test_tablero_puebla_ae_semaforo_y_contadores(self):
        """El tablero arma el semáforo NL/L/LP y los contadores coherentes."""
        e1, e2, e3 = self.estandares
        # E1 todos Cumple -> LP ; E2 un No cumple -> NL ; E3 un parcial -> L.
        factories.valorar_estandar(self.ae, self.criterios[e1], default=factories.CUMPLE)
        factories.valorar_estandar(self.ae, self.criterios[e2], juicios={0: factories.NO_CUMPLE})
        factories.valorar_estandar(self.ae, self.criterios[e3], juicios={0: factories.CUMPLE_PARCIAL})

        # Garantizar que ESTA autoevaluación sea la más reciente por 'modified'
        # (el tablero elige la primera por modified desc), aislándola de cualquier
        # AE pre-sembrada en el sitio. set_value directo no dispara el workflow.
        frappe.db.set_value("Autoevaluacion", self.ae, "titulo", "Tablero de prueba")

        ctx = self._ctx()
        tablero.get_context(ctx)

        self.assertIsNotNone(ctx.ae)
        self.assertEqual(ctx.ae["name"], self.ae)
        self.assertIsInstance(ctx.ae["avance"], int)

        # 3 Valoracion Estandar -> 3 tarjetas; ordenadas por código.
        self.assertEqual(ctx.total_estandares, 3)
        niveles = {e["name"]: e["nivel"] for e in ctx.estandares}
        self.assertEqual(niveles[e1], "LP")
        self.assertEqual(niveles[e2], "NL")
        self.assertEqual(niveles[e3], "L")

        # El semáforo agregado cuadra con los niveles propuestos.
        self.assertEqual(ctx.resumen, {"NL": 1, "L": 1, "LP": 1})

        # El color/meta de cada tarjeta corresponde a su nivel.
        for e in ctx.estandares:
            self.assertEqual(e["meta"], tablero.NIVEL_META[e["nivel"]])

        # 3 estándares × 3 criterios valorados = 9 Valoracion Criterio.
        self.assertEqual(ctx.n_criterios, 9)
        self.assertEqual(ctx.desk_url, "/app/autoevaluacion/" + self.ae)

    def test_tablero_estandar_sin_valorar_usa_fallback(self):
        """Un estándar sin nivel propuesto cae al meta 'Sin valorar' (fallback)."""
        e1 = self.estandares[0]
        # Crear una Valoracion Estandar sin nivel_propuesto (estándar no valorado).
        factories.crear_valoracion_estandar(self.ae, e1)
        frappe.db.set_value("Autoevaluacion", self.ae, "titulo", "Tablero fallback")

        ctx = self._ctx()
        tablero.get_context(ctx)

        tarjeta = next(e for e in ctx.estandares if e["name"] == e1)
        self.assertEqual(tarjeta["nivel"], "")
        self.assertEqual(tarjeta["meta"], tablero._FALLBACK)
        # No suma en ninguna categoría del semáforo.
        self.assertEqual(ctx.resumen, {"NL": 0, "L": 0, "LP": 0})

    def test_tablero_muestra_indicadores_publicados_por_un_conector(self):
        """El panel resuelve las mediciones por (programa_sede, periodo) de la AE.

        Es el caso real: el conector externo publica sin poblar `autoevaluacion`,
        así que una vista que filtre por ese Link no ve nada. Este test fija que
        el tablero SÍ las ve, y que advierte cuando hay más de una fuente.
        """
        ps = factories.crear_programa_sede().name
        periodo = factories.crear_periodo_academico().name
        ae = factories.crear_autoevaluacion(
            self.marco, programa_sede=ps, periodo_academico=periodo,
            titulo="Tablero con indicadores",
        ).name

        ind = factories.crear_indicador(codigo="TEST-WWW-ID10", nombre="Aprobados")
        factories.crear_valor_indicador(
            ind, ps, periodo, valor_num=88.22, fuente="dw",
            valor_texto="DW v1 · n=452 · meta 80% (cumple)",
        )
        # Segundo productor del MISMO par -> debe aparecer como advertencia.
        otro = factories.crear_indicador(codigo="TEST-WWW-ID6")
        factories.crear_valor_indicador(otro, ps, periodo, valor_num=-0.71, fuente="lamb")

        ctx = self._ctx()
        tablero.get_context(ctx)

        self.assertEqual(ctx.ae["name"], ae)
        self.assertEqual(ctx.indicadores_fuente, "dw")
        self.assertEqual([i["indicador"] for i in ctx.indicadores], ["TEST-WWW-ID10"])
        self.assertIs(ctx.indicadores[0]["cumple"], True)
        self.assertIsNone(ctx.indicadores_motivo)

        # La otra fuente se reporta para que la plantilla pueda advertirla.
        self.assertEqual(ctx.indicadores_otras_fuentes, [{"fuente": "lamb", "n_indicadores": 1}])

        # El contador cuenta indicadores distintos de TODAS las fuentes (2), no
        # los que tienen el Link `autoevaluacion` poblado (0, como antes).
        self.assertEqual(ctx.n_indicadores, 2)

    def test_tablero_sin_indicadores_expone_el_motivo(self):
        """Sin mediciones el panel queda vacío pero dice por qué."""
        frappe.db.set_value("Autoevaluacion", self.ae, "titulo", "Tablero sin indicadores")

        ctx = self._ctx()
        tablero.get_context(ctx)

        self.assertEqual(ctx.indicadores, [])
        # La AE base de setUp no tiene programa_sede -> el par no resuelve.
        self.assertEqual(ctx.indicadores_motivo, "autoevaluacion_sin_programa_sede")
        self.assertEqual(ctx.n_indicadores, 0)

    # ======================================================================
    # estandar.py — detalle de un estándar (?ae=&est=)
    # ======================================================================
    def test_estandar_detalle_puebla_criterios_y_nivel(self):
        """El detalle del estándar lista sus criterios y el nivel propuesto."""
        e1 = self.estandares[0]
        factories.valorar_estandar(self.ae, self.criterios[e1], default=factories.CUMPLE)

        ctx = self._ctx(ae=self.ae, est=e1)
        estandar.get_context(ctx)

        self.assertIsNotNone(ctx.estandar)
        self.assertEqual(ctx.estandar["codigo"], e1)      # código == name en el árbol
        self.assertEqual(ctx.ae_name, self.ae)
        # Todos Cumple -> nivel propuesto LP.
        self.assertEqual(ctx.nivel, "LP")
        self.assertEqual(ctx.nivel_meta, estandar.NIVEL_META["LP"])

        self.assertEqual(ctx.total, 3)
        self.assertEqual(ctx.resumen["Cumple"], 3)
        self.assertEqual(ctx.resumen["No cumple"], 0)
        for c in ctx.criterios:
            self.assertEqual(c["cumple"], "Cumple")
            self.assertEqual(c["meta"], estandar.CUMPLE_META["Cumple"])

    def test_estandar_sin_parametro_est_devuelve_none(self):
        """Sin `est` (o inexistente) el contexto queda con estandar=None."""
        ctx = self._ctx(ae=self.ae)   # falta 'est'
        estandar.get_context(ctx)
        self.assertIsNone(ctx.estandar)

        ctx2 = self._ctx(ae=self.ae, est="NO-EXISTE")
        estandar.get_context(ctx2)
        self.assertIsNone(ctx2.estandar)

    # ======================================================================
    # criterio.py — detalle de un criterio (?ae=&crit=)
    # ======================================================================
    def test_criterio_detalle_puebla_valoracion_hallazgos_evidencias(self):
        """El detalle del criterio trae su valoración, hallazgos y evidencias."""
        e1 = self.estandares[0]
        crit = self.criterios[e1][0]
        factories.valorar_criterio(self.ae, crit, factories.CUMPLE)

        # Evidencia anclada al criterio por su origen (Elemento Marco).
        evd = factories.crear_evidencia(
            codigo="TEST-EVD-CRIT",
            origen_doctype="Elemento Marco",
            origen_id=crit,
        )
        # Un hallazgo vinculado al par (autoevaluacion, criterio).
        self._crear_hallazgo(crit, "TEST-HALL-CRIT")

        ctx = self._ctx(ae=self.ae, crit=crit)
        criterio.get_context(ctx)

        self.assertIsNotNone(ctx.criterio)
        self.assertEqual(ctx.criterio["codigo"], crit)
        self.assertEqual(ctx.ae_name, self.ae)
        # El padre del criterio es su estándar E1.
        self.assertEqual(ctx.estandar_name, e1)

        self.assertEqual(ctx.valoracion["cumple"], "Cumple")
        self.assertEqual(ctx.valoracion["meta"], criterio.CUMPLE_META["Cumple"])

        # 1 hallazgo, con su meta de color de estado calculada.
        self.assertEqual(len(ctx.hallazgos), 1)
        self.assertIn("estado_meta", ctx.hallazgos[0])

        # La evidencia sembrada aparece entre las trazadas al criterio.
        codigos_evid = [e["codigo"] for e in ctx.evidencias]
        self.assertIn(evd.name, codigos_evid)

    def test_criterio_inexistente_devuelve_none(self):
        """Un `crit` que no existe deja criterio=None sin lanzar excepción."""
        ctx = self._ctx(ae=self.ae, crit="NO-EXISTE")
        criterio.get_context(ctx)
        self.assertIsNone(ctx.criterio)

    # ======================================================================
    # mejora.py — ciclo CAPA (?ae=)
    # ======================================================================
    def test_mejora_capa_puebla_hallazgos_planes_y_acciones(self):
        """La página CAPA arma hallazgos, planes y sus acciones, con contadores."""
        e1 = self.estandares[0]
        crit = self.criterios[e1][0]
        self._crear_hallazgo(crit, "TEST-HALL-MEJ")
        self._crear_plan_con_accion("TEST-PLAN-MEJ", "TEST-ACC-MEJ", avance=50)

        ctx = self._ctx(ae=self.ae)
        mejora.get_context(ctx)

        self.assertEqual(ctx.ae_name, self.ae)
        # Hallazgos y planes están filtrados por la autoevaluación reciente.
        self.assertEqual(ctx.n_hallazgos, 1)
        self.assertEqual(ctx.n_planes, 1)
        self.assertEqual(ctx.n_acciones, 1)

        # La acción refleja su avance manual (estado 'En ejecucion' respeta el %).
        acc = ctx.planes[0]["acciones"][0]
        self.assertEqual(acc["avance"], 50)
        self.assertIn("estado_meta", acc)

        # El hallazgo trae meta de estado y de severidad.
        self.assertIn("estado_meta", ctx.hallazgos[0])
        self.assertIn("sev_meta", ctx.hallazgos[0])

        # No Conformidad se cuenta global (sin filtro de ae): solo debe ser entero.
        self.assertIsInstance(ctx.n_nc, int)

    # ======================================================================
    # api.py — catálogo de la escala NL/L/LP
    # ======================================================================
    def test_api_get_niveles_escala_devuelve_niveles_en_orden(self):
        """get_niveles_escala trae sigla/etiqueta y respeta el orden ascendente."""
        factories.crear_escala_niveles()  # asegura los 3 Nivel Escala NL/L/LP

        res = api.get_niveles_escala()
        self.assertIsInstance(res, list)
        self.assertGreaterEqual(len(res), 3)

        siglas = {r["sigla"] for r in res}
        self.assertTrue({"NL", "L", "LP"}.issubset(siglas))

        # Devuelve los campos legibles (no solo el name): sigla y etiqueta.
        for r in res:
            self.assertIn("sigla", r)
            self.assertIn("etiqueta", r)

        # Ordenado por 'orden' asc: NL (0) antes que L (1) antes que LP (2).
        rango = {"NL": 0, "L": 1, "LP": 2}
        secuencia = [rango[r["sigla"]] for r in res if r["sigla"] in rango]
        self.assertEqual(secuencia, sorted(secuencia))

    def test_api_acceso_m365_existe(self):
        """El endpoint SSO existe y es invocable (el redirect no se ejercita a fondo)."""
        self.assertTrue(callable(api.acceso_m365))
        # Está registrado como método whitelisted de Frappe (redirect SSO).
        self.assertIn(api.acceso_m365, frappe.whitelisted)
        self.assertEqual(
            inspect.signature(api.acceso_m365).parameters["redirect_to"].default,
            "/sgc/",
        )
