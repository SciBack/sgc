// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// Indicador de color por nivel BPM en la list view de Proceso, para distinguir
// de un vistazo Macroproceso (N0) / Proceso (N1) / Subproceso (N2).
// Mecanismo nativo: frappe.get_indicator() usa settings.get_indicator
// (frappe/public/js/frappe/model/indicator.js:88). Devuelve [label, color, filtro];
// el tercer elemento hace que al hacer clic en la píldora se filtre la lista.
frappe.listview_settings["Proceso"] = {
	add_fields: ["nivel_bpm", "is_group"],
	get_indicator: function (doc) {
		const colores = {
			Macroproceso: "purple",
			Proceso: "blue",
			Subproceso: "cyan",
		};
		const nivel = doc.nivel_bpm;
		if (nivel && colores[nivel]) {
			return [__(nivel), colores[nivel], "nivel_bpm,=," + nivel];
		}
		return [__("Sin nivel"), "gray", "nivel_bpm,=,"];
	},
};
