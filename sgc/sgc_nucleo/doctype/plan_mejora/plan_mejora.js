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

// «Obtener de → Hallazgos de la autoevaluación»: una acción de mejora por cada debilidad u
// oportunidad elegida, ya enlazada al plan y al hallazgo (el diálogo nativo que ERPNext usa en
// «Obtener artículos de», `frappe.ui.form.MultiSelectDialog`). El servidor
// (`acciones_desde_hallazgos`) no repite hallazgos que ya tengan acción.
frappe.ui.form.on("Plan Mejora", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.estado === "Cerrado" || !frappe.model.can_create("Accion Mejora")) return;
		frm.add_custom_button(
			__("Hallazgos de la autoevaluación"),
			() => {
				new frappe.ui.form.MultiSelectDialog({
					doctype: "Hallazgo",
					target: frm,
					setters: {},
					primary_action_label: __("Crear acciones"),
					get_query() {
						const filters = { tipo: ["in", ["Debilidad", "Oportunidad de mejora"]] };
						if (frm.doc.autoevaluacion) filters.autoevaluacion = frm.doc.autoevaluacion;
						return { filters };
					},
					action(seleccion) {
						if (!seleccion || !seleccion.length) return;
						frm.call("acciones_desde_hallazgos", { nombres: seleccion }).then((r) => {
							this.dialog.hide();
							frappe.show_alert({
								message: r.message
									? __("{0} acciones de mejora creadas", [r.message])
									: __("Esos hallazgos ya tenían acción en el plan"),
								indicator: r.message ? "green" : "blue",
							});
							frm.reload_doc();
						});
					},
				});
			},
			__("Obtener de")
		);
	},
});
