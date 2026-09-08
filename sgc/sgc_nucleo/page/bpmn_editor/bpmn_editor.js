// Editor BPMN embebido (Fase 1) — bpmn-js Modeler self-hosted en /assets/sgc/bpmn/.
// Se abre desde una ficha (botón «Editar BPMN»); carga sus .bpmn adjuntos, permite
// editar (mover cajas y flechas) y guarda el XML de vuelta como adjunto.
// Ver docs/decisiones/bpmn-herramientas.md (punto 2) y sgc/bpmn_editor.py.

frappe.pages['bpmn-editor'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Editor BPMN'),
		single_column: true,
	});
	new BpmnEditorPage(page, wrapper);
};

class BpmnEditorPage {
	constructor(page, wrapper) {
		this.page = page;
		this.$body = $(wrapper).find('.layout-main-section');
		this.modeler = null;
		this.filemap = {};
		this.current = null;
		this.sucio = false;
		this.render_shell();
		this.load_assets();
	}

	render_shell() {
		this.$body.empty().append(`
			<div class="bpmn-toolbar" style="margin-bottom:8px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
				<span class="bpmn-doc text-muted" style="font-size:12px;"></span>
				<select class="form-control bpmn-file-select" style="max-width:360px;height:28px;"></select>
				<button class="btn btn-default btn-xs bpmn-importar">${__('Importar .bpmn')}</button>
				<button class="btn btn-default btn-xs bpmn-descartar">${__('Descartar cambios')}</button>
				<span class="bpmn-status" style="margin-left:auto;font-size:12px;"></span>
			</div>
			<div class="bpmn-stage" style="display:flex;align-items:stretch;gap:8px;height:74vh;">
				<div class="bpmn-palette-host" style="flex:0 0 auto;display:flex;align-items:flex-start;padding:6px;border:1px solid var(--border-color);border-radius:6px;background:var(--fg-color);overflow:auto;"></div>
				<div class="bpmn-canvas" style="flex:1 1 auto;min-width:0;border:1px solid var(--border-color);border-radius:6px;background:#fff;"></div>
			</div>
		`);
		// La paleta de bpmn-js se dibuja flotando DENTRO del lienzo y no se puede mover:
		// tapa la esquina superior izquierda del diagrama, que es justo donde suele
		// empezar el flujo. Al sacarla a su propia columna deja de estorbar.
		this.$body.append(`
			<style>
				.bpmn-palette-host .djs-palette {
					position: static;
					border: none;
					background: transparent;
					box-shadow: none;
				}
			</style>
		`);
	}

	load_assets() {
		['/assets/sgc/bpmn/diagram-js.css', '/assets/sgc/bpmn/bpmn-js.css', '/assets/sgc/bpmn/bpmn-font.css']
			.forEach((href) => {
				if (!document.querySelector(`link[href="${href}"]`)) {
					$('<link rel="stylesheet" type="text/css">').attr('href', href).appendTo('head');
				}
			});
		frappe.require('/assets/sgc/bpmn/bpmn-modeler.js', () => this.init());
	}

	init() {
		const route = frappe.get_route(); // ['bpmn-editor', doctype, docname]
		this.doctype = route[1];
		this.docname = route[2];
		if (!this.doctype || !this.docname) {
			this.$body.html(
				`<div class="text-muted" style="padding:24px">${__('Abre el editor desde una ficha, con el botón «Editar BPMN».')}</div>`
			);
			return;
		}
		this.$body.find('.bpmn-doc').text(`${this.doctype}: ${this.docname}`);
		this.modeler = new BpmnJS({ container: this.$body.find('.bpmn-canvas')[0] });
		this.desacoplar_paleta();

		this.page.set_primary_action(__('Guardar'), () => this.save(), 'octicon octicon-check');
		this.page.set_secondary_action(__('Descargar .bpmn'), () => this.download());
		this.page.add_menu_item(__('Ajustar a pantalla'), () => this.fit());

		this.$body.find('.bpmn-file-select').on('change', (e) => this.open($(e.target).val()));
		this.$body.find('.bpmn-importar').on('click', () => this.importar());
		this.$body.find('.bpmn-descartar').on('click', () => this.descartar());
		// Todo cambio en el lienzo pasa por el commandStack, incluido deshacer y rehacer.
		this.modeler.on('commandStack.changed', () => this.marcar_sucio(true));
		this.load_list();
	}

	load_list() {
		frappe
			.call('sgc.bpmn_editor.listar_bpmn', { doctype: this.doctype, docname: this.docname })
			.then((r) => {
				const files = r.message || [];
				const $sel = this.$body.find('.bpmn-file-select').empty();
				this.filemap = {};
				if (!files.length) {
					$sel.append(`<option>${__('(sin .bpmn adjuntos)')}</option>`);
					this.status(__('Adjunta un archivo .bpmn a la ficha para poder editarlo.'), 'var(--orange-600)');
					return;
				}
				files.forEach((f) => {
					this.filemap[f.file_url] = f.file_name;
					$sel.append(`<option value="${f.file_url}">${frappe.utils.escape_html(f.file_name)}</option>`);
				});
				this.open(files[0].file_url);
			});
	}

