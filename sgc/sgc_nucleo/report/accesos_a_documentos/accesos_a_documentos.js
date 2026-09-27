// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

frappe.query_reports['Accesos a Documentos'] = {
	filters: [
		{
			fieldname: 'documento',
			label: __('Documento'),
			fieldtype: 'Link',
			options: 'Documento Controlado',
		},
		{
			fieldname: 'usuario',
			label: __('Usuario'),
			fieldtype: 'Link',
			options: 'User',
		},
		{
			fieldname: 'desde',
			label: __('Desde'),
			fieldtype: 'Date',
		},
		{
			fieldname: 'hasta',
			label: __('Hasta'),
			fieldtype: 'Date',
		},
	],
};
