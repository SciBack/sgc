// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// «Crear ▾»: el paso siguiente ya enlazado a este registro, como en ERPNext. Solo lo que el usuario
// puede crear (frappe.model.can_create) y solo con el registro guardado. frappe.new_doc pasa los
// valores por frappe.route_options (frappe/public/js/frappe/model/create_new.js:364).
frappe.ui.form.on("Autoevaluacion", {
	refresh(frm) {
		if (frm.is_new()) return;
		[
			["Hallazgo", __("Hallazgo"), { autoevaluacion: frm.doc.name, origen: "Autoevaluacion" }],
			["Plan Mejora", __("Plan de mejora"), { autoevaluacion: frm.doc.name }],
		].forEach(([doctype, etiqueta, valores]) => {
			if (!frappe.model.can_create(doctype)) return;
			frm.add_custom_button(etiqueta, () => frappe.new_doc(doctype, valores), __("Crear"));
		});
	},
});

// Cifras del registro en la pestaña «Resumen» (frm.dashboard.add_indicator, como el panel del
// cliente en ERPNext). Cuentan con frappe.db.count: cada usuario ve solo lo que puede leer.
frappe.ui.form.on("Autoevaluacion", {
	refresh(frm) {
		if (frm.is_new()) return;
		const pintar = (etiqueta, color) => frm.dashboard.add_indicator(etiqueta, color);
		const de_esta = { autoevaluacion: frm.doc.name };
		Promise.all([
			frappe.db.count("Valoracion Criterio", { filters: de_esta }),
			frappe.db.count("Valoracion Criterio", { filters: { ...de_esta, estado: ["in", ["Valorado", "Revisado"]] } }),
			frappe.db.count("Valoracion Criterio", { filters: { ...de_esta, cumple: "No cumple" } }),
			frappe.db.count("Hallazgo", { filters: de_esta }),
		]).then(([criterios, valorados, no_cumple, hallazgos]) => {
			pintar(__("Criterios valorados: {0} de {1}", [valorados, criterios]),
				criterios && valorados === criterios ? "green" : criterios ? "orange" : "gray");
			pintar(__("No cumple: {0}", [no_cumple]), no_cumple ? "red" : "green");
			pintar(__("Hallazgos: {0}", [hallazgos]), hallazgos ? "blue" : "gray");
		});
	},
});
