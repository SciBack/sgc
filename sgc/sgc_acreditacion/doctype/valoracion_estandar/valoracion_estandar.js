// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// El estándar valorado, solo del marco de la autoevaluación: en el desplegable salían los elementos de
// los 10 marcos mezclados. Si no hay autoevaluación, no se filtra.
(() => {
	function leer_marco(frm) {
		frm.marco_de_autoevaluacion = null;
		if (!frm.doc.autoevaluacion) return;
		frappe.db.get_value("Autoevaluacion", frm.doc.autoevaluacion, "marco_normativo").then((r) => {
			frm.marco_de_autoevaluacion = (r.message && r.message.marco_normativo) || null;
		});
	}

	frappe.ui.form.on("Valoracion Estandar", {
		setup(frm) {
			frm.set_query("elemento_marco", () =>
				frm.marco_de_autoevaluacion
					? { filters: { marco_normativo: frm.marco_de_autoevaluacion } }
					: {}
			);
		},
		refresh: leer_marco,
		autoevaluacion: leer_marco,
	});
})();
