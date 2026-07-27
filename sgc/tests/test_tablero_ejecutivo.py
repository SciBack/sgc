# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests de `sgc.tablero_ejecutivo` — M13, vista institucional de acreditación.

Verifica que `resumen_ejecutivo`:
- Devuelve la estructura esperada (cobertura, programas, niveles, cbc, mejora,
  riesgos, auditoria, revision_direccion).
- Cuenta la cobertura contra el total de Programa Sede.
- Clasifica los estándares por nivel: usa el OFICIAL cuando está confirmado y el
  propuesto por el motor cuando no; lo no valorado cae en `sin_valorar`.
- GRC: resuelve el nivel del riesgo por su `Evaluacion Riesgo` (residual antes que
  inherente, `sin_evaluar` si no hay ninguna), cuenta auditorías/hallazgos (con
  filtro opcional por periodo) y localiza la última revisión por la dirección.

Los riesgos/auditorías/revisiones se crean con helpers PRIVADOS de este módulo
(`factories.py` es archivo compartido y no se toca en esta etapa). Los conteos se
verifican SIEMPRE por delta: producción ya tiene datos y la base no es 0.
"""

import itertools

import frappe
from frappe.tests import IntegrationTestCase

from sgc.tablero_ejecutivo import resumen_ejecutivo
from sgc.tests import factories

# Contador para códigos únicos dentro de la transacción del test.
_seq = itertools.count(1)


def _insertar(doctype, valores):
    doc = frappe.get_doc({"doctype": doctype, **valores})
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    return doc


def _riesgo(titulo=None, estado="Identificado", **extra):
    """Riesgo en su estado inicial. Para moverlo se usa `frappe.db.set_value`
    (hay Workflow "Riesgo SGC" sobre `estado`: `.save()` no es el camino)."""
    doc = _insertar("Riesgo", {"titulo": titulo or f"Riesgo de prueba {next(_seq)}", **extra})
    if estado != "Identificado":
        frappe.db.set_value("Riesgo", doc.name, "estado", estado)
    return doc


def _evaluacion(riesgo, momento="Residual", nivel="Alto", fecha="2026-01-01", **extra):
    return _insertar("Evaluacion Riesgo", {
        "riesgo": riesgo.name if hasattr(riesgo, "name") else riesgo,
        "momento": momento,
        "nivel": nivel,
        "fecha": fecha,
        **extra,
    })


def _periodo(codigo=None):
    codigo = codigo or "TEST-EJEC-PER"
    if frappe.db.exists("Periodo Academico", codigo):
        return codigo
    _insertar("Periodo Academico", {"codigo": codigo, "anio": 2026, "semestre": "I"})
    return codigo


def _auditoria(estado="Planificada", **extra):
    """Auditoria SIEMPRE creada en 'Planificada': su validate() exige equipo,
    criterios e independencia a partir de 'En ejecucion'. El estado se mueve
    después con `frappe.db.set_value`, sin pasar por el workflow."""
    doc = _insertar("Auditoria", {"titulo": f"Auditoria de prueba {next(_seq)}", **extra})
    if estado != "Planificada":
        frappe.db.set_value("Auditoria", doc.name, "estado", estado)
    return doc


def _hallazgo(auditoria, tipo="Observacion", estado="Abierto", **extra):
    return _insertar("Hallazgo Auditoria", {
        "auditoria": auditoria.name if hasattr(auditoria, "name") else auditoria,
        "tipo": tipo,
        "estado": estado,
        **extra,
    })


def _revision(fecha="2099-01-01", estado="Planificada", **extra):
    """Revisión por la dirección. `fecha` futura por defecto para que quede como
    'la última' aunque producción ya tenga revisiones reales."""
    n = next(_seq)
    return _insertar("Revision Direccion", {
        "codigo": f"TEST-RPD-{n}",
        "titulo": f"Revision de prueba {n}",
        "fecha": fecha,
        "estado": estado,
        **extra,
    })


class IntegrationTestTableroEjecutivo(IntegrationTestCase):
    def test_estructura(self):
        """El payload trae las 8 secciones y los conteos son enteros."""
        r = resumen_ejecutivo()
        self.assertEqual(
            set(r.keys()),
            {
                "cobertura", "programas", "niveles", "cbc", "mejora",
                "riesgos", "auditoria", "revision_direccion",
            },
        )
        self.assertIsInstance(r["programas"], list)
        for clave in ("NL", "L", "LP", "sin_valorar"):
            self.assertIsInstance(r["niveles"][clave], int)
        self.assertIsInstance(r["cobertura"]["programas_total"], int)
        self.assertIsInstance(r["mejora"]["nc_abiertas"], int)

    def test_cobertura_cuenta_autoevaluaciones_vivas(self):
        """Crear una autoevaluación viva incrementa la cobertura."""
        base = resumen_ejecutivo()["cobertura"]["con_autoevaluacion"]
        arbol = factories.crear_marco_prueba(n_estandares=2, n_criterios=1, prefijo="TEST-EJEC")
        factories.crear_autoevaluacion(arbol, prefijo="TEST-EJEC")
        self.assertEqual(resumen_ejecutivo()["cobertura"]["con_autoevaluacion"], base + 1)

    def test_nivel_propuesto_se_clasifica(self):
        """Un estándar con nivel propuesto (sin confirmar) cuenta en su sigla."""
        arbol = factories.crear_marco_prueba(n_estandares=1, n_criterios=2, prefijo="TEST-EJEC2")
        ae = factories.crear_autoevaluacion(arbol, prefijo="TEST-EJEC2")
        est = arbol["estandares"][0]
        # Valorar ambos criterios como Cumple -> el motor propone LP.
        factories.valorar_estandar(ae, arbol["criterios"][est], default=factories.CUMPLE)

        info = next(p for p in resumen_ejecutivo()["programas"] if p["name"] == ae.name)
        self.assertEqual(info["estandares_total"], 1)
        self.assertEqual(info["niveles"]["LP"], 1)

    def test_nivel_oficial_confirmado_prevalece(self):
        """Con el nivel oficial confirmado, se clasifica por ese (no por el propuesto)."""
        arbol = factories.crear_marco_prueba(n_estandares=1, n_criterios=2, prefijo="TEST-EJEC3")
        ae = factories.crear_autoevaluacion(arbol, prefijo="TEST-EJEC3")
        est = arbol["estandares"][0]
        factories.valorar_estandar(ae, arbol["criterios"][est], default=factories.CUMPLE)  # propone LP
        factories.confirmar_estandar(ae, est, "L", prefijo="TEST-EJEC3")  # oficial: L

        info = next(p for p in resumen_ejecutivo()["programas"] if p["name"] == ae.name)
        self.assertEqual(info["niveles"]["L"], 1)
        self.assertEqual(info["niveles"]["LP"], 0)

    # ----------------------------------------------------------------- riesgos
    def test_riesgo_sin_evaluacion_cae_en_sin_evaluar(self):
        """Un riesgo abierto sin ninguna Evaluacion Riesgo NO se adivina."""
        base = resumen_ejecutivo()["riesgos"]
        _riesgo()
        r = resumen_ejecutivo()["riesgos"]
        self.assertEqual(r["por_nivel"]["sin_evaluar"], base["por_nivel"]["sin_evaluar"] + 1)
        self.assertEqual(r["abiertos"], base["abiertos"] + 1)
        self.assertEqual(r["criticos"], base["criticos"])

    def test_nivel_residual_prevalece_sobre_inherente(self):
        """Se reporta el residual (ISO 31000), aunque el inherente sea más reciente."""
        base = resumen_ejecutivo()["riesgos"]["por_nivel"]
        rk = _riesgo()
        _evaluacion(rk, momento="Inherente", nivel="Extremo", fecha="2026-06-01")
        _evaluacion(rk, momento="Residual", nivel="Moderado", fecha="2026-01-01")

        por_nivel = resumen_ejecutivo()["riesgos"]["por_nivel"]
        self.assertEqual(por_nivel["Moderado"], base["Moderado"] + 1)
        self.assertEqual(por_nivel["Extremo"], base["Extremo"])

    def test_residual_mas_reciente_gana_y_cuenta_como_critico(self):
        """Entre dos residuales manda el de fecha mayor; Alto/Extremo son críticos."""
        base = resumen_ejecutivo()["riesgos"]
        rk = _riesgo()
        _evaluacion(rk, momento="Residual", nivel="Bajo", fecha="2026-01-01")
        _evaluacion(rk, momento="Residual", nivel="Extremo", fecha="2026-09-01")

        r = resumen_ejecutivo()["riesgos"]
        self.assertEqual(r["por_nivel"]["Extremo"], base["por_nivel"]["Extremo"] + 1)
        self.assertEqual(r["por_nivel"]["Bajo"], base["por_nivel"]["Bajo"])
        self.assertEqual(r["criticos"], base["criticos"] + 1)

    def test_riesgo_cerrado_no_cuenta_como_abierto(self):
        """'Cerrado' sale de los abiertos; 'Materializado' sigue vivo y se expone aparte."""
        base = resumen_ejecutivo()["riesgos"]
        cerrado = _riesgo(estado="Cerrado")
        _evaluacion(cerrado, nivel="Extremo")
        _riesgo(estado="Materializado")

        r = resumen_ejecutivo()["riesgos"]
        self.assertEqual(r["abiertos"], base["abiertos"] + 1)  # solo el materializado
        self.assertEqual(r["criticos"], base["criticos"])
        self.assertEqual(r["materializados"], base["materializados"] + 1)
        self.assertEqual(r["por_estado"]["Cerrado"], base["por_estado"]["Cerrado"] + 1)

    # --------------------------------------------------------------- auditoría
    def test_auditoria_y_hallazgos_se_cuentan(self):
        """Auditoría por estado y hallazgos por tipo/estado, con los abiertos aparte."""
        base = resumen_ejecutivo()["auditoria"]
        aud = _auditoria()
        _hallazgo(aud, tipo="No conformidad menor", estado="Abierto")
        _hallazgo(aud, tipo="Fortaleza", estado="Cerrado")

        a = resumen_ejecutivo()["auditoria"]
        self.assertEqual(a["total"], base["total"] + 1)
        self.assertEqual(a["por_estado"]["Planificada"], base["por_estado"]["Planificada"] + 1)
        self.assertEqual(a["hallazgos"]["total"], base["hallazgos"]["total"] + 2)
        self.assertEqual(a["hallazgos"]["abiertos"], base["hallazgos"]["abiertos"] + 1)
        self.assertEqual(
            a["hallazgos"]["por_tipo"]["No conformidad menor"],
            base["hallazgos"]["por_tipo"]["No conformidad menor"] + 1,
        )

    def test_filtro_por_periodo_acota_auditorias_y_hallazgos(self):
        """Con `periodo_academico` solo entran esas auditorías y SUS hallazgos.

        El hallazgo no tiene periodo propio: se deriva por su Link `auditoria`.
        """
        periodo = _periodo()
        con_periodo = _auditoria(periodo_academico=periodo)
        _hallazgo(con_periodo, tipo="Observacion")
        sin_periodo = _auditoria()
        _hallazgo(sin_periodo, tipo="Observacion")

        a = resumen_ejecutivo(periodo_academico=periodo)["auditoria"]
        self.assertEqual(a["periodo_academico"], periodo)
        self.assertEqual(a["total"], 1)
        self.assertEqual(a["hallazgos"]["total"], 1)

    # ------------------------------------------------- revisión por la dirección
    def test_ultima_revision_direccion(self):
        """La sección trae el conteo por estado y la revisión de fecha más alta."""
        base = resumen_ejecutivo()["revision_direccion"]
        _revision(fecha="2098-01-01")
        rev = _revision(fecha="2099-06-30")

        r = resumen_ejecutivo()["revision_direccion"]
        self.assertEqual(r["total"], base["total"] + 2)
        self.assertEqual(r["por_estado"]["Planificada"], base["por_estado"]["Planificada"] + 2)
        self.assertEqual(r["ultima"]["name"], rev.name)
        self.assertEqual(r["ultima"]["estado"], "Planificada")
