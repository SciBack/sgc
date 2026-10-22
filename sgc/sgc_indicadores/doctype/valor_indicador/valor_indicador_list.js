// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// La lista de mediciones se lee por su semáforo: el color dice de un vistazo qué valores se
// salen de la meta. Mecanismo nativo: settings.get_indicator -> [etiqueta, color, filtro]
// (frappe/public/js/frappe/model/indicator.js); al pulsar la píldora se filtra la lista.
frappe.listview_settings["Valor Indicador"] = {
	add_fields: ["semaforo"],
	get_indicator: function (doc) {
		const colores = { Verde: "green", Ambar: "orange", Rojo: "red" };
		if (doc.semaforo && colores[doc.semaforo]) {
			return [__(doc.semaforo), colores[doc.semaforo], "semaforo,=," + doc.semaforo];
		}
		return [__("Sin meta"), "gray", "semaforo,is,not set"];
	},
};
