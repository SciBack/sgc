// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// Indicador de nivel BPM en la list view de Procedimiento. Todo Procedimiento es
// N3 en la jerarquia (Macroproceso N0 > Proceso N1 > Subproceso N2 > Procedimiento
// N3 > Tarea N4), asi que el indicador es estatico (no hay campo derivado). Mismo
// mecanismo nativo que Proceso: settings.get_indicator -> [label, color, filtro]
// (frappe/public/js/frappe/model/indicator.js:88). Sin build, solo clear-cache.
frappe.listview_settings["Procedimiento"] = {
	get_indicator: function (doc) {
		return [__("N3 Procedimiento"), "orange"];
	},
};
