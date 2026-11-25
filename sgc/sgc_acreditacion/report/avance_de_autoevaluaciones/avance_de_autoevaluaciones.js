// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

frappe.query_reports["Avance de Autoevaluaciones"] = {
	filters: [
		{ fieldname: "marco_normativo", label: __("Modelo"), fieldtype: "Link", options: "Marco Normativo" },
		{ fieldname: "facultad", label: __("Facultad"), fieldtype: "Link", options: "Unidad Organica" },
		{ fieldname: "sede", label: __("Sede"), fieldtype: "Link", options: "Unidad Organica" },
		{ fieldname: "programa_sede", label: __("Programa y sede"), fieldtype: "Link", options: "Programa Sede" },
		{
			fieldname: "estado",
			label: __("Estado"),
			fieldtype: "Select",
			options: ["", "Planificada", "En curso", "En revision", "Consolidada", "Cerrada"],
		},
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "evaluacion_externa" && data) {
			const color = data.evaluacion_externa === __("Sí") ? "green" : "gray";
			value = `<span class="indicator-pill ${color}">${value}</span>`;
		}
		return value;
	},
};
