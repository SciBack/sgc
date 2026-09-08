// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

frappe.ui.form.on("Ficha Caracterizacion Proceso", {
	refresh(frm) {
		if (frm.is_new()) return;

		// Los .bpmn adjuntos se dibujan dentro de la ficha (sección «Diagrama BPMN»),
		// sin tener que salir a otra página para verlos. Ver sgc/public/bpmn/visor.js.
		frappe.require("/assets/sgc/bpmn/visor.js", () => sgc.bpmn.montar(frm, "visor_bpmn"));

		// Editor BPMN embebido (Fase 1): abre la página bpmn-editor con esta ficha,
		// que carga sus .bpmn adjuntos para editarlos. Ver sgc/bpmn_editor.py.
		frm.add_custom_button(__("Editar BPMN"), () => {
			frappe.set_route("bpmn-editor", frm.doc.doctype, frm.doc.name);
		});
	},
});
