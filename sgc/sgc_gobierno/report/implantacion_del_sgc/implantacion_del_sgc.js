// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

frappe.query_reports["Implantacion del SGC"] = {
	filters: [],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "estado" && data) {
			const color = { Cumple: "green", "En curso": "orange", "Sin empezar": "red" }[data.estado];
			if (color) value = `<span class="indicator-pill ${color}">${value}</span>`;
		}
		return value;
	},
};
