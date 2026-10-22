// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// «Crear ▾»: el paso siguiente ya enlazado a este registro, como en ERPNext. Solo lo que el usuario
// puede crear (frappe.model.can_create) y solo con el registro guardado. frappe.new_doc pasa los
// valores por frappe.route_options (frappe/public/js/frappe/model/create_new.js:364).
frappe.ui.form.on("Plan Mejora", {
	refresh(frm) {
		if (frm.is_new()) return;
		[
			["Accion Mejora", __("Acción de mejora"), { plan_mejora: frm.doc.name }],
		].forEach(([doctype, etiqueta, valores]) => {
			if (!frappe.model.can_create(doctype)) return;
			frm.add_custom_button(etiqueta, () => frappe.new_doc(doctype, valores), __("Crear"));
		});
	},
});

// Cifras del registro en la pestaña «Resumen» (frm.dashboard.add_indicator, como el panel del
// cliente en ERPNext). Cuentan con frappe.db.count: cada usuario ve solo lo que puede leer.
frappe.ui.form.on("Plan Mejora", {
	refresh(frm) {
		if (frm.is_new()) return;
		const pintar = (etiqueta, color) => frm.dashboard.add_indicator(etiqueta, color);
		Promise.all([
			frappe.db.count("Accion Mejora", { filters: { plan_mejora: frm.doc.name } }),
			frappe.db.count("Accion Mejora", {
				filters: { plan_mejora: frm.doc.name, estado: ["in", ["Planificada", "En ejecucion"]] },
			}),
			frappe.db.count("Accion Mejora", {
				filters: { plan_mejora: frm.doc.name, estado: "Verificada eficaz" },
			}),
		]).then(([total, abiertas, eficaces]) => {
			pintar(__("Avance: {0}%", [frm.doc.avance_pct || 0]), (frm.doc.avance_pct || 0) >= 100 ? "green" : "blue");
			pintar(__("Acciones: {0}", [total]), total ? "blue" : "gray");
			pintar(__("Abiertas: {0}", [abiertas]), abiertas ? "orange" : "green");
			pintar(__("Verificadas eficaces: {0}", [eficaces]), eficaces ? "green" : "gray");
		});
	},
});
