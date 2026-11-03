// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

frappe.query_reports["Tiempos de Tratamiento"] = {
	filters: [
		{
			fieldname: "tipo",
			label: __("Registro"),
			fieldtype: "Select",
			options: [
				{ value: "No Conformidad", label: __("No conformidades") },
				{ value: "Accion Mejora", label: __("Acciones de mejora") },
				{ value: "Plan Mejora", label: __("Planes de mejora") },
				{ value: "Salida No Conforme", label: __("Salidas no conformes") },
				{ value: "Evento Riesgo", label: __("Eventos de riesgo") },
				{ value: "Tratamiento Riesgo", label: __("Tratamientos de riesgo") },
				{ value: "Documento Controlado", label: __("Documentos controlados") },
				{ value: "Ficha Caracterizacion Proceso", label: __("Fichas de caracterización") },
			],
			default: "No Conformidad",
			reqd: 1,
		},
		{ fieldname: "desde", label: __("Creados desde"), fieldtype: "Date" },
		{ fieldname: "hasta", label: __("Creados hasta"), fieldtype: "Date" },
	],
};
