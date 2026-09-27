// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// Enviar el comunicado (#92). Una sola vez: el servidor lo sella y lo cierra.
frappe.ui.form.on("Comunicado", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.estado !== "Borrador") return;
		frm.add_custom_button(__("Enviar comunicado"), () => {
			frappe.confirm(
				__("Se enviará a los usuarios activos de los roles elegidos y no se podrá reenviar. ¿Enviar?"),
				() =>
					frm.call("enviar").then((r) => {
						const res = r.message || {};
						frappe.msgprint(
							res.retenidos
								? __("Enviado a {0}. Retenidos {1} por la configuración del correo: constan en Registro Correo.", [res.enviados, res.retenidos])
								: __("Enviado a {0} usuario(s).", [res.enviados])
						);
						frm.reload_doc();
					})
			);
		}).addClass("btn-primary");
	},
});
