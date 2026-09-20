// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

frappe.query_reports['Mejoramiento Continuo'] = {
	filters: [
		{
			fieldname: 'solo_pendientes',
			label: __('Solo pendientes'),
			fieldtype: 'Check',
			// Por defecto encendido: al abrir el informe interesa lo que queda por
			// hacer, no el histórico completo. Quien quiera el histórico lo apaga.
			default: 1,
		},
		{
			fieldname: 'tipo',
			label: __('Tipo'),
			fieldtype: 'Select',
			options: ['', 'Correctiva', 'Preventiva', 'Mejora'],
		},
		{
			fieldname: 'responsable',
			label: __('Responsable'),
			fieldtype: 'Link',
			options: 'User',
		},
		{
			fieldname: 'plan_mejora',
			label: __('Plan de mejora'),
			fieldtype: 'Link',
			options: 'Plan Mejora',
		},
	],

	formatter(value, row, column, data, default_formatter) {
		const salida = default_formatter(value, row, column, data);
		// El retraso es lo único que se resalta: si todo grita, nada se oye.
		if (column.fieldname === 'dias_retraso' && data && data.dias_retraso) {
			const color = data.dias_retraso > 30 ? 'var(--red-600)' : 'var(--orange-600)';
			return `<span style="color:${color};font-weight:600">${salida}</span>`;
		}
		return salida;
	},
};
