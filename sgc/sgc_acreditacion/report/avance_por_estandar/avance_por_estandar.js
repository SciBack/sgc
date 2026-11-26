// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

frappe.query_reports["Avance por Estandar"] = {
	filters: [
		{
			fieldname: "autoevaluacion",
			label: __("Autoevaluación"),
			fieldtype: "Link",
			options: "Autoevaluacion",
			reqd: 1,
		},
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "semaforo" && data) {
			const color = { Logrado: "green", "En proceso": "orange", "No logrado": "red", "Sin empezar": "gray" }[data.semaforo];
			if (color) value = `<span class="indicator-pill ${color}">${value}</span>`;
		}
		return value;
	},
};
