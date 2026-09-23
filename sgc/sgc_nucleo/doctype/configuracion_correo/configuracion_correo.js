// Configuracion Correo — estado visible y comprobación de destinatarios (#41)
frappe.ui.form.on("Configuracion Correo", {
	refresh(frm) {
		const lista = (frm.doc.lista_blanca || "").split("\n").filter(Boolean);
		if (frm.doc.modo !== "Real") {
			frm.set_intro(
				__(
					"Modo ensayo: ninguna regla envía correo. Lo que se habría enviado queda en el Registro Correo."
				),
				"orange"
			);
		} else if (lista.length) {
			frm.set_intro(
				__(
					"Envío real solo a la lista blanca ({0} direcciones). El resto queda registrado como omitido.",
					[lista.length]
				),
				"blue"
			);
		} else {
			frm.set_intro(__("Envío real a todos los destinatarios de cada regla."), "green");
		}

		frm.add_custom_button(__("Comprobar destinatarios"), () => mostrar_destinatarios());
		frm.add_custom_button(__("Registro Correo"), () =>
			frappe.set_route("List", "Registro Correo")
		);
	},
});

function mostrar_destinatarios() {
	const esc = (v) => frappe.utils.escape_html(v == null ? "" : String(v));

	frappe.call({ method: "sgc.correo.estado" }).then((r) => {
		const res = r.message || {};
		const hay_lista = (res.lista_blanca || []).length > 0;

		const filas = (res.reglas || [])
			.map((regla) => {
				const destinos = regla.destinos.length
					? regla.destinos
							.map((d) => {
								if (d.tipo !== "rol") {
									return `<li>${esc(d.tipo)}: <code>${esc(
										d.valor
									)}</code> — ${__("depende de cada documento")}</li>`;
								}
								const n = d.correos.length;
								const cuenta = n
									? __("{0} persona(s) con correo", [n])
									: `<b class="text-danger">${__(
											"nadie: este aviso no llegará"
									  )}</b>`;
								const blanca = hay_lista
									? ` · ${__("{0} en lista blanca", [d.en_lista_blanca.length])}`
									: "";
								return `<li>${__("rol")} <b>${esc(
									d.valor
								)}</b>: ${cuenta}${blanca}</li>`;
							})
							.join("")
					: `<li class="text-danger">${__("sin destinatarios")}</li>`;
				return `<p><b>${esc(regla.regla)}</b> <span class="text-muted">(${esc(
					regla.documento
				)})</span></p><ul>${destinos}</ul>`;
			})
			.join("");

		frappe.msgprint({
			title: __("Destinatarios de las reglas de correo"),
			indicator: (res.roles_vacios || []).length ? "red" : "green",
			message: filas || __("No hay reglas de notificación por correo activas."),
			wide: true,
		});
	});
}
