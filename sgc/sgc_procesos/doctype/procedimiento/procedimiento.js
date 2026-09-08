// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

frappe.ui.form.on("Procedimiento", {
	refresh(frm) {
		if (frm.is_new()) return;

		// El BPMN adjunto se dibuja dentro del propio formulario: el diagrama es la
		// forma natural de leer un procedimiento, y un .bpmn suelto solo se puede
		// descargar. Ver sgc/public/bpmn/visor.js.
		frappe.require("/assets/sgc/bpmn/visor.js", () => sgc.bpmn.montar(frm, "visor_bpmn"));

		// Editar sí queda detrás de un botón: abre el modeler completo, que escribe
		// sobre el adjunto.
		frm.add_custom_button(__("Editar BPMN"), () => {
			frappe.set_route("bpmn-editor", frm.doc.doctype, frm.doc.name);
		});
	},
});
