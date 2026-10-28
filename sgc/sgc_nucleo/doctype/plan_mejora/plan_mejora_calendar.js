// Calendario y Gantt de los planes de mejora: de la aprobación a la fecha comprometida.
frappe.views.calendar["Plan Mejora"] = {
	field_map: {
		start: "fecha_aprobacion",
		end: "fecha_compromiso",
		id: "name",
		title: "titulo",
		allDay: "allDay",
		progress: "avance_pct",
	},
	gantt: true,
	get_events_method: "frappe.desk.calendar.get_events",
};
