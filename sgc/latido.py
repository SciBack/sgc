"""Latido del scheduler — ¿siguen corriendo las tareas programadas? (#42)

Si el scheduler de Frappe se para, las tareas programadas dejan de correr sin
error, sin traza y sin síntoma: el sitio responde, la gente trabaja, y las
evidencias vencidas simplemente dejan de marcarse como vencidas. Pasa tras un
despliegue, un reinicio o un `bench` a medias.

**De dónde sale la marca.** No sellamos nada propio: Frappe ya lo hace. Cada
tarea diaria deja un `Scheduled Job Log` y lo pasa a `Complete` solo si terminó
sin excepción; si lanza, lo deja en `Failed` tras deshacer la transacción
(`ScheduledJobType.execute`, frappe/core/doctype/scheduled_job_type/
scheduled_job_type.py:143-161). Es exactamente la marca que hace falta —un fallo
repetido no parece salud— y duplicarla en un registro propio solo añadiría un
segundo sitio que puede desincronizarse del primero. El registro nativo se
conserva 90 días por defecto (`Log Settings`), muy por encima del umbral.

**Quién lo comprueba.** Esta comprobación NO corre en el scheduler: si corriera
ahí, se caería con él y nadie avisaría de nada. La dispara el Desk al cargar
(`public/js/latido_scheduler.js`) para los System Manager, y también
`sgc.verificacion.run`.

**Umbral.** 48 horas por defecto, configurable sin tocar código:

    bench --site DOMINIO set-config sgc_scheduler_umbral_horas 72

Un día de margen evita el ruido de un reinicio o de una ejecución desplazada;
lo que interesa detectar es un scheduler parado durante días, no un retraso.
"""

import frappe

UMBRAL_HORAS_DEFECTO = 48
CLAVE_UMBRAL = "sgc_scheduler_umbral_horas"

# Horas entre dos ejecuciones normales, por frecuencia de `Scheduled Job Type`.
# Una tarea semanal no está «atrasada» a las 48 h; el umbral se suma a lo que
# de todos modos tarda en tocarle. Las Cron se tratan como diarias: es lo
# conservador sin interpretar la expresión.
_PERIODO_HORAS = {
	"All": 0,
	"Hourly": 1,
	"Daily": 24,
	"Weekly": 24 * 7,
	"Monthly": 24 * 31,
	"Yearly": 24 * 366,
	"Annual": 24 * 366,
}

# Solo se envía un aviso al Error Log por día, aunque el Desk consulte en cada carga.
_CLAVE_REGISTRADO = "sgc:latido:registrado"


def periodo_horas(frecuencia):
	"""Horas entre ejecuciones de una frecuencia de Frappe («Daily Long» → 24)."""
	base = (frecuencia or "").split(" ")[0]
	return _PERIODO_HORAS.get(base, 24)


def umbral_tarea(umbral, frecuencia):
	"""Horas sin completar a partir de las cuales una tarea se da por atrasada."""
	return umbral + max(0, periodo_horas(frecuencia) - 24)


def horas_desde(momento, ahora):
	return (ahora - momento).total_seconds() / 3600


def evaluar(tareas, ahora, umbral, scheduler_apagado=False):
	"""Decide si hay que avisar. Función pura: recibe el estado, no lo lee.

	`tareas`: una entrada por tarea del app, con
	    metodo, frecuencia, detenida (bool), alta (datetime de creación del
	    Scheduled Job Type), ultima_ok (datetime | None), ultimo_estado.

	Se evalúa **cada tarea** contra su umbral, no solo la más reciente: con dos
	tareas diarias, una que falla todos los días quedaría tapada por la otra, y
	eso es justo el fallo silencioso que se quiere cortar. Un scheduler parado
	las atrasa todas, así que ese caso queda cubierto también.

	Una tarea que nunca ha completado cuenta desde que se dio de alta: una
	instalación recién hecha tiene margen, una que lleva días sin estrenarse no.
	"""
	filas = []
	for t in tareas:
		referencia = t["ultima_ok"] or t["alta"]
		horas = horas_desde(referencia, ahora)
		limite = umbral_tarea(umbral, t.get("frecuencia"))
		atrasada = horas > limite
		filas.append(
			{
				"metodo": t["metodo"],
				"frecuencia": t.get("frecuencia"),
				"ultima_ok": t["ultima_ok"],
				"ultimo_estado": t.get("ultimo_estado"),
				"horas": round(horas, 1),
				"limite": limite,
				"nunca": t["ultima_ok"] is None,
				"detenida": bool(t.get("detenida")),
				"atrasada": atrasada,
				"alerta": atrasada or bool(t.get("detenida")),
			}
		)

	marcas = [f["ultima_ok"] for f in filas if f["ultima_ok"]]
	ultima = max(marcas) if marcas else None

	return {
		"alerta": scheduler_apagado or any(f["alerta"] for f in filas),
		"scheduler_apagado": scheduler_apagado,
		"umbral": umbral,
		"ultima_ok": ultima,
		"horas_desde_ultima": round(horas_desde(ultima, ahora), 1) if ultima else None,
		"tareas": sorted(filas, key=lambda f: (not f["alerta"], f["metodo"])),
	}


