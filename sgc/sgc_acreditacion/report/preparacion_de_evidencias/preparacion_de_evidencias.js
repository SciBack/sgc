// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

frappe.query_reports["Preparacion de Evidencias"] = {
	filters: [
		{
			fieldname: "marco_normativo",
			label: __("Marco normativo"),
			fieldtype: "Link",
			options: "Marco Normativo",
			reqd: 1,
		},
		{
			fieldname: "unidad_responsable",
			label: __("Unidad responsable"),
			fieldtype: "Link",
			options: "Unidad Organica",
		},
		{
			fieldname: "estado",
			label: __("Estado"),
			fieldtype: "Select",
			options: ["", "Sin evidencias", "Con evidencias por validar", "Con evidencia válida"],
		},
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "estado" && data) {
			const color = {
				"Con evidencia válida": "green",
				"Con evidencias por validar": "orange",
				"Sin evidencias": "red",
			}[data.estado];
			if (color) value = `<span class="indicator-pill ${color}">${value}</span>`;
		}
		return value;
	},
};
