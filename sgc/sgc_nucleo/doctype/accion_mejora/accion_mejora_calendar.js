// Calendario y Gantt de las acciones de mejora: del inicio a la fecha comprometida.
frappe.views.calendar["Accion Mejora"] = {
	field_map: {
		start: "fecha_inicio",
		end: "fecha_compromiso",
		id: "name",
		title: "codigo",
		allDay: "allDay",
		progress: "avance_pct",
	},
	gantt: true,
	filters: [
		{ fieldtype: "Link", fieldname: "plan_mejora", options: "Plan Mejora", label: __("Plan de mejora") },
		{ fieldtype: "Link", fieldname: "responsable", options: "User", label: __("Responsable") },
	],
	get_events_method: "frappe.desk.calendar.get_events",
};
