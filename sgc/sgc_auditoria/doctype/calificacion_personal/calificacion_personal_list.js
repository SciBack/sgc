// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// Estado de la calificación en color. Mecanismo nativo:
// settings.get_indicator -> [etiqueta, color, filtro] (frappe/public/js/frappe/model/indicator.js).
frappe.listview_settings["Calificacion Personal"] = {
	add_fields: ["estado"],
	get_indicator: function (doc) {
		const colores = { Vigente: "green", Vencida: "orange", Revocada: "red" };
		const estado = doc.estado || "Vigente";
		return [__(estado), colores[estado] || "gray", "estado,=," + estado];
	},
};
