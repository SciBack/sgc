// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// Estado de la alerta en color: abierta pide atención, resuelta ya no. Mecanismo nativo:
// settings.get_indicator -> [etiqueta, color, filtro] (frappe/public/js/frappe/model/indicator.js).
frappe.listview_settings["Alerta Indicador"] = {
	add_fields: ["estado"],
	get_indicator: function (doc) {
		const colores = {
			Abierta: "orange",
			"En atención": "light-blue",
			Resuelta: "green",
			Descartada: "gray",
		};
		const estado = doc.estado || "Abierta";
		return [__(estado), colores[estado] || "gray", "estado,=," + estado];
	},
};
