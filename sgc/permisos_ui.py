"""Permisos efectivos del usuario, para que la SPA se pinte según su rol.

La SPA se pintaba igual para todo el mundo: el mismo menú de 43 entradas para
la DPGC que para un rol de solo lectura, y el botón «Nuevo» visible para quien
no puede crear nada. El backend rechazaba correctamente (403), pero la persona
solo lo descubría tras rellenar el formulario entero -- comprobado en
producción con `Rectorado/VR (lectura)` el 2026-08-23.

El Desk nativo de Frappe no tiene ese problema porque conoce los permisos al
pintar. Esto le da a la SPA la misma información: un mapa DocType -> acciones
permitidas, inyectado en el boot (`window.permisos_ui`) para no costar ni una
llamada extra.

⚠️ Esto es SOLO presentación. Quien decide de verdad sigue siendo el backend en
cada operación; ocultar un botón no es un control de seguridad. Sirve para que
nadie pierda el tiempo en una pantalla que no le corresponde.
"""

import frappe

# Los 7 módulos de la app (sgc/modules.txt). Se filtran los `istable` porque una
# child table no se navega: sus permisos son los del documento que la contiene.
MODULOS = (
	"SGC UPeU",
	"SGC Estructura",
	"SGC Nucleo",
	"SGC Auditoria",
	"SGC Riesgos",
	"SGC Gobierno",
	"SGC Procesos",
)

ACCIONES = ("read", "create", "write", "delete")


def permisos_de_ui(user: str | None = None) -> dict[str, dict[str, bool]]:
	"""DocType -> {read, create, write, delete} para el usuario dado.

	Un DocType ausente del mapa NO significa «denegado»: significa «no es del
	SGC» (File, User, Comment...). La SPA trata la ausencia como «no opino» y
	deja que mande el backend; así un DocType nuevo nunca desaparece de la
	interfaz por olvidarse de listarlo aquí.
	"""
	doctypes = frappe.get_all(
		"DocType",
		filters={"module": ["in", MODULOS], "istable": 0},
		pluck="name",
	)
	permisos: dict[str, dict[str, bool]] = {}
	for dt in doctypes:
		permisos[dt] = {
			accion: bool(frappe.has_permission(dt, accion, user=user))
			for accion in ACCIONES
		}
	return permisos


@frappe.whitelist()
def mis_permisos() -> dict[str, dict[str, bool]]:
	"""Mismo mapa, pedido a demanda. Existe para el modo dev de la SPA (que
	corre en Vite, sin el boot de Jinja) y para refrescar tras un cambio de
	roles sin recargar la página."""
	return permisos_de_ui()