def umbral_horas():
	"""El umbral configurado en site_config, o 48 si falta o no es válido."""
	from frappe.utils import cint

	valor = cint(frappe.conf.get(CLAVE_UMBRAL))
	return valor if valor > 0 else UMBRAL_HORAS_DEFECTO


def _scheduler_apagado():
	"""¿Frappe tiene el scheduler desactivado a propósito? (System Settings o site_config)."""
	from frappe.utils.scheduler import is_scheduler_inactive

	return is_scheduler_inactive(verbose=False)


def _tareas():
	"""Las tareas programadas del app, con su última ejecución completa."""
	tipos = frappe.get_all(
		"Scheduled Job Type",
		filters={"method": ["like", "sgc.%"]},
		fields=["name", "method", "frequency", "stopped", "creation"],
		limit=0,
	)
	tareas = []
	for tipo in tipos:
		ultima_ok = frappe.db.get_value(
			"Scheduled Job Log",
			{"scheduled_job_type": tipo.name, "status": "Complete"},
			"modified",
			order_by="modified desc",
		)
		ultimo_estado = frappe.db.get_value(
			"Scheduled Job Log",
			{"scheduled_job_type": tipo.name},
			"status",
			order_by="creation desc",
		)
		tareas.append(
			{
				"metodo": tipo.method,
				"frecuencia": tipo.frequency,
				"detenida": tipo.stopped,
				"alta": tipo.creation,
				"ultima_ok": ultima_ok,
				"ultimo_estado": ultimo_estado,
			}
		)
	return tareas


def comprobar():
	"""Lee el estado de la instancia y lo evalúa. No escribe nada."""
	from frappe.utils import now_datetime

	return evaluar(_tareas(), now_datetime(), umbral_horas(), _scheduler_apagado())


def _registrar(resultado):
	"""Deja constancia en el Error Log, una vez al día como mucho."""
	if frappe.cache.get_value(_CLAVE_REGISTRADO):
		return
	lineas = [f"Umbral: {resultado['umbral']} h"]
	if resultado["scheduler_apagado"]:
		lineas.append("El scheduler está desactivado en System Settings o en site_config.")
	for f in resultado["tareas"]:
		if f["alerta"]:
			lineas.append(_describir(f))
	frappe.log_error(title="SGC: las tareas programadas no están corriendo", message="\n".join(lineas))
	frappe.cache.set_value(_CLAVE_REGISTRADO, 1, expires_in_sec=24 * 3600)


def _describir(f):
	if f["detenida"]:
		return f"{f['metodo']}: detenida (Scheduled Job Type con «stopped»)."
	if f["nunca"]:
		return f"{f['metodo']}: nunca ha terminado bien; dada de alta hace {f['horas']} h."
	return (
		f"{f['metodo']}: última ejecución completa hace {f['horas']} h "
		f"(límite {f['limite']} h; último estado: {f['ultimo_estado'] or '—'})."
	)


@frappe.whitelist()
def estado():
	"""Lo que consulta el Desk al cargar. Solo para System Manager.

	Si hay alerta, además la deja registrada: el aviso en pantalla lo ve quien
	entra, el Error Log queda para quien llegue después.
	"""
	frappe.only_for("System Manager")
	resultado = comprobar()
	if resultado["alerta"]:
		_registrar(resultado)
	return resultado