	open(file_url) {
		if (!file_url || !this.filemap[file_url]) return;
		this.current = { file_url, file_name: this.filemap[file_url] };
		fetch(file_url, { credentials: 'same-origin' })
			.then((r) => r.text())
			.then((xml) => this.modeler.importXML(xml))
			.then(() => {
				this.fit();
				// La importación mueve el commandStack: el flag se limpia después, no antes.
				this.marcar_sucio(false);
				this.status(`${__('Cargado')}: ${this.current.file_name}`, 'var(--green-600)');
			})
			.catch((e) => this.status(`${__('Error al cargar')}: ${e.message}`, 'var(--red-600)'));
	}

	desacoplar_paleta() {
		// bpmn-js monta la paleta en el contenedor del canvas (`_getParentContainer()`
		// devuelve el del canvas y no admite configuración), así que se mueve el nodo
		// una vez creada. Los manejadores viven en el propio elemento y se conservan.
		const paleta = this.$body.find('.bpmn-canvas .djs-palette')[0];
		if (!paleta) return;
		this.$body.find('.bpmn-palette-host')[0].appendChild(paleta);
	}

	importar() {
		// Cierra el viaje de ida y vuelta con Bizagi u otro editor de escritorio:
		// «Descargar .bpmn» saca el diagrama y esto lo devuelve. Solo lo carga en
		// pantalla; persistirlo sigue siendo un acto explícito con «Guardar».
		const input = document.createElement('input');
		input.type = 'file';
		input.accept = '.bpmn,.xml,application/xml,text/xml';
		input.addEventListener('change', () => {
			const archivo = input.files && input.files[0];
			if (!archivo) return;
			archivo
				.text()
				.then((xml) => this.modeler.importXML(xml))
				.then(() => {
					this.fit();
					this.status(
						`${__('Importado')}: ${archivo.name} — ${__('pulse «Guardar» para conservarlo')}`,
						'var(--orange-600)'
					);
				})
				.catch((e) => this.status(`${__('Error al importar')}: ${e.message}`, 'var(--red-600)'));
		});
		input.click();
	}

	descartar() {
		// Volver al último guardado. El editor no tiene «deshacer todo» a la vista, y sin
		// esto la única forma de arrepentirse era abandonar la página y confiar en que
		// nada se hubiera escrito.
		if (!this.current) {
			frappe.msgprint(__('No hay diagrama abierto.'));
			return;
		}
		if (!this.sucio) {
			this.status(__('No hay cambios que descartar.'));
			return;
		}
		frappe.confirm(
			__('Se perderán los cambios que no haya guardado. ¿Volver al último diagrama guardado?'),
			() => this.open(this.current.file_url)
		);
	}

	marcar_sucio(sucio) {
		this.sucio = sucio;
		this.$body.find('.bpmn-descartar').toggleClass('btn-warning', sucio);
		if (sucio) {
			this.status(__('Cambios sin guardar'), 'var(--orange-600)');
		}
	}

	fit() {
		try {
			this.modeler.get('canvas').zoom('fit-viewport');
		} catch (e) {
			/* noop */
		}
	}

	save() {
		if (!this.current) {
			frappe.msgprint(__('No hay diagrama abierto.'));
			return;
		}
		this.modeler
			.saveXML({ format: true })
			.then(({ xml }) =>
				frappe.call('sgc.bpmn_editor.guardar_bpmn', {
					doctype: this.doctype,
					docname: this.docname,
					file_name: this.current.file_name,
					xml,
				})
			)
			.then((r) => {
				if (r.message && r.message.ok) {
					this.current.file_url = r.message.file_url;
					frappe.show_alert({ message: __('BPMN guardado'), indicator: 'green' });
					this.marcar_sucio(false);
					this.status(`${__('Guardado')}: ${this.current.file_name}`, 'var(--green-600)');
				}
			})
			.catch((e) => this.status(`${__('Error al guardar')}: ${e.message}`, 'var(--red-600)'));
	}

	download() {
		if (!this.current) return;
		this.modeler.saveXML({ format: true }).then(({ xml }) => {
			const blob = new Blob([xml], { type: 'application/xml' });
			const a = document.createElement('a');
			a.href = URL.createObjectURL(blob);
			a.download = this.current.file_name;
			a.click();
			URL.revokeObjectURL(a.href);
		});
	}

	status(msg, color) {
		this.$body.find('.bpmn-status').text(msg).css('color', color || '');
	}
}
