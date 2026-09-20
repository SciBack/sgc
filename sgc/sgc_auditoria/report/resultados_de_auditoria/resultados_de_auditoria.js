// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

frappe.query_reports['Resultados de Auditoria'] = {
	filters: [
		{ fieldname: 'auditoria', label: __('Auditoría'), fieldtype: 'Link', options: 'Auditoria' },
		{
			fieldname: 'tipo',
			label: __('Tipo de hallazgo'),
			fieldtype: 'Select',
			options: ['', 'No conformidad mayor', 'No conformidad menor', 'Observacion', 'Oportunidad de mejora'],
		},
		{ fieldname: 'proceso', label: __('Proceso'), fieldtype: 'Link', options: 'Proceso' },
		{
			// El filtro que convierte el informe en una lista de trabajo: no
			// conformidades documentadas que nunca se escalaron y, por tanto,
			// nunca se trataron.
			fieldname: 'solo_sin_escalar',
			label: __('Solo no conformidades sin escalar'),
			fieldtype: 'Check',
			default: 0,
		},
	],

	formatter(value, row, column, data, default_formatter) {
		const salida = default_formatter(value, row, column, data);
		if (column.fieldname === 'escalo' && data && data.escalo === __('PENDIENTE')) {
			return `<span style="color:var(--red-600);font-weight:600">${salida}</span>`;
		}
		return salida;
	},
};
