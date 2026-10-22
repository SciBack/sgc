// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// «Crear ▾»: el paso siguiente ya enlazado a este registro, como en ERPNext. Solo lo que el usuario
// puede crear (frappe.model.can_create) y solo con el registro guardado. frappe.new_doc pasa los
// valores por frappe.route_options (frappe/public/js/frappe/model/create_new.js:364).
frappe.ui.form.on("Proceso", {
	refresh(frm) {
		if (frm.is_new()) return;
		[
			["Ficha Caracterizacion Proceso", __("Ficha de caracterización"), { proceso: frm.doc.name }],
			["Procedimiento", __("Procedimiento"), { proceso: frm.doc.name }],
			["Documento Controlado", __("Documento controlado"), { proceso: frm.doc.name }],
			["Indicador", __("Indicador"), { proceso: frm.doc.name }],
			["Riesgo", __("Riesgo"), { proceso: frm.doc.name }],
		].forEach(([doctype, etiqueta, valores]) => {
			if (!frappe.model.can_create(doctype)) return;
			frm.add_custom_button(etiqueta, () => frappe.new_doc(doctype, valores), __("Crear"));
		});
	},
});

// Cifras del registro en la pestaña «Resumen» (frm.dashboard.add_indicator, como el panel del
// cliente en ERPNext). Cuentan con frappe.db.count: cada usuario ve solo lo que puede leer.
frappe.ui.form.on("Proceso", {
	refresh(frm) {
		if (frm.is_new()) return;
		const pintar = (etiqueta, color) => frm.dashboard.add_indicator(etiqueta, color);
		const de_este = { proceso: frm.doc.name };
		Promise.all([
			frappe.db.count("Procedimiento", { filters: de_este }),
			frappe.db.count("Documento Controlado", { filters: de_este }),
			frappe.db.count("Documento Controlado", { filters: { ...de_este, estado: "Publicado" } }),
			frappe.db.count("Indicador", { filters: de_este }),
			frappe.db.count("No Conformidad", {
				filters: { ...de_este, estado: ["not in", ["Cerrada eficaz", "Cerrada no eficaz"]] },
			}),
			frappe.db.count("Riesgo", { filters: de_este }),
		]).then(([procedimientos, documentos, publicados, indicadores, nc_abiertas, riesgos]) => {
			const responsable = frm.doc.responsable
				? frappe.user.full_name(frm.doc.responsable)
				: __("sin asignar");
			pintar(__("Responsable: {0}", [responsable]), frm.doc.responsable ? "green" : "red");
			pintar(__("Procedimientos: {0}", [procedimientos]), procedimientos ? "blue" : "gray");
			pintar(
				__("Documentos publicados: {0}/{1}", [publicados, documentos]),
				documentos && publicados === documentos ? "green" : documentos ? "orange" : "gray"
			);
			pintar(__("Indicadores: {0}", [indicadores]), indicadores ? "blue" : "gray");
			pintar(__("NC abiertas: {0}", [nc_abiertas]), nc_abiertas ? "red" : "green");
			pintar(__("Riesgos: {0}", [riesgos]), riesgos ? "blue" : "gray");
		});
	},
});
