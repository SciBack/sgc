// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

frappe.query_reports["Indicadores por Familia"] = {
	filters: [
		{
			fieldname: "agrupar_por",
			label: __("Agrupar por"),
			fieldtype: "Select",
			options: ["Categoría", "Marco normativo", "Proceso"],
			default: "Categoría",
			reqd: 1,
		},
		{
			fieldname: "periodo_academico",
			label: __("Periodo académico"),
			fieldtype: "Link",
			options: "Periodo Academico",
			description: __("Vacío: la última medición de cada indicador, sea del periodo que sea."),
		},
	],
};
