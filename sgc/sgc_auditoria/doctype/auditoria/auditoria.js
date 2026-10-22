// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// «Crear ▾»: el paso siguiente ya enlazado a este registro, como en ERPNext. Solo lo que el usuario
// puede crear (frappe.model.can_create) y solo con el registro guardado. frappe.new_doc pasa los
// valores por frappe.route_options (frappe/public/js/frappe/model/create_new.js:364).
frappe.ui.form.on("Auditoria", {
	refresh(frm) {
		if (frm.is_new()) return;
		[
			["Lista Verificacion", __("Lista de verificación"), { auditoria: frm.doc.name }],
			["Hallazgo Auditoria", __("Hallazgo de auditoría"), { auditoria: frm.doc.name }],
			["Informe Auditoria", __("Informe de auditoría"), { auditoria: frm.doc.name }],
		].forEach(([doctype, etiqueta, valores]) => {
			if (!frappe.model.can_create(doctype)) return;
			frm.add_custom_button(etiqueta, () => frappe.new_doc(doctype, valores), __("Crear"));
		});
	},
});

// Cifras del registro en la pestaña «Resumen» (frm.dashboard.add_indicator, como el panel del
// cliente en ERPNext). Cuentan con frappe.db.count: cada usuario ve solo lo que puede leer.
frappe.ui.form.on("Auditoria", {
	refresh(frm) {
		if (frm.is_new()) return;
		const pintar = (etiqueta, color) => frm.dashboard.add_indicator(etiqueta, color);
		const actividades = frm.doc.actividades || [];
		const hechas = actividades.filter((a) => a.realizada).length;
		Promise.all([
			frappe.db.count("Hallazgo Auditoria", { filters: { auditoria: frm.doc.name } }),
			frappe.db.count("Hallazgo Auditoria", { filters: { auditoria: frm.doc.name, estado: "Abierto" } }),
		]).then(([hallazgos, abiertos]) => {
			pintar(__("Actividades hechas: {0}/{1}", [hechas, actividades.length]),
				actividades.length && hechas === actividades.length ? "green" : "blue");
			pintar(__("Hallazgos: {0}", [hallazgos]), hallazgos ? "blue" : "gray");
			pintar(__("Hallazgos abiertos: {0}", [abiertos]), abiertos ? "orange" : "green");
		});
	},
});
