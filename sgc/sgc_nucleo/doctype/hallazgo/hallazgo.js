// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// Escalar a no conformidad: el método existía y estaba probado (`capa.py`), pero
// sin botón no había forma de usarlo desde el Desk. El servidor exige permiso
// para crear una No Conformidad y es idempotente; aquí solo se evita ofrecer el
// botón donde no aplica.
const TIPOS_QUE_ESCALAN = ["Debilidad", "Oportunidad de mejora"];
const ESTADOS_CERRADOS = ["Cerrado eficaz", "Cerrado no eficaz"];

frappe.ui.form.on("Hallazgo", {
	refresh(frm) {
		if (
			frm.is_new() ||
			frm.doc.no_conformidad ||
			!TIPOS_QUE_ESCALAN.includes(frm.doc.tipo) ||
			ESTADOS_CERRADOS.includes(frm.doc.estado) ||
			!frappe.model.can_create("No Conformidad")
		) {
			return;
		}
		frm.add_custom_button(__("Escalar a no conformidad"), () => {
			frappe.confirm(
				__("Se creará una no conformidad con los datos de este hallazgo. ¿Continuar?"),
				() => {
					frm.call("escalar_a_no_conformidad").then((r) => {
						if (!r.message) return;
						frm.reload_doc();
						frappe.show_alert({
							message: __("Escalado a la no conformidad {0}", [r.message]),
							indicator: "green",
						});
					});
				}
			);
		});
	},
});

// «Crear ▾»: el paso siguiente ya enlazado a este registro, como en ERPNext. Solo lo que el usuario
// puede crear (frappe.model.can_create) y solo con el registro guardado. frappe.new_doc pasa los
// valores por frappe.route_options (frappe/public/js/frappe/model/create_new.js:364).
frappe.ui.form.on("Hallazgo", {
	refresh(frm) {
		if (frm.is_new()) return;
		[
			["Accion Mejora", __("Acción de mejora"), { hallazgo: frm.doc.name }],
		].forEach(([doctype, etiqueta, valores]) => {
			if (!frappe.model.can_create(doctype)) return;
			frm.add_custom_button(etiqueta, () => frappe.new_doc(doctype, valores), __("Crear"));
		});
	},
});

// El criterio incumplido, solo del marco de la autoevaluación: en el desplegable salían los
// elementos de los 10 marcos mezclados. Si el hallazgo no viene de una autoevaluación, no se filtra.
(() => {
	function leer_marco(frm) {
		frm.marco_de_autoevaluacion = null;
		if (!frm.doc.autoevaluacion) return;
		frappe.db.get_value("Autoevaluacion", frm.doc.autoevaluacion, "marco_normativo").then((r) => {
			frm.marco_de_autoevaluacion = (r.message && r.message.marco_normativo) || null;
		});
	}

	frappe.ui.form.on("Hallazgo", {
		setup(frm) {
			frm.set_query("criterio", () =>
				frm.marco_de_autoevaluacion
					? { filters: { marco_normativo: frm.marco_de_autoevaluacion } }
					: {}
			);
		},
		refresh: leer_marco,
		autoevaluacion: leer_marco,
	});
})();
