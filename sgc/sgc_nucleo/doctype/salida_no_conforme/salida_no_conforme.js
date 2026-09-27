// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// Escalar a no conformidad (#33): cuando la salida no es un caso aislado sino
// síntoma de que el sistema falla. El servidor valida permisos y es idempotente.
frappe.ui.form.on("Salida No Conforme", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.no_conformidad || frm.doc.estado === "Cerrada") {
			return;
		}
		frm.add_custom_button(__("Escalar a no conformidad"), () => {
			frappe.prompt(
				{
					fieldname: "tipo",
					fieldtype: "Select",
					label: __("Tipo de no conformidad"),
					options: "No conformidad menor\nNo conformidad mayor",
					default: "No conformidad menor",
					reqd: 1,
				},
				(valores) => {
					frm.call("escalar_a_no_conformidad", { tipo: valores.tipo }).then((r) => {
						if (!r.message) return;
						frm.reload_doc();
						frappe.show_alert({
							message: __("Escalada a la no conformidad {0}", [r.message]),
							indicator: "green",
						});
					});
				},
				__("Escalar a no conformidad"),
				__("Escalar")
			);
		});
	},
});
