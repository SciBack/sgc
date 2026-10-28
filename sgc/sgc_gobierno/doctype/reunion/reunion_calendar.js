// Calendario de las reuniones de los comités.
frappe.views.calendar["Reunion"] = {
	field_map: {
		start: "fecha",
		end: "fecha",
		id: "name",
		title: "titulo",
		allDay: "allDay",
	},
	filters: [{ fieldtype: "Link", fieldname: "comite", options: "Comite", label: __("Comité") }],
	get_events_method: "frappe.desk.calendar.get_events",
};
