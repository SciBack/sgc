// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// Confirmar la lectura de un documento (ver sgc/acuses.py).
//
// El diálogo pide las preguntas al servidor SIN las respuestas correctas y le manda lo que
// marcó la persona; la nota la pone el servidor. Si el documento no trae preguntas, basta
// con la declaración.

frappe.ui.form.on("Acuse Lectura", {
	refresh(frm) {
		if (frm.doc.documento) {
			frm.add_custom_button(__("Abrir el documento"), () =>
				frappe.set_route("Form", "Documento Controlado", frm.doc.documento)
			);
		}
		if (frm.doc.estado === "Pendiente" && frm.doc.usuario === frappe.session.user) {
			frm.add_custom_button(__("Confirmar lectura"), () => confirmar_lectura(frm)).addClass(
				"btn-primary"
			);
		}
	},
});

function confirmar_lectura(frm) {
	frappe.call("sgc.acuses.preguntas", { acuse: frm.doc.name }).then((r) => {
		const datos = r.message;
		const esc = frappe.utils.escape_html;
		const campos = [
			{
				fieldtype: "HTML",
				options: `<p>${esc(datos.titulo)} · ${__("versión {0}", [datos.version])}</p>`,
			},
		];
		datos.preguntas.forEach((p) => {
			campos.push({
				fieldname: `p${p.idx}`,
				fieldtype: "Select",
				label: esc(p.pregunta),
				reqd: 1,
				options: [""].concat(
					p.opciones.map(([letra, texto]) => ({ value: letra, label: `${letra}) ${esc(texto)}` }))
				),
			});
		});
		if (datos.preguntas.length) {
			campos.push({
				fieldtype: "HTML",
				options: `<p class="text-muted">${__("Hace falta acertar el {0} % de las preguntas.", [
					datos.nota_minima,
				])}</p>`,
			});
		}
		campos.push({
			fieldname: "declaro",
			fieldtype: "Check",
			label: __("He leído y entendido este documento"),
		});

		const dialogo = new frappe.ui.Dialog({
			title: __("Confirmar lectura"),
			fields: campos,
			primary_action_label: __("Confirmar"),
			primary_action(valores) {
				if (!valores.declaro) {
					frappe.msgprint(__("Marque la declaración de que leyó y entendió el documento."));
					return;
				}
				const respuestas = {};
				datos.preguntas.forEach((p) => (respuestas[p.idx] = valores[`p${p.idx}`]));
				frappe
					.call("sgc.acuses.acusar", { acuse: frm.doc.name, respuestas, declaro: 1 })
					.then((res) => {
						dialogo.hide();
						const m = res.message;
						if (m.aprobado) {
							frappe.show_alert({ message: __("Lectura confirmada"), indicator: "green" });
						} else {
							frappe.msgprint(
								__(
									"Acertó {0} de {1} preguntas ({2} %) y hace falta el {3} %. Vuelva a leer el documento e inténtelo de nuevo.",
									[m.aciertos, m.total, m.puntaje, m.nota_minima]
								)
							);
						}
						frm.reload_doc();
					});
			},
		});
		dialogo.show();
	});
}
