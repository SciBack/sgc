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

	// El cuadro institucional: la lámina aprobada, que vive en `Mapa Procesos`.
	// Se abre desde aquí y no desde su lista porque esta pantalla es donde la
	// gente va a buscar "el mapa"; la lista es para administrarlo.
	function mostrar_mapa_institucional() {
		frappe.call({
			method: "sgc.sgc_procesos.doctype.mapa_procesos.mapa_procesos.mapa_vigente",
			callback(r) {
				const mapa = r.message || {};
				if (!mapa.hay_mapa) {
					frappe.msgprint({
						title: __("Sin mapa institucional"),
						indicator: "orange",
						message: __(
							"Todavía no hay ninguna versión del cuadro marcada como vigente. Se carga en {0}.",
							[
								`<a href="/app/mapa-procesos">${escape(
									__("Mapa Procesos")
								)}</a>`,
							]
						),
					});
					return;
				}
				frappe.msgprint({
					title: escape(mapa.titulo || __("Mapa de procesos institucional")),
					indicator: mapa.desfasado ? "orange" : "green",
					message: cuerpo_mapa(mapa),
					wide: true,
				});
			},
		});
	}

	function cuerpo_mapa(mapa) {
		const partes = [];

		if (mapa.desfasado) {
			// No bloquea: un mapa aprobado sigue siendo el aprobado. Solo deja de
			// ser invisible que el árbol ha seguido avanzando por debajo.
			partes.push(
				`<div class="alert alert-warning">${__(
					"El árbol de procesos ha cambiado después de aprobarse este cuadro ({0}). Puede estar desfasado.",
					[escape(frappe.datetime.str_to_user(mapa.ultimo_cambio_arbol))]
				)}</div>`
			);
		}

		if (mapa.imagen) {
			partes.push(
				`<img src="${escape(
					mapa.imagen
				)}" style="max-width:100%" alt="${escape(
					mapa.titulo || __("Mapa de procesos")
				)}">`
			);
		}

		const ficha = [
			[__("Versión"), mapa.version],
			[__("Aprobado el"), frappe.datetime.str_to_user(mapa.fecha_aprobacion)],
			[__("Aprobado por"), mapa.aprobado_por],
			[__("Resolución"), mapa.resolucion],
		]
			.filter(([, valor]) => valor)
			.map(([etiqueta, valor]) => `<b>${escape(etiqueta)}:</b> ${escape(valor)}`)
			.join(" · ");

		if (ficha) partes.push(`<p class="text-muted mt-3">${ficha}</p>`);

		return partes.join("");
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
		menu_items: [
			{
				label: __("Mapa institucional"),
				action: mostrar_mapa_institucional,
			},
		],
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

			// Familia (Estratégicos / Clave / Soporte): es agrupación, no documento.
			// No lleva píldora de nivel —dentro de ella todos son N0, así que decirlo
			// en cada fila es ruido— sino el nombre y cuántos macroprocesos agrupa.
			if (data.node_type === "FAM") {
				const total = Number.isFinite(data.total) ? data.total : null;
				const cuenta =
					total === null ? "" : ` <span class="text-muted">${total}</span>`;
				return `<span class="font-weight-bold">${escape(node.title)}</span>${cuenta}`;
			}

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
