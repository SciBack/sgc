// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

frappe.query_reports['Indicadores de Acreditacion'] = {
	filters: [
		{
			// Sin valor por defecto en el código: se toma el productor que la institución
			// haya declarado (`sgc_fuente_indicadores`), para no atar el canónico al
			// nombre que le da un cliente al suyo.
			fieldname: 'fuente',
			label: __('Fuente'),
			fieldtype: 'Data',
			default: frappe.defaults.get_default('sgc_fuente_indicadores') || '',
		},
		{
			fieldname: 'periodo_academico',
			label: __('Periodo'),
			fieldtype: 'Link',
			options: 'Periodo Academico',
		},
		{
			fieldname: 'programa_sede',
			label: __('Programa / Sede'),
			fieldtype: 'Link',
			options: 'Programa Sede',
		},
		{
			fieldname: 'indicador',
			label: __('Indicador'),
			fieldtype: 'Link',
			options: 'Indicador',
		},
		{
			fieldname: 'solo_incumplidos',
			label: __('Solo los que no cumplen'),
			fieldtype: 'Check',
			default: 0,
		},
	],

	formatter(valor, fila, columna, dato, por_defecto) {
		const html = por_defecto(valor, fila, columna, dato);
		// El incumplimiento tiene que verse de un vistazo: es lo que dispara una acción
		// de mejora. El "—" (el productor no se pronuncia) NO se pinta de rojo.
		if (columna.fieldname === 'cumple') {
			if (valor === __('No')) return `<span style="color:var(--red-600);font-weight:600">${html}</span>`;
			if (valor === __('Sí')) return `<span style="color:var(--green-600)">${html}</span>`;
		}
		return html;
	},
};
