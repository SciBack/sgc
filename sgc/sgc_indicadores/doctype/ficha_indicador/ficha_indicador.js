// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// «Crear ▾»: el paso siguiente ya enlazado a este registro, como en ERPNext. Solo lo que el usuario
// puede crear (frappe.model.can_create) y solo con el registro guardado. frappe.new_doc pasa los
// valores por frappe.route_options (frappe/public/js/frappe/model/create_new.js:364).
frappe.ui.form.on("Ficha Indicador", {
	refresh(frm) {
		if (frm.is_new()) return;
		[
			["Valor Indicador", __("Medición"), { indicador: frm.doc.indicador }],
		].forEach(([doctype, etiqueta, valores]) => {
			if (!frappe.model.can_create(doctype)) return;
			frm.add_custom_button(etiqueta, () => frappe.new_doc(doctype, valores), __("Crear"));
		});
	},
});

// Cifras del registro en la pestaña «Resumen» (frm.dashboard.add_indicator, como el panel del
// cliente en ERPNext). Cuentan con frappe.db.count: cada usuario ve solo lo que puede leer.
frappe.ui.form.on("Ficha Indicador", {
	refresh(frm) {
		if (frm.is_new()) return;
		const pintar = (etiqueta, color) => frm.dashboard.add_indicator(etiqueta, color);
		if (!frm.doc.indicador) return;
		const del_indicador = { indicador: frm.doc.indicador };
		Promise.all([
			frappe.db.get_list("Valor Indicador", {
				filters: del_indicador, fields: ["valor_num", "valor_texto", "semaforo"],
				order_by: "fecha desc", limit: 1,
			}),
			frappe.db.count("Valor Indicador", { filters: del_indicador }),
			frappe.db.count("Valor Indicador", { filters: { ...del_indicador, semaforo: "Rojo" } }),
		]).then(([ultima, total, en_rojo]) => {
			const u = ultima[0];
			const colores = { Verde: "green", Ambar: "orange", Rojo: "red" };
			pintar(u ? __("Última medición: {0}", [u.valor_texto || u.valor_num]) : __("Sin mediciones"),
				u ? colores[u.semaforo] || "gray" : "gray");
			pintar(__("Mediciones: {0}", [total]), total ? "blue" : "gray");
			pintar(__("En rojo: {0}", [en_rojo]), en_rojo ? "red" : "green");
		});
	},
});
