// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// «¿Qué acción ataca esta causa?» (#34). La causa se elige entre las de la no
// conformidad de la acción; el servidor rechaza una causa de otra NC.
frappe.ui.form.on("Accion Mejora", {
	refresh(frm) {
		if (!frm.doc.no_conformidad || frm.doc.docstatus !== 0) return;
		frm.add_custom_button(__("Elegir causa"), () => elegir_causa(frm));
	},
	no_conformidad(frm) {
		// Una causa solo tiene sentido dentro de su no conformidad.
		frm.set_value("causa", null);
		frm.set_value("causa_descripcion", null);
	},
});

function elegir_causa(frm) {
	frappe.db.get_doc("No Conformidad", frm.doc.no_conformidad).then((nc) => {
		const causas = nc.causas || [];
		if (!causas.length) {
			frappe.msgprint(__("La no conformidad {0} no tiene causas identificadas todavía.", [nc.name]));
			return;
		}
		const etiqueta = (c) => `${c.idx}. ${c.es_causa_raiz ? __("(raíz) ") : ""}${c.descripcion}`;
		const por_etiqueta = Object.fromEntries(causas.map((c) => [etiqueta(c), c.name]));
		frappe.prompt(
			{
				fieldname: "causa",
				fieldtype: "Select",
				label: __("Causa que ataca esta acción"),
				options: Object.keys(por_etiqueta).join("\n"),
				reqd: 1,
			},
			(valores) => {
				frm.set_value("causa", por_etiqueta[valores.causa]);
				frm.set_value(
					"causa_descripcion",
					(causas.find((c) => c.name === por_etiqueta[valores.causa]) || {}).descripcion
				);
			},
			__("Elegir causa"),
			__("Elegir")
		);
	});
}
