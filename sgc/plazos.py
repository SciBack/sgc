"""Estado del plazo: si un registro se cerró en plazo, y cuánto se retrasó.

Hasta la 1.7.15, «vencido» solo existía calculado al vuelo (`dashboards.py`,
`reportes.dias_de_retraso`). Al cerrar el registro, ese dato desaparecía: la NC
sellaba quién la verificó pero no cuándo se cerró, y no había forma de medir
«% de no conformidades cerradas en plazo», que es la pregunta que hace la revisión
por la dirección sobre la eficacia de las acciones (ISO 9001 §9.3.2 c, §10.2).

Aquí se guarda, en tres campos de solo lectura que pone el sistema:

- `fecha_cierre`: el día en que el registro entró en un estado de cierre.
- `estado_plazo`: *Sin plazo, En plazo, Por vencer, Vencido, Cerrado en plazo* o
  *Cerrado fuera de plazo*.
- `dias_retraso`: días pasados de la fecha de compromiso; hasta hoy si sigue abierto,
  hasta el cierre si ya se cerró.

Son campos guardados y no virtuales a propósito: un campo virtual no se puede
filtrar ni contar (`frappe/model/meta.py:271`). El patrón viene de Frappe Helpdesk
(`agreement_status` del SLA).

Cada controlador llama a `aplicar(self)` en su `validate`. Lo que solo cambia con el
paso del tiempo (En plazo → Por vencer → Vencido) lo refresca `recalcular_abiertos`
una vez al día.
"""

import frappe
from frappe.utils import date_diff, getdate, nowdate

from sgc.dashboards import ACCION_CERRADA, TRATAMIENTO_CERRADO

SIN_PLAZO = "Sin plazo"
EN_PLAZO = "En plazo"
POR_VENCER = "Por vencer"
VENCIDO = "Vencido"
CERRADO_EN_PLAZO = "Cerrado en plazo"
CERRADO_FUERA = "Cerrado fuera de plazo"

# Días antes del compromiso en que un registro abierto pasa a «Por vencer».
DIAS_POR_VENCER = 7

# Estados que cierran el plazo de cada DocType. Son los mismos con los que cuentan
# los cuadros de mando, para que «vencidas» signifique lo mismo en todas partes: una
# acción sigue abierta hasta que se verifica, y un tratamiento hasta que se implementa.
CIERRES = {
	"No Conformidad": ("Cerrada eficaz", "Cerrada no eficaz"),
	"Accion Mejora": ACCION_CERRADA,
	"Plan Mejora": ("Cerrado",),
	"Tratamiento Riesgo": TRATAMIENTO_CERRADO,
}


def calcular(fecha_compromiso, fecha_cierre=None, hoy=None):
	"""Devuelve `(estado_plazo, dias_retraso)`.

	Sin `fecha_cierre` el registro se trata como abierto. Un registro sin fecha de
	compromiso no está vencido ni en plazo: no tiene plazo que cumplir.
	"""
	if not fecha_compromiso:
		return SIN_PLAZO, 0

	compromiso = getdate(fecha_compromiso)
	if fecha_cierre:
		retraso = date_diff(getdate(fecha_cierre), compromiso)
		return (CERRADO_FUERA, retraso) if retraso > 0 else (CERRADO_EN_PLAZO, 0)

	retraso = date_diff(getdate(hoy or nowdate()), compromiso)
	if retraso > 0:
		return VENCIDO, retraso
	if -retraso <= DIAS_POR_VENCER:
		return POR_VENCER, 0
	return EN_PLAZO, 0


def aplicar(doc):
	"""Sella `fecha_cierre` y calcula el estado del plazo. Se llama desde `validate`.

	`fecha_cierre` se pone la primera vez que el registro entra en un estado de cierre,
	y se borra si vuelve a uno abierto: un registro reabierto no está cerrado.
	"""
	if doc.estado in CIERRES[doc.doctype]:
		if not doc.fecha_cierre:
			doc.fecha_cierre = nowdate()
	else:
		doc.fecha_cierre = None

	doc.estado_plazo, doc.dias_retraso = calcular(doc.fecha_compromiso, doc.fecha_cierre)


def recalcular_abiertos():
	"""Tarea diaria: refresca el estado del plazo de lo que sigue abierto.

	Solo escribe cuando el valor cambia, y sin tocar `modified`: que pase un día no es
	una edición del registro.
	"""
	for doctype, cierres in CIERRES.items():
		abiertos = frappe.get_all(
			doctype,
			filters={"estado": ["not in", cierres]},
			fields=["name", "fecha_compromiso", "estado_plazo", "dias_retraso"],
		)
		for fila in abiertos:
			estado, dias = calcular(fila.fecha_compromiso)
			if (estado, dias) != (fila.estado_plazo, fila.dias_retraso):
				frappe.db.set_value(
					doctype, fila.name, {"estado_plazo": estado, "dias_retraso": dias}, update_modified=False
				)
	frappe.db.commit()

