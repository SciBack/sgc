// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// Estado del acuse en color: pendiente pide atención, acusado ya no. Mecanismo nativo:
// settings.get_indicator -> [etiqueta, color, filtro] (frappe/public/js/frappe/model/indicator.js).
frappe.listview_settings["Acuse Lectura"] = {
	add_fields: ["estado"],
	get_indicator: function (doc) {
		const colores = { Pendiente: "orange", Acusado: "green", "Sin efecto": "gray" };
		const estado = doc.estado || "Pendiente";
		return [__(estado), colores[estado] || "gray", "estado,=," + estado];
	},
};
