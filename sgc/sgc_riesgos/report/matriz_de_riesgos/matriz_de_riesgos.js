// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

frappe.query_reports['Matriz de Riesgos'] = {
	filters: [
		{
			fieldname: 'categoria',
			label: __('Categoría'),
			fieldtype: 'Select',
			options: ['', 'Estrategico', 'Operacional', 'Cumplimiento', 'Financiero', 'Reputacional', 'Seguridad'],
		},
		{ fieldname: 'proceso', label: __('Proceso'), fieldtype: 'Link', options: 'Proceso' },
		{
			fieldname: 'solo_altos',
			label: __('Solo Alto y Extremo'),
			fieldtype: 'Check',
			default: 0,
		},
	],

	formatter(value, row, column, data, default_formatter) {
		const salida = default_formatter(value, row, column, data);
		// Las dos señales que el informe existe para hacer visibles.
		if (column.fieldname === 'efecto' && data) {
			if (data.efecto === __('SIN TRATAMIENTO') || data.efecto === __('NO BAJÓ')) {
				return `<span style="color:var(--red-600);font-weight:600">${salida}</span>`;
			}
		}
		return salida;
	},
};
