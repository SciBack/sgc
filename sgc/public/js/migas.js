// SGC — migas de pan coherentes en el Desk (revisión del 27-sep-2026)
// -----------------------------------------------------------------------------
// La miga de un área del SGC es  ⌂ > Área > Pantalla > Registro  venga de donde
// venga. Casi todo lo resuelve la configuración (una portada por área, barras sin
// pantallas repetidas y `translations/es.csv`, ver setup/f18_workspace.py). Aquí
// solo se cubren cuatro huecos de Frappe 16.32 (`frappe/public/js/frappe/views/breadcrumbs.js`):
//
// 1. Al llegar DESDE una portada, `set_workspace` busca el área solo entre las
//    portadas del módulo de la pantalla y, si no la encuentra, no tiene plan B:
//    desde la portada general, las listas de las otras áreas salían sin área.
//    Se completa con la portada del propio módulo.
// 2. En la vista árbol (Proceso, Unidad orgánica, Estándar o criterio) Frappe no
//    añade el nombre de la pantalla. Se añade como en la vista lista.
//
// No sustituye ninguna función: llama a la original y solo rellena lo que dejó
// vacío. Si una versión futura de Frappe cambia estas funciones, el guard hace
// que el Desk siga funcionando con la miga nativa.
(() => {
	const migas = frappe.breadcrumbs;
	if (!migas || typeof migas.set_workspace !== "function" || typeof migas.update !== "function") {
		return;
	}

	const es_del_sgc = (modulo) => typeof modulo === "string" && modulo.startsWith("SGC ");

	const set_workspace = migas.set_workspace;
	migas.set_workspace = function (breadcrumbs) {
		set_workspace.call(this, breadcrumbs);
		if (breadcrumbs.workspace || !es_del_sgc(breadcrumbs.module)) return;
		const portadas = (frappe.boot.module_wise_workspaces || {})[breadcrumbs.module];
		if (portadas && portadas.length) {
			breadcrumbs.workspace = portadas[0];
		}
	};

	// 3. La lista dibuja la miga ANTES de que la barra lateral cambie a la de su
	//    área, y el área de la miga es el título de la barra (su icono): al llegar
	//    desde otra pantalla salía sin área. `sidebar_setup` se emite al empezar a
	//    cambiar de barra (`sidebar.js`, setup); al terminar ese cambio se redibuja.
	$(document).on("sidebar_setup", () => {
		setTimeout(() => {
			const actual = migas.all[migas.current_page()];
			if (actual && es_del_sgc(actual.module)) migas.update();
		}, 0);
	});

	// 4. En la ruta de un informe (`query-report`), `router.meta` conserva el módulo
	//    de la pantalla ANTERIOR (p. ej. «Desk» si se venía de Tareas). Con ese
	//    módulo, `resolve_sidebar` filtra las barras por su app y descarta las del
	//    SGC, así que la barra (y el área de la miga) se quedaba en la anterior.
	//    Si la barra que enlaza el informe es del SGC, se resuelve sin ese módulo.
	const Barra = frappe.ui && frappe.ui.Sidebar;
	if (Barra && typeof Barra.prototype.resolve_sidebar === "function") {
		const resolve_sidebar = Barra.prototype.resolve_sidebar;
		Barra.prototype.resolve_sidebar = function (entity, module) {
			if ((frappe.get_route()[0] || "").toLowerCase() === "query-report") {
				const del_sgc = this.get_workspace_sidebars(entity).some((barra) => {
					const cfg = (frappe.boot.workspace_sidebar_item || {})[barra.toLowerCase()];
					return cfg && cfg.app === "sgc";
				});
				if (del_sgc) module = undefined;
			}
			return resolve_sidebar.call(this, entity, module);
		};
	}

	const update = migas.update;
	migas.update = function () {
		update.call(this);
		const actual = this.all[this.current_page()];
		const vista = (frappe.get_route()[0] || "").toLowerCase();
		if (vista === "tree" && actual && actual.doctype && es_del_sgc(actual.module)) {
			this.set_list_breadcrumb(actual);
		}
	};
})();
