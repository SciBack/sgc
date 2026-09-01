// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

(() => {
	const NIVELES_PROCESO = Object.freeze({
		N0: { label: "N0", color: "blue" },
		N1: { label: "N1", color: "green" },
		N2: { label: "N2", color: "orange" },
		N3: { label: "N3", color: "purple" },
		N4: { label: "N4", color: "gray" },
	});

	const DOCTYPES_ABRIBLES = Object.freeze(["Proceso", "Procedimiento"]);

	function escape(value) {
		return frappe.utils.escape_html(String(value ?? ""));
	}

	function puede_abrir_nodo(node) {
		return (
			!node.is_root &&
			DOCTYPES_ABRIBLES.includes(node.data.doctype) &&
			Boolean(node.data.docname)
		);
	}

	frappe.treeview_settings["Proceso"] = {
		title: __("Mapa de procesos"),
		get_tree_nodes: "sgc.sgc_procesos.doctype.proceso.proceso_tree.get_children",
		disable_add_node: true,
		toolbar: [
			{
				label: __("Abrir"),
				condition(node) {
					return puede_abrir_nodo(node);
				},
				click(node) {
					const { doctype, docname } = node.data;
					if (!DOCTYPES_ABRIBLES.includes(doctype) || !docname) return;
					frappe.set_route("Form", doctype, docname);
				},
			},
		],
		get_label(node) {
			if (node.is_root) return escape(__("Mapa de procesos"));

			const data = node.data || {};
			const nivel = NIVELES_PROCESO[data.node_type];
			const identificador =
				data.node_type === "N4" ? escape(data.bpmn_id) : escape(data.docname);
			const titulo = escape(node.title);
			const badge = nivel
				? `<span class="indicator-pill ${nivel.color}">${nivel.label}</span>`
				: "";

			return `${badge} <span class="text-muted">${identificador}</span> <span>${titulo}</span>`;
		},
	};
})();
