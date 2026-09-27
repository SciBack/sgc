// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// Lista de verificación (#32): reutilizar las preguntas en otra auditoría y
// convertir en hallazgos los puntos no conformes. El servidor valida permisos,
// estado de la auditoría y que no se dupliquen hallazgos.
frappe.ui.form.on("Lista Verificacion", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("Usar en una auditoría"), () => {
			frappe.prompt(
				{
					fieldname: "auditoria",
					fieldtype: "Link",
					options: "Auditoria",
					label: __("Auditoría"),
					reqd: 1,
				},
				(valores) => {
					frm.call("usar_en_auditoria", { auditoria: valores.auditoria }).then((r) => {
						if (r.message) frappe.set_route("Form", "Lista Verificacion", r.message);
					});
				},
				__("Usar las preguntas en una auditoría"),
				__("Crear lista")
			);
		});

		const hay_hallazgos_por_generar = (frm.doc.items || []).some(
			(i) => ["No conforme", "Observacion"].includes(i.resultado) && !i.hallazgo
		);
		if (frm.doc.auditoria && hay_hallazgos_por_generar) {
			frm.add_custom_button(__("Generar hallazgos"), () => {
				frm.call("generar_hallazgos").then(() => frm.reload_doc());
			});
		}
	},
});
