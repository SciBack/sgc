"""Competencia del personal y calificación de auditores (ISO 9001 §7.2, ISO 19011 §7).

Hasta ahora quien entraba en el equipo auditor bastaba con que figurase en él: nada decía
que estuviera calificado para auditar, y el único dato del miembro que hablaba de su
idoneidad —«independiente del área»— lo marca el propio interesado.

- **Competencia**: lo que se exige (requisitos), cuánto dura (vigencia en meses) y, si se
  indica, el **rol del equipo auditor** que habilita.
- **Calificación del personal**: que una persona la tiene, con su base (formación,
  evaluación o experiencia), el sustento y la evidencia. Quién la otorgó lo sella el
  sistema, y nadie se califica a sí mismo. Vence según la vigencia y se puede revocar con
  motivo.
- **La regla**: una auditoría no pasa a «En ejecución» si alguien del equipo tiene un rol
  que alguna competencia activa habilita y no tiene una calificación vigente para él. Si
  ninguna competencia habilita ese rol, no se exige: la institución todavía no lo ha
  definido, y una regla sin catálogo bloquearía la primera auditoría.

El patrón (evaluador asignado, certificado con vencimiento) viene de Frappe LMS
(`lms_certificate_evaluation`, `lms_certificate`).
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, get_fullname, getdate, nowdate

VIGENTE = "Vigente"
VENCIDA = "Vencida"
REVOCADA = "Revocada"


def calcular_estado(vence, revocada, hoy=None):
	if cint(revocada):
		return REVOCADA
	if vence and getdate(vence) < getdate(hoy or nowdate()):
		return VENCIDA
	return VIGENTE


def fecha_de_vencimiento(fecha_otorgamiento, vigencia_meses):
	return add_months(fecha_otorgamiento, cint(vigencia_meses)) if cint(vigencia_meses) > 0 else None


def roles_exigidos():
	"""Roles del equipo auditor que alguna competencia activa habilita."""
	return {
		r for r in frappe.get_all("Competencia", filters={"activa": 1}, pluck="habilita_rol") if r
	}


def calificado(usuario, rol):
	"""Si el usuario tiene una calificación vigente de una competencia activa que habilita el rol."""
	competencias = frappe.get_all("Competencia", filters={"activa": 1, "habilita_rol": rol}, pluck="name")
	if not competencias:
		return False
	return bool(frappe.db.exists(
		"Calificacion Personal",
		{"usuario": usuario, "competencia": ["in", competencias], "estado": VIGENTE},
	))


def sin_calificacion(equipo):
	"""Miembros del equipo con un rol que se exige y sin calificación vigente: [(usuario, rol)]."""
	exigidos = roles_exigidos()
	return [
		(m.usuario, m.rol)
		for m in equipo or []
		if m.usuario and m.rol in exigidos and not calificado(m.usuario, m.rol)
	]


def mensaje_sin_calificacion(faltan):
	personas = ", ".join(f"{get_fullname(u)} ({_(rol)})" for u, rol in faltan)
	return _("No se puede iniciar la ejecución: {0} sin una calificación vigente para su rol en el equipo "
			 "auditor. Regístrela en «Calificaciones del personal» o cambie el rol.").format(personas)


def marcar_vencidas():
	"""Tarea diaria: pasa a «Vencida» la calificación vigente cuyo vencimiento ya pasó.

	`between` y no `<`: Frappe envuelve el filtro en `coalesce`, y una calificación SIN
	fecha de vencimiento (la que no vence) contaría como vencida (ver `sgc/dashboards.py`).
	"""
	vencidas = frappe.get_all(
		"Calificacion Personal",
		filters={"estado": VIGENTE, "vence": ["between", ["1900-01-01", add_days(nowdate(), -1)]]},
		pluck="name",
	)
	for nombre in vencidas:
		frappe.db.set_value("Calificacion Personal", nombre, "estado", VENCIDA, update_modified=False)
	frappe.db.commit()
