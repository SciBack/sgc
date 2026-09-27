// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// Canal de soporte (#56): «Reportar un problema», en el menú de Ayuda.
// Dos pasos: escribir y, antes de enviar, ver EXACTAMENTE lo que viaja (el texto
// y el contexto técnico). El servidor compone el ticket y decide qué contexto va;
// aquí solo se pinta. Si el helpdesk no responde, se ofrece la alternativa y el
// texto listo para copiar, no un error genérico.
frappe.provide("sgc.soporte");

sgc.soporte.abrir = function (valores) {
	const estado = frappe.boot.sgc_soporte || {};
	if (!estado.activo) {
		frappe.msgprint(__("No hay un canal de soporte configurado en este sistema."));
		return;
	}
	// La ruta en la que está la persona: el servidor le quita el identificador del registro.
	const ruta = (valores && valores.ruta) || window.location.pathname;

	const d = new frappe.ui.Dialog({
		title: __("Reportar un problema"),
		fields: [
			{ fieldname: "asunto", fieldtype: "Data", label: __("Asunto"), reqd: 1, description: __("En una línea, qué no funciona.") },
			{
				fieldname: "prioridad",
				fieldtype: "Select",
				label: __("Prioridad"),
				options: ["Baja", "Media", "Alta"],
				default: "Media",
				reqd: 1,
			},
			{
				fieldname: "descripcion",
				fieldtype: "Small Text",
				label: __("Descripción"),
				reqd: 1,
				description: __("Qué hacía, qué esperaba y qué pasó. No pegue datos de otras personas."),
			},
			{
				fieldname: "nota",
				fieldtype: "HTML",
				options: `<p class="text-muted small">${__(
					"Con su texto viaja un contexto técnico (versión, su usuario y roles, la pantalla sin el registro abierto). Lo verá completo antes de enviarlo."
				)}</p>`,
			},
		],
		primary_action_label: __("Revisar"),
		primary_action(v) {
			frappe
				.call("sgc.soporte.previsualizar", { asunto: v.asunto, descripcion: v.descripcion, prioridad: v.prioridad, ruta })
				.then((r) => {
					d.hide();
					sgc.soporte.revisar(Object.assign({}, v, { ruta }), r.message);
				});
		},
	});
	if (valores) d.set_values(valores);
	d.show();
};

sgc.soporte.revisar = function (valores, ticket) {
	const e = frappe.utils.escape_html;
	// Un <div> con <br> y no un <pre>: Frappe pasa los <pre> por highlight.js, que
	// se come los saltos de línea y deja el contexto técnico en un solo renglón.
	const d = new frappe.ui.Dialog({
		title: __("Esto es lo que se enviará"),
		fields: [
			{
				fieldname: "vista",
				fieldtype: "HTML",
				options: `<p><b>${e(ticket.asunto)}</b> · ${__("Prioridad")}: ${e(ticket.prioridad)}</p>
					<div class="small" style="max-height: 320px; overflow: auto; padding: 8px 12px; border-radius: 6px; background: var(--subtle-fg)">${e(
						ticket.cuerpo
					).replace(/\n/g, "<br>")}</div>`,
			},
		],
		primary_action_label: __("Enviar"),
		primary_action() {
			frappe
				.call({
					method: "sgc.soporte.reportar",
					args: { asunto: valores.asunto, descripcion: valores.descripcion, prioridad: valores.prioridad, ruta: valores.ruta },
					freeze: true,
					freeze_message: __("Enviando al helpdesk…"),
				})
				.then((r) => {
					d.hide();
					const res = r.message || {};
					if (res.ok) {
						frappe.msgprint({
							title: __("Reporte enviado"),
							indicator: "green",
							message:
								res.proveedor === "Correo"
									? __("Su reporte se envió por correo a {0}.", [e(res.referencia)])
									: res.referencia
										? __("Su reporte llegó al helpdesk con la referencia {0}.", [e(res.referencia)])
										: __("Su reporte llegó al helpdesk."),
						});
					} else {
						sgc.soporte.alternativa(res);
					}
				});
		},
		secondary_action_label: __("Volver"),
		secondary_action() {
			d.hide();
			sgc.soporte.abrir(valores);
		},
	});
	d.show();
};

sgc.soporte.alternativa = function (res) {
	const e = frappe.utils.escape_html;
	const via = res.alternativa
		? __("Puede enviarlo por correo a {0}:", [`<a href="mailto:${e(res.alternativa)}">${e(res.alternativa)}</a>`])
		: __("Guárdelo y vuelva a intentarlo más tarde:");
	const d = new frappe.ui.Dialog({
		title: __("No se pudo enviar"),
		fields: [
			{ fieldname: "aviso", fieldtype: "HTML", options: `<p>${e(res.mensaje || "")}</p><p>${via}</p>` },
			{ fieldname: "texto", fieldtype: "Code", label: __("Su reporte"), read_only: 1, default: res.texto || "" },
		],
		primary_action_label: __("Copiar el texto"),
		primary_action() {
			frappe.utils.copy_to_clipboard(res.texto || "");
		},
	});
	d.show();
};
