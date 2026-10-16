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
