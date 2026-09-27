// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

frappe.query_reports['Salidas No Conformes'] = {
	filters: [
		{
			fieldname: 'desde',
			label: __('Detectadas desde'),
			fieldtype: 'Date',
		},
		{
			fieldname: 'hasta',
			label: __('Hasta'),
			fieldtype: 'Date',
		},
		{
			fieldname: 'proceso',
			label: __('Proceso'),
			fieldtype: 'Link',
			options: 'Proceso',
		},
		{
			fieldname: 'origen',
			label: __('Origen'),
			fieldtype: 'Select',
			options: ['', 'Interno', 'Reclamo de usuario', 'Auditoria', 'Proveedor externo'],
		},
		{
			fieldname: 'decision',
			label: __('Decisión'),
			fieldtype: 'Select',
			options: ['', 'Corregir', 'Autorizar bajo concesion', 'Suspender la entrega', 'Retirar lo entregado'],
		},
	],
};
