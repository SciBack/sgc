# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Los indicadores medidos, legibles y de UNA sola fuente.

La lista de `Valor Indicador` muestra las tres fuentes mezcladas y el texto en bruto del
productor (`DW v1-norma Coneau 2026 · n=12 · meta >= 20% (cumple)`). Quien la abre ve dos
cifras distintas del mismo indicador —`dw` y `lamb` aplican reglas de cálculo distintas— y
tiene que descifrar el texto a ojo. Este informe hace lo que hacía el panel que se perdió al
retirar la SPA: muestra un solo productor y separa el texto en columnas.

Dos cosas que no son obvias y que este informe respeta:

1. **`valor_num` es el valor del indicador; el `n=` del texto es el tamaño de la muestra.**
   25 % de 12 docentes: el valor es 25, la n es 12. Confundirlos da un informe que miente.
2. **El cumplimiento se lee, no se deduce.** El juicio lo emite el productor contra su marco
   normativo, y el mismo valor puede cumplir un marco e incumplir otro. Aquí no se recalcula
   comparando valor con meta: se muestra lo que el productor declaró.

Las otras fuentes no se ocultan: se cuentan en el mensaje de cabecera, para que nadie crea
que lo que ve es todo lo que hay.
"""

import frappe
from frappe import _

# Se importa el parser del motor de indicadores en vez de repetir aquí la lectura del
# contrato: si el productor cambia el formato, hay un solo sitio que corregir.
from sgc.indicadores_acreditacion import (
	_nombres_de_indicador,
	_orden_codigo,
	_parsear_valor_texto,
	fuente_preferida,
)

CAMPOS = [
	"name",
	"indicador",
	"programa_sede",
	"periodo_academico",
	"unidad_organica",
	"valor_num",
	"valor_texto",
	"fuente",
	"fecha",
]


def execute(filters=None):
	filters = frappe._dict(filters or {})
	fuente = (filters.get("fuente") or "").strip() or fuente_preferida()

	condiciones = {"fuente": fuente}
	for campo in ("periodo_academico", "programa_sede", "indicador"):
		if filters.get(campo):
			condiciones[campo] = filters.get(campo)

	registros = frappe.get_all("Valor Indicador", filters=condiciones, fields=CAMPOS, limit_page_length=0)
	nombres = _nombres_de_indicador({r.indicador for r in registros})

	filas = []
	for r in registros:
		leido = _parsear_valor_texto(r.valor_texto or "")
		cumple = leido.get("cumple")
		if filters.get("solo_incumplidos") and cumple is not False:
			continue
		filas.append(
			{
				"indicador": r.indicador,
				"nombre": nombres.get(r.indicador, ""),
				"programa_sede": r.programa_sede,
				"periodo_academico": r.periodo_academico,
				"valor": r.valor_num,
				"meta": leido.get("meta_texto") or "",
				# Tres estados, no dos: que el productor no se pronuncie no es un "No".
				"cumple": {True: _("Sí"), False: _("No")}.get(cumple, "—"),
				"muestra": leido.get("n"),
				"marco": leido.get("marco") or "",
				"provisional": 1 if leido.get("provisional") else 0,
				"fuente": r.fuente,
			}
		)

	filas.sort(key=lambda f: (_orden_codigo(f["indicador"]), f["programa_sede"] or ""))

	return (
		_columnas(),
		filas,
		_aviso_de_otras_fuentes(fuente, condiciones),
		None,
		_resumen(filas),
		# Sumar porcentajes de programas distintos daría una cifra que no existe.
		True,
	)


def _columnas():
	return [
		{"label": _("Indicador"), "fieldname": "indicador", "fieldtype": "Link", "options": "Indicador", "width": 120},
		{"label": _("Nombre"), "fieldname": "nombre", "fieldtype": "Data", "width": 300},
		{
			"label": _("Programa / Sede"),
			"fieldname": "programa_sede",
			"fieldtype": "Link",
			"options": "Programa Sede",
			"width": 140,
		},
		{
			"label": _("Periodo"),
			"fieldname": "periodo_academico",
			"fieldtype": "Link",
			"options": "Periodo Academico",
			"width": 90,
		},
		{"label": _("Valor"), "fieldname": "valor", "fieldtype": "Float", "precision": 2, "width": 90},
		{"label": _("Meta"), "fieldname": "meta", "fieldtype": "Data", "width": 110},
		{"label": _("¿Cumple?"), "fieldname": "cumple", "fieldtype": "Data", "width": 90},
		# El tamaño de la muestra: 25 % de 12 no dice lo mismo que 25 % de 400.
		{"label": _("Muestra (n)"), "fieldname": "muestra", "fieldtype": "Float", "precision": 0, "width": 100},
		{"label": _("Marco"), "fieldname": "marco", "fieldtype": "Data", "width": 170},
		{"label": _("Provisional"), "fieldname": "provisional", "fieldtype": "Check", "width": 90},
		{"label": _("Fuente"), "fieldname": "fuente", "fieldtype": "Data", "width": 80},
	]


def _aviso_de_otras_fuentes(fuente, condiciones):
	"""Dice cuántas mediciones quedan fuera, para que nadie lea esto como el total."""
	otras = {}
	filtro = {k: v for k, v in condiciones.items() if k != "fuente"}
	for v in frappe.get_all("Valor Indicador", filters=filtro, fields=["fuente"], limit_page_length=0):
		nombre = (v.fuente or "").strip() or _("(sin fuente)")
		if nombre != fuente:
			otras[nombre] = otras.get(nombre, 0) + 1
	if not otras:
		return None
	detalle = ", ".join(f"<b>{n}</b>: {c}" for n, c in sorted(otras.items()))
	return _(
		"Se muestra únicamente la fuente <b>{0}</b>. Hay {1} medición(es) de otros productores que"
		" no se muestran ({2}). No se mezclan: cada productor aplica sus propias reglas de cálculo,"
		" así que sumarlos daría una cifra que no existe en ninguno."
	).format(fuente, sum(otras.values()), detalle)


def _resumen(filas):
	total = len(filas)
	cumplen = sum(1 for f in filas if f["cumple"] == _("Sí"))
	sin_juicio = sum(1 for f in filas if f["cumple"] == "—")
	return [
		{"label": _("Mediciones"), "value": total, "datatype": "Int"},
		{"label": _("Indicadores distintos"), "value": len({f["indicador"] for f in filas}), "datatype": "Int"},
		{
			"label": _("Cumplen"),
			"value": cumplen,
			"datatype": "Int",
			"indicator": "Green" if cumplen else "Grey",
		},
		{
			"label": _("No cumplen"),
			"value": total - cumplen - sin_juicio,
			"datatype": "Int",
			"indicator": "Red" if (total - cumplen - sin_juicio) else "Grey",
		},
	]
