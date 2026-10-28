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

	// Nodo de un proceso real (N0-N2), no una familia ni un procedimiento o una tarea.
	function es_proceso(node) {
		return !node.is_root && node.data.doctype === "Proceso" && ["N0", "N1", "N2"].includes(node.data.node_type);
	}

	function es_procedimiento(node) {
		return !node.is_root && node.data.node_type === "N3" && Boolean(node.data.docname);
	}

	const COLOR_ESTADO = Object.freeze({
		Vigente: "green",
		Publicado: "green",
		Aprobado: "green",
		"En revisión": "orange",
		Borrador: "gray",
		Obsoleto: "gray",
	});

	function pildora(texto, color) {
		return `<span class="indicator-pill ${color || "gray"}">${escape(__(texto))}</span>`;
	}

	// Lo que hace falta para trabajar cada nodo, junto a su nombre, como el saldo de cada cuenta en el
	// árbol del plan de cuentas de ERPNext (account_tree.js): estado, responsable, ficha y
	// procedimientos. Lo que falta sale en rojo para que se vea sin abrir nada.
	function datos_de_trabajo(data) {
		const partes = [];
		if (data.estado) partes.push(pildora(data.estado, COLOR_ESTADO[data.estado]));
		if (data.doctype === "Proceso") {
			partes.push(
				data.responsable
					? `<span class="text-muted">${escape(data.responsable_nombre || data.responsable)}</span>`
					: `<span class="text-danger">${escape(__("Sin responsable"))}</span>`
			);
			partes.push(
				data.ficha
					? `<span class="text-muted">${escape(__("Ficha"))}: ${escape(__(data.ficha_estado || ""))}</span>`
					: `<span class="text-muted">${escape(__("Sin ficha"))}</span>`
			);
			if (data.procedimientos) {
				partes.push(
					`<span class="text-muted">${escape(__("{0} proced.", [data.procedimientos]))}</span>`
				);
			}
		}
		if (!partes.length) return "";
		return `<span class="small" style="display:inline-flex;gap:0.75rem;align-items:center;margin-left:1rem">${partes.join("")}</span>`;
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
			// Las versiones del cuadro aprobado (cargar una nueva, consultar las obsoletas) no tienen
			// entrada propia en el menú del área: se abren desde aquí.
			{
				label: __("Versiones del mapa institucional"),
				action() {
					frappe.set_route("List", "Mapa Procesos");
				},
				// treeview.js evalúa la condición de menu_items como TEXTO (eval).
				condition: 'frappe.model.can_read("Mapa Procesos")',
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
			// La ficha es una por proceso: se abre si existe y, si no, se crea ya enlazada.
			{
				label: __("Ficha"),
				condition(node) {
					return es_proceso(node) && (Boolean(node.data.ficha) || frappe.model.can_create("Ficha Caracterizacion Proceso"));
				},
				click(node) {
					if (node.data.ficha) {
						frappe.set_route("Form", "Ficha Caracterizacion Proceso", node.data.ficha);
					} else {
						frappe.new_doc("Ficha Caracterizacion Proceso", { proceso: node.data.docname });
					}
				},
			},
			{
				label: __("Nuevo subproceso"),
				condition(node) {
					return es_proceso(node) && node.data.node_type !== "N2" && frappe.model.can_create("Proceso");
				},
				click(node) {
					frappe.new_doc("Proceso", { parent_proceso: node.data.docname });
				},
			},
			{
				label: __("Nuevo procedimiento"),
				condition(node) {
					return es_proceso(node) && frappe.model.can_create("Procedimiento");
				},
				click(node) {
					frappe.new_doc("Procedimiento", { proceso: node.data.docname });
				},
			},
			{
				label: __("Editar diagrama"),
				condition(node) {
					return es_procedimiento(node) && frappe.model.can_write("Procedimiento");
				},
				click(node) {
					frappe.set_route("bpmn-editor", "Procedimiento", node.data.docname);
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

			return `${badge} <span class="text-muted">${identificador}</span> <span>${titulo}</span>${datos_de_trabajo(data)}`;
		},
	};
})();
