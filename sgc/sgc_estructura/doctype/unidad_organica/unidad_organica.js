// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// La sede de una unidad es otra unidad, la de tipo «Sede» (#102): así cada institución
// declara sus sedes en su propio árbol en vez de traerlas fijas en el código.
frappe.ui.form.on("Unidad Organica", {
	setup(frm) {
		frm.set_query("sede", () => ({ filters: { tipo: "Sede" } }));
	},
});
