// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// El color de la fila dice el estado del proceso, como en el resto de listas del SGC; el nivel BPM
// va en su propia columna. Mecanismo nativo: frappe.get_indicator() usa settings.get_indicator
// (frappe/public/js/frappe/model/indicator.js:88). Devuelve [label, color, filtro]; el tercer
// elemento hace que al hacer clic en la píldora se filtre la lista.
// hide_name_column: el nombre del proceso ES su código, que ya sale en la columna «Código».
frappe.listview_settings["Proceso"] = {
	add_fields: ["estado"],
	hide_name_column: true,
	get_indicator: function (doc) {
		const colores = { Vigente: "green", Borrador: "gray", Obsoleto: "gray" };
		const estado = doc.estado;
		if (estado) {
			return [__(estado), colores[estado] || "gray", "estado,=," + estado];
		}
		return [__("Sin estado"), "gray", "estado,is,not set"];
	},
};
