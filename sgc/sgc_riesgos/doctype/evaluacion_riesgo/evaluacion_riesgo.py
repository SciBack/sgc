# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Evaluación de un riesgo — análisis y valoración (ISO 31000 §6.4.3/§6.4.4).

Recorrido del flujo 13 en producción (2026-08-23): el `score` y el `nivel` los
declaraba el diseño como "calculado en F4 (Server Script)" y ese script NUNCA
existió. Los dos campos son `read_only`, así que nadie podía siquiera corregirlos
a mano: toda evaluación nacía con `score = 0` y —por ser `nivel` un Select sin
valor, que Frappe rellena con su primera opción— con `nivel = "Bajo"`. Se
comprobó insertando una evaluación con probabilidad 1 e impacto 1: score 0,
nivel «Bajo». Con probabilidad 5 e impacto 5 habría dado exactamente lo mismo.

Un inventario de riesgos en el que TODO sale «Bajo» no es un inventario: es una
declaración falsa de que la organización no tiene riesgos relevantes, justo lo
contrario de lo que ISO 9001:2015 §6.1 pide determinar. El cálculo vive ahora en
el controlador, que es donde el resto del SGC pone los suyos.
"""
import json

import frappe
from frappe import _
from frappe.model.document import Document

# Niveles del Select `nivel`, de menor a mayor. El orden importa: es el que se
# usa para repartir el rango de score cuando la matriz no declara umbrales.
NIVELES = ("Bajo", "Moderado", "Alto", "Extremo")

# Claves aceptadas al leer `Matriz Riesgo.umbrales`. La forma canónica es
# [{"min": 1, "max": 4, "nivel": "Bajo"}, ...]; se toleran sinónimos porque el
# campo es JSON libre y lo rellena a mano quien configura la escala.
_K_MIN = ("min", "desde", "minimo", "from")
_K_MAX = ("max", "hasta", "maximo", "to")
_K_NIVEL = ("nivel", "label", "etiqueta", "nombre")


class EvaluacionRiesgo(Document):
    def validate(self):
        self._validar_valores()
        self._calcular()
        self._sellar_evaluador()

    # ------------------------------------------------------------------ pasos
    def _validar_valores(self):
        """Sin probabilidad e impacto no hay análisis, solo un formulario vacío.

        ISO 31000 §6.4.3 define el análisis como la comprensión de la
        probabilidad y de las consecuencias. Guardar la evaluación sin ellas
        producía un registro que decía "este riesgo se evaluó" y no contenía
        ninguna valoración.
        """
        if not (self.probabilidad or 0) or not (self.impacto or 0):
            frappe.throw(
                _("Indique la probabilidad y el impacto: son el análisis del riesgo "
                  "(ISO 31000 §6.4.3), no un dato opcional."),
                title=_("Evaluación sin valores"),
            )

    def _calcular(self):
        """`score` = probabilidad x impacto; `nivel`, derivado de la escala.

        La escala la fija la `Matriz Riesgo` que el riesgo declara usar. Se
        prefieren sus `umbrales` explícitos; si no los tiene (o no se pueden
        leer), se reparte el rango en cuatro tramos iguales sobre el score máximo
        de la matriz. Si el riesgo no declara matriz, el nivel queda EN BLANCO:
        sin criterios de riesgo no hay valoración posible (ISO 31000 §6.4.4
        compara el análisis contra criterios), y mentir con un «Bajo» es
        exactamente el fallo que este controlador viene a corregir.
        """
        self.score = int(self.probabilidad or 0) * int(self.impacto or 0)
        self.nivel = self._derivar_nivel(self.score)

    def _sellar_evaluador(self):
        """Evaluar ES el acto: lo registra quien lo ejecuta.

        `evaluado_por` era un Link tecleable. Comprobado en el recorrido del
        2026-08-23: el dueño del proceso insertó una evaluación de su propio
        riesgo atribuyéndosela a la DPGC, y el registro quedó diciendo que la
        valoró alguien que no la miró. Mismo arreglo que
        `No Conformidad.verificada_por` y `Programa Auditoria.aprobado_por`.

        Se sella al crear y cada vez que cambian los valores evaluados: una
        reevaluación es otro acto y la firma tiene que ser la de quien la hace.
        """
        anterior = self.get_doc_before_save()
        cambio = anterior is None or (
            anterior.probabilidad != self.probabilidad or anterior.impacto != self.impacto
        )
        if cambio:
            self.evaluado_por = frappe.session.user

    # ---------------------------------------------------------------- helpers
    def _derivar_nivel(self, score):
        matriz = frappe.db.get_value("Riesgo", self.riesgo, "matriz_riesgo") if self.riesgo else None
        if not matriz:
            return None

        m = frappe.db.get_value(
            "Matriz Riesgo", matriz,
            ["umbrales", "dimension", "niveles_probabilidad", "niveles_impacto"],
            as_dict=True,
        ) or {}

        por_umbral = _nivel_por_umbrales(score, m.get("umbrales"))
        if por_umbral:
            return por_umbral

        tope = _score_maximo(m)
        if not tope:
            return None
        return _nivel_proporcional(score, tope)


# ---------------------------------------------------------------------------
# Lectura de la escala. Todo aquí es defensivo a propósito: `umbrales`,
# `niveles_probabilidad` y `niveles_impacto` son campos JSON libres y una escala
# mal escrita no puede tumbar el guardado de una evaluación — como mucho deja el
# nivel en blanco, que es honesto.
# ---------------------------------------------------------------------------
def _cargar(valor):
    if isinstance(valor, (list, dict)):
        return valor
    if not valor:
        return None
    try:
        return json.loads(valor)
    except (ValueError, TypeError):
        return None


def _primera(d, claves):
    for k in claves:
        if k in d:
            return d[k]
    return None


def _nivel_por_umbrales(score, umbrales):
    """Busca el tramo que contiene `score` en [{"min","max","nivel"}, ...]."""
    tramos = _cargar(umbrales)
    if not isinstance(tramos, list):
        return None
    for t in tramos:
        if not isinstance(t, dict):
            continue
        nivel = _primera(t, _K_NIVEL)
        if nivel not in NIVELES:
            continue
        try:
            minimo = int(_primera(t, _K_MIN))
            maximo = int(_primera(t, _K_MAX))
        except (TypeError, ValueError):
            continue
        if minimo <= score <= maximo:
            return nivel
    return None


def _score_maximo(matriz):
    """Score máximo de la escala: dimensión² o el mayor valor de cada eje."""
    dim = matriz.get("dimension") or 0
    if dim:
        return int(dim) ** 2

    def tope_eje(campo):
        niveles = _cargar(matriz.get(campo))
        if not isinstance(niveles, list):
            return 0
        valores = []
        for n in niveles:
            valor = n.get("valor") if isinstance(n, dict) else n
            try:
                valores.append(int(valor))
            except (TypeError, ValueError):
                continue
        return max(valores) if valores else 0

    return tope_eje("niveles_probabilidad") * tope_eje("niveles_impacto")


def _nivel_proporcional(score, tope):
    """Reparte [1..tope] en cuatro tramos iguales: Bajo/Moderado/Alto/Extremo."""
    if score <= 0:
        return NIVELES[0]
    fraccion = min(score / float(tope), 1.0)
    for i, corte in enumerate((0.25, 0.5, 0.75)):
        if fraccion <= corte:
            return NIVELES[i]
    return NIVELES[3]
