// Calendario de revisiones: cada documento en la fecha en que toca revisarlo.
frappe.views.calendar["Documento Controlado"] = {
	field_map: {
		start: "fecha_proxima_revision",
		end: "fecha_proxima_revision",
		id: "name",
		title: "titulo",
		allDay: "allDay",
	},
	filters: [{ fieldtype: "Link", fieldname: "proceso", options: "Proceso", label: __("Proceso") }],
	get_events_method: "frappe.desk.calendar.get_events",
};
