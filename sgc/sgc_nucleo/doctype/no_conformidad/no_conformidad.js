// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// Análisis de causas (#34): la misma tabla, presentada según la metodología.
// Cinco porqués se lee por nivel; Ishikawa, por categoría; Pareto, por frecuencia
// de mayor a menor. Solo cambia el orden y las columnas que se ven: los datos
// son los mismos y la validación está en el servidor (no_conformidad.py).
const COLUMNA_POR_METODOLOGIA = {
	"Cinco porqués": "nivel",
	"Espina de pescado (Ishikawa)": "categoria",
	Pareto: "frecuencia",
};
const CATEGORIAS = ["Personas", "Método", "Material", "Máquina", "Medición", "Entorno"];

function presentar_causas(frm) {
	const campo_tabla = frm.fields_dict.causas;
	if (!campo_tabla || !campo_tabla.grid) return;
	const grid = campo_tabla.grid;
	const propia = COLUMNA_POR_METODOLOGIA[frm.doc.metodologia];

	// Se ve la columna de la metodología declarada; las de las otras, no.
	Object.values(COLUMNA_POR_METODOLOGIA).forEach((campo) => {
		grid.update_docfield_property(campo, "in_list_view", !propia || campo === propia ? 1 : 0);
	});

	const filas = (frm.doc.causas || []).slice();
	const orden = {
		"Cinco porqués": (a, b) => (a.nivel || 99) - (b.nivel || 99),
		"Espina de pescado (Ishikawa)": (a, b) =>
			CATEGORIAS.indexOf(a.categoria) - CATEGORIAS.indexOf(b.categoria),
		Pareto: (a, b) => (b.frecuencia || 0) - (a.frecuencia || 0),
	}[frm.doc.metodologia];
	if (orden && !frm.doc.__islocal && frm.doc.docstatus === 0) {
		filas.sort(orden).forEach((fila, i) => (fila.idx = i + 1));
		frm.doc.causas = filas;
	}
	grid.reset_grid();
	frm.refresh_field("causas");
}

frappe.ui.form.on("No Conformidad", {
	refresh: presentar_causas,
	metodologia: presentar_causas,
});
