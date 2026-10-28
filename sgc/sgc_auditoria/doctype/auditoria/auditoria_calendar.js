// Calendario de las auditorías por su fecha planificada.
frappe.views.calendar["Auditoria"] = {
	field_map: {
		start: "fecha_plan",
		end: "fecha_plan",
		id: "name",
		title: "titulo",
		allDay: "allDay",
	},
	filters: [{ fieldtype: "Link", fieldname: "proceso", options: "Proceso", label: __("Proceso") }],
	get_events_method: "frappe.desk.calendar.get_events",
};
