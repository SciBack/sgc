"""¿Se avisó a los usuarios de esta ventana de mantenimiento? (#55)

Una actualización corta el servicio unos minutos. Lo que no puede pasar es que ese corte pille a
la gente por sorpresa: antes de actualizar tiene que haber salido un `Comunicado` de tipo
«Mantenimiento programado» (#92) cuya ventana cubra el momento de la actualización. Ese
comunicado ya exige 24 h de antelación al enviarse, así que aquí solo se mira que exista.

Lo consulta `deploy/actualizar.sh` antes de tocar nada:

    bench --site <sitio> execute sgc.mantenimiento.ventana_avisada

No es un endpoint: no lleva `@frappe.whitelist`. Solo lo ejecuta quien opera la instancia.
"""

import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime

from sgc.sgc_gobierno.doctype.comunicado.comunicado import MANTENIMIENTO

# Se admite empezar un poco antes de la hora anunciada: preparar la imagen y el respaldo lleva
# unos minutos, y ese rato el sistema sigue funcionando.
MARGEN_MINUTOS = 30


def ventana_avisada(momento=None, margen_minutos=MARGEN_MINUTOS):
	"""El comunicado enviado cuya ventana cubre `momento` (ahora, por defecto), o `avisado: False`.

	Cubrir es: inicio - margen <= momento <= fin. Un mantenimiento anunciado sin fin solo cubre su
	inicio más el margen: «empieza a las 22:00» no autoriza a cortar a las 3:00.
	"""
	momento = get_datetime(momento) if momento else now_datetime()
	# Sin filtro «is set» sobre el Datetime: en PostgreSQL compara la fecha con '' y revienta.
	enviados = frappe.get_all(
		"Comunicado",
		filters={"tipo": MANTENIMIENTO, "estado": "Enviado"},
		fields=["name", "inicio_mantenimiento", "fin_mantenimiento", "n_destinatarios"],
		order_by="creation desc",
		limit=0,
	)
	for c in enviados:
		if not c.inicio_mantenimiento:
			continue
		inicio = get_datetime(c.inicio_mantenimiento)
		fin = get_datetime(c.fin_mantenimiento) if c.fin_mantenimiento else add_to_date(inicio, minutes=margen_minutos)
		if add_to_date(inicio, minutes=-margen_minutos) <= momento <= fin:
			return {
				"avisado": True,
				"comunicado": c.name,
				"inicio": str(inicio),
				"fin": str(fin) if c.fin_mantenimiento else None,
				"destinatarios": c.n_destinatarios or 0,
			}
	return {"avisado": False, "momento": str(momento)}
