// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// Enviar un documento o una ficha publicados por correo (#92). El servidor decide
// qué sale (solo lo publicado, sin archivo si es de solo consulta, ficha pública
// para externos) y lo pasa por el modo de ensayo y la lista blanca.
frappe.provide("sgc.envio");

sgc.envio.dialogo = function (frm) {
	const d = new frappe.ui.Dialog({
		title: __("Enviar por correo"),
		fields: [
			{
				fieldname: "usuarios",
				fieldtype: "MultiSelectList",
				label: __("Usuarios del sistema"),
				options: "User",
				get_data: (txt) => frappe.db.get_link_options("User", txt, { enabled: 1 }),
			},
			{
				fieldname: "externos",
				fieldtype: "Small Text",
				label: __("Otras direcciones"),
				description: __("Separadas por coma o una por línea. También personal externo."),
			},
			{ fieldname: "mensaje", fieldtype: "Small Text", label: __("Mensaje") },
		],
		primary_action_label: __("Enviar"),
		primary_action(v) {
			frappe
				.call("sgc.envio.enviar_por_correo", {
					doctype: frm.doctype,
					name: frm.doc.name,
					usuarios: v.usuarios || [],
					externos: v.externos || "",
					mensaje: v.mensaje || "",
				})
				.then((r) => {
					d.hide();
					const res = r.message || {};
					const enviados = (res.enviados || []).length;
					const retenidos = (res.retenidos || []).length;
					frappe.msgprint(
						retenidos
							? __("Enviado a {0}. Retenidos {1} por la configuración del correo (ensayo o lista blanca): constan en Registro Correo.", [enviados, retenidos])
							: __("Enviado a {0} destinatario(s).", [enviados])
					);
					frm.reload_doc();
				});
		},
	});
	d.show();
};

sgc.envio.ROLES = ["DPGC", "Analista de Calidad (DPGC)", "Dueño de Proceso", "System Manager"];

sgc.envio.boton = function (frm) {
	if (frm.is_new() || frm.doc.estado !== "Publicado") return;
	if (!sgc.envio.ROLES.some((rol) => frappe.user.has_role(rol))) return;
	frm.add_custom_button(__("Enviar por correo"), () => sgc.envio.dialogo(frm));
};
