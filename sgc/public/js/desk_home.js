// SGC — entrada directa al workspace, saltando el "apps screen"
// -----------------------------------------------------------------------------
// Problema (Frappe v16): la entrada "pelada" al Desk (`/desk`, el ítem
// «Escritorio» del sidebar_header.js:15 -> frappe.set_route("/desk"), y el
// breadcrumb Home) resuelve la ruta vacía por `frappe.boot.home_page`
// (router.js render() -> pageview.js show("") -> boot.home_page). Ese home_page
// solo puede ser una **Page** (boot.py::add_home_page -> desk_page.get); un
// Workspace ("sgc") no es Page, así que cae al fallback "desktop" = el apps
// screen. Con una sola app + workspace propio eso obliga a un clic extra (o
// queda en blanco para usuarios restringidos).
//
// Fix agnóstico de versión, sin tocar el core: usamos el mecanismo nativo
// `frappe.re_route` (router.js:325-340), que el router consulta ANTES de
// renderizar (route() línea 144), de modo que la redirección ocurre sin flash
// del apps screen. El destino lo toma del `default_path` que el propio server
// ya resolvió (frappe.apps.get_default_path -> add_to_apps_screen.route),
// entregado en el boot como `boot.apps_data.default_path` (sessions.py:178).
//
// Solo redirige cuando el server resolvió a un workspace concreto del Desk
// ("/desk/<slug>"); si resolvió a "/desk" o "/apps" (varias apps), NO toca nada
// y se conserva el apps screen. Verificado en 16.32; get_default_path y
// re_route existen idénticos en 16.27.
frappe.provide("frappe.re_route");

(() => {
	const boot = frappe.boot || {};

	// Los System Manager conservan el apps screen (pueden querer conmutar de app
	// o entrar a la rejilla). El salto directo es para los roles operativos
	// (p. ej. «Dueño de Proceso»), que solo tienen su workspace.
	const roles = (boot.user && boot.user.roles) || [];
	if (roles.includes("System Manager")) return;

	const default_path = boot.apps_data && boot.apps_data.default_path;
	const match = typeof default_path === "string" && default_path.match(/^\/desk\/(.+)$/);
	if (match) {
		// clave "" = sub_path vacío (= /desk pelado) -> slug del workspace destino
		frappe.re_route[""] = match[1];
	}
})();
