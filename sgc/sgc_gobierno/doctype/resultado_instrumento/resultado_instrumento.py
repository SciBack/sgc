# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""M12 — Resultado de Instrumento + tabulación.

Captura un resultado tabulado de una `Aplicacion Instrumento`: por dimensión
(p. ej. "Trato del personal", "Infraestructura"), su `valor` (media Likert, %,
etc.), la `unidad`, el `n` (respuestas que sustentan ese valor) y la
`fecha_corte`. Opcionalmente materializa un `Valor Indicador` fechado que el
motor de indicadores lee (A2).

El DocType no tiene campo `estado` de flujo → NO lleva Workflow.

`tabular_aplicacion` es el método whitelisted de agregación que consume un
tablero: promedio simple, promedio ponderado por `n` y desglose por dimensión.
"""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate


class ResultadoInstrumento(Document):
    def validate(self):
        if self.dimension:
            self.dimension = self.dimension.strip()

        # El n (tamaño que sustenta el valor) no puede ser negativo.
        if self.n is not None and self.n < 0:
            frappe.throw(_("El n (número de respuestas) no puede ser negativo."))

        # Si la unidad es un porcentaje, el valor debe estar en [0, 100].
        if self.unidad and "%" in self.unidad and self.valor is not None:
            if self.valor < 0 or self.valor > 100:
                frappe.throw(
                    _("Un valor en porcentaje debe estar entre 0 y 100 (recibido {0}).").format(
                        self.valor
                    )
                )

        # Fecha de corte por defecto: el fin del campo de la aplicación, o hoy.
        if not self.fecha_corte and self.aplicacion_instrumento:
            fin = frappe.db.get_value(
                "Aplicacion Instrumento", self.aplicacion_instrumento, "fecha_fin"
            )
            self.fecha_corte = fin or nowdate()


# ===========================================================================
# Tabulación / agregación (consumo de tablero)
# ===========================================================================

@frappe.whitelist()
def tabular_aplicacion(aplicacion):
    """Agrega los Resultado Instrumento de una aplicación para un tablero.

    Devuelve, sobre todas las filas de resultado de la aplicación:
      - `n_resultados`: cuántas filas de resultado hay.
      - `n_total`: suma de los `n` (respuestas totales que sustentan los valores).
      - `promedio`: media simple de los `valor`.
      - `promedio_ponderado`: media de los `valor` ponderada por `n`.
      - `dimensiones`: desglose por dimensión con su promedio (simple y
        ponderado), su `n` y el porcentaje de la muestra que representa.

    Whitelisted: respeta permisos del DocType al leer.
    """
    if not aplicacion:
        frappe.throw(_("Falta la aplicación de instrumento a tabular."))
    if not frappe.db.exists("Aplicacion Instrumento", aplicacion):
        frappe.throw(_("La aplicación de instrumento {0} no existe.").format(aplicacion))

    filas = frappe.get_all(
        "Resultado Instrumento",
        filters={"aplicacion_instrumento": aplicacion},
        fields=["dimension", "valor", "unidad", "n", "fecha_corte"],
        order_by="dimension asc",
    )

    n_resultados = len(filas)

    # --- Agregación global ---
    valores = [f.valor for f in filas if f.valor is not None]
    promedio = round(sum(valores) / len(valores), 4) if valores else None

    n_total = sum((f.n or 0) for f in filas)
    suma_pond = sum((f.valor or 0) * (f.n or 0) for f in filas)
    promedio_ponderado = round(suma_pond / n_total, 4) if n_total else None

    # --- Desglose por dimensión ---
    acum = {}
    for f in filas:
        dim = f.dimension or _("(sin dimensión)")
        d = acum.setdefault(
            dim,
            {"dimension": dim, "n_resultados": 0, "valores": [],
             "n": 0, "suma_pond": 0.0, "unidad": f.unidad},
        )
        d["n_resultados"] += 1
        if f.valor is not None:
            d["valores"].append(f.valor)
        d["n"] += (f.n or 0)
        d["suma_pond"] += (f.valor or 0) * (f.n or 0)
        # Conserva la primera unidad no vacía vista para la dimensión.
        if not d["unidad"] and f.unidad:
            d["unidad"] = f.unidad

    dimensiones = []
    for dim, d in acum.items():
        prom = round(sum(d["valores"]) / len(d["valores"]), 4) if d["valores"] else None
        prom_pond = round(d["suma_pond"] / d["n"], 4) if d["n"] else None
        pct_muestra = round(d["n"] * 100.0 / n_total, 2) if n_total else None
        dimensiones.append({
            "dimension": dim,
            "unidad": d["unidad"] or "",
            "n_resultados": d["n_resultados"],
            "n": d["n"],
            "promedio": prom,
            "promedio_ponderado": prom_pond,
            "pct_muestra": pct_muestra,
        })

    # Orden estable por dimensión para el tablero.
    dimensiones.sort(key=lambda x: x["dimension"])

    return {
        "aplicacion": aplicacion,
        "n_resultados": n_resultados,
        "n_total": n_total,
        "promedio": promedio,
        "promedio_ponderado": promedio_ponderado,
        "dimensiones": dimensiones,
    }
