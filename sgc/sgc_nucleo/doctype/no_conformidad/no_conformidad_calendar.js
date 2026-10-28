// Calendario de las no conformidades: de la detección a la fecha comprometida para cerrarlas.
frappe.views.calendar["No Conformidad"] = {
	field_map: {
		start: "fecha_deteccion",
		end: "fecha_compromiso",
		id: "name",
		title: "titulo",
		allDay: "allDay",
	},
	filters: [{ fieldtype: "Link", fieldname: "proceso", options: "Proceso", label: __("Proceso") }],
	get_events_method: "frappe.desk.calendar.get_events",
};
