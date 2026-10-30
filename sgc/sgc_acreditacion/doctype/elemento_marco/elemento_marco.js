// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

frappe.ui.form.on("Elemento Marco", {
	setup(frm) {
		// El elemento padre, solo del mismo marco: hay 10 marcos y sus elementos no se mezclan.
		frm.set_query("parent_elemento_marco", () =>
			frm.doc.marco_normativo ? { filters: { marco_normativo: frm.doc.marco_normativo } } : {}
		);
	},
});
