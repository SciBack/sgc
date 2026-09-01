// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

frappe.ui.form.on("Ficha Caracterizacion Proceso", {
	refresh(frm) {
		if (frm.is_new()) return;
		// Editor BPMN embebido (Fase 1): abre la página bpmn-editor con esta ficha,
		// que carga sus .bpmn adjuntos para verlos y editarlos. Ver sgc/bpmn_editor.py.
		frm.add_custom_button(__("Editar BPMN"), () => {
			frappe.set_route("bpmn-editor", frm.doc.doctype, frm.doc.name);
		});
	},
});
