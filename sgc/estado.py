"""Estado de la instancia, para dar soporte sin entrar por SSH (#53).

    GET /api/method/sgc.estado.instancia      (sesión o token de un System Manager)

Responde a «¿qué tienes instalado y cómo está?» con lo mínimo:

- `version`: la de la app en el código y la de Frappe.
- `migracion`: cuándo fue el último `migrate` y qué versión de la app registró. Si no coincide
  con la del código, la imagen se actualizó y nadie migró: `pendiente` lo dice.
- `scheduler`: si las tareas programadas siguen corriendo (#42).
- `correo`: si hay por dónde salir, si está silenciado y en qué modo (#41).
- `sso`: si hay inicio de sesión institucional.

**Y nada más.** Esta instancia guarda datos de calidad de una universidad: no se devuelven
conteos de negocio, nombres de usuario, rutas del sistema ni configuración que ayude a atacarla.
La lista de lo que sale está fijada en `CAMPOS` y la comprueban los tests.

**Acceso.** Solo System Manager. Sin sesión, Frappe rechaza la llamada antes de llegar aquí
(no lleva `allow_guest`): un endpoint de salud abierto le dice a cualquiera qué versión atacar.

**Responde aunque algo esté roto.** Cada bloque se calcula por separado; si uno falla, ese bloque
dice `{"estado": "error"}` y los demás salen igual. Un endpoint de salud que falla cuando algo
va mal no sirve justo cuando hace falta. Del error solo se devuelve su tipo, nunca su mensaje,
que puede llevar rutas o datos.

Lo mismo por consola: `bench --site <sitio> execute sgc.estado.instancia`.
"""

import frappe

import sgc

# Las claves de primer nivel y, dentro de cada una, las únicas que pueden salir.
CAMPOS = {
	"version": {"sgc", "frappe"},
	"migracion": {"fecha", "version_sgc", "pendiente"},
	"scheduler": {"ok", "apagado", "horas_desde_ultima"},
	"correo": {"configurado", "silenciado", "modo"},
	"sso": {"configurado"},
}
ERROR = "error"


def _version():
	return {"sgc": sgc.__version__, "frappe": frappe.__version__}


def _migracion():
	instaladas = frappe.get_single("Installed Applications")
	registrada = next(
		(fila.app_version for fila in instaladas.installed_applications if fila.app_name == "sgc"), None
	)
	return {
		"fecha": str(instaladas.modified) if instaladas.modified else None,
		"version_sgc": registrada,
		"pendiente": registrada != sgc.__version__,
	}


def _scheduler():
	from sgc import latido

	resultado = latido.comprobar()
	return {
		"ok": not resultado["alerta"],
		"apagado": bool(resultado["scheduler_apagado"]),
		"horas_desde_ultima": resultado["horas_desde_ultima"],
	}


def _correo():
	from sgc import correo

	return {
		# Lo mismo que mira Frappe al enviar (ver sgc.verificacion.correo.cuenta_saliente).
		"configurado": bool(
			frappe.db.get_value("Email Account", {"enable_outgoing": 1, "default_outgoing": 1})
			or frappe.conf.get("mail_server")
		),
		"silenciado": bool(frappe.conf.get("mute_emails")),
		"modo": correo.modo(),
	}


def _sso():
	return {"configurado": bool(frappe.get_all("Social Login Key", filters={"enable_social_login": 1}, limit=1))}


BLOQUES = {
	"version": _version,
	"migracion": _migracion,
	"scheduler": _scheduler,
	"correo": _correo,
	"sso": _sso,
}


def _bloque(nombre, calcular):
	try:
		datos = calcular()
	except Exception as e:
		return {"estado": ERROR, "tipo": type(e).__name__}
	# Defensa en profundidad: aunque un bloque devolviera de más, solo sale lo declarado.
	return {clave: valor for clave, valor in datos.items() if clave in CAMPOS[nombre]}


def componer():
	"""El estado de la instancia, sin comprobar permisos. Lo usan el endpoint y los tests."""
	return {nombre: _bloque(nombre, calcular) for nombre, calcular in BLOQUES.items()}


@frappe.whitelist(methods=["GET"])
def instancia():
	frappe.only_for("System Manager")
	return componer()
