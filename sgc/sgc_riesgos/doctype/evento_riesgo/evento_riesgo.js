// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// Reporte de evento de riesgo: lo escribe cualquier colaborador y lo decide Calidad.
// Las transiciones las pinta el workflow «Evento Riesgo SGC»; aquí solo se explica
// en qué punto está el reporte a quien lo mira.
frappe.ui.form.on("Evento Riesgo", {
	refresh(frm) {
		if (frm.is_new()) {
			frm.set_intro(
				__("Cuente qué pasó. Calidad lo evaluará y le avisará por correo de lo que decida."),
				"blue"
			);
			return;
		}
		if (frm.doc.estado === "Confirmado" && frm.doc.no_conformidad) {
			frm.set_intro(
				__("Confirmado. El análisis de causas y el plan de acción se hacen en la no conformidad {0}.", [
					`<a href="/desk/no-conformidad/${encodeURIComponent(frm.doc.no_conformidad)}">${frappe.utils.escape_html(frm.doc.no_conformidad)}</a>`,
				]),
				"green"
			);
		} else if (frm.doc.estado === "Descartado") {
			frm.set_intro(__("Descartado: {0}", [frappe.utils.escape_html(frm.doc.motivo_descarte || "")]), "orange");
		} else {
			frm.set_intro(__("Pendiente de la evaluación de Calidad."), "blue");
		}
		if (["Confirmado", "Descartado"].includes(frm.doc.estado)) {
			// Lo decidido no se reescribe: el servidor lo impide y la pantalla no lo ofrece.
			frm.disable_save();
			frm.set_read_only();
		}
	},
});
