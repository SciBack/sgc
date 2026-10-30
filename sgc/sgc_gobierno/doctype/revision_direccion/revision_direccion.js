// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// «Obtener entradas de…» trae a la revisión, como entradas del §9.3.2, los registros que ya
// están en el SGC (no conformidades, informes de auditoría, mediciones, encuestas, riesgos y la
// revisión anterior), enlazados a su fuente. Es el diálogo nativo de Frappe que ERPNext usa
// para «Obtener artículos de» (`frappe.ui.form.MultiSelectDialog`). El servidor
// (`agregar_entradas`) decide el inciso de cada uno y no repite fuentes.
//
// «Consolidar salidas» siembra las salidas obligatorias del §9.3.3 que falten a partir de las
// entradas. El método existía y no tenía botón.
(() => {
	const FUENTES = [
		{ doctype: "No Conformidad", label: __("No conformidades") },
		{
			doctype: "Informe Auditoria",
			label: __("Informes de auditoría"),
			filters: { estado: ["in", ["Aprobado", "Distribuido"]] },
		},
		{ doctype: "Valor Indicador", label: __("Mediciones de indicador") },
		{ doctype: "Resultado Instrumento", label: __("Resultados de encuestas") },
		{ doctype: "Evaluacion Riesgo", label: __("Evaluaciones de riesgo") },
		{ doctype: "Revision Direccion", label: __("Revisión anterior"), anterior: true },
	];

	function obtener(frm, fuente) {
		new frappe.ui.form.MultiSelectDialog({
			doctype: fuente.doctype,
			target: frm,
			setters: {},
			primary_action_label: __("Añadir como entradas"),
			get_query() {
				const filters = { ...(fuente.filters || {}) };
				if (fuente.anterior) filters.name = ["!=", frm.doc.name];
				return { filters };
			},
			action(seleccion) {
				if (!seleccion || !seleccion.length) return;
				frm.call("agregar_entradas", {
					fuente_doctype: fuente.doctype,
					nombres: seleccion,
				}).then((r) => {
					this.dialog.hide();
					frappe.show_alert({
						message: r.message
							? __("{0} entradas añadidas", [r.message])
							: __("Ya estaban todas"),
						indicator: r.message ? "green" : "blue",
					});
					frm.reload_doc();
				});
			},
		});
	}

	frappe.ui.form.on("Revision Direccion", {
		refresh(frm) {
			if (frm.is_new() || frm.doc.estado === "Cerrada" || !frm.perm[0]?.write) return;

			FUENTES.forEach((fuente) => {
				frm.add_custom_button(fuente.label, () => obtener(frm, fuente), __("Obtener entradas de"));
			});

			frm.add_custom_button(__("Consolidar salidas"), () => {
				frm.call("consolidar_salidas").then((r) => {
					frappe.show_alert({
						message: r.message
							? __("{0} salidas añadidas", [r.message])
							: __("Ya estaban las tres salidas obligatorias"),
						indicator: r.message ? "green" : "blue",
					});
					frm.reload_doc();
				});
			});
		},
	});
})();
