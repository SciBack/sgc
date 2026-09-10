// Visor BPMN embebido en el formulario — solo lectura.
//
// Dibuja los .bpmn adjuntos a un documento dentro de su propio formulario, para que el
// diagrama se vea al abrirlo sin pulsar nada. Editar sigue estando detrás del botón
// «Editar BPMN», que abre la página `bpmn-editor` (ver sgc/bpmn_editor.py).
//
// Reutiliza el bundle `bpmn-modeler.js` que ya se sirve para el editor —el mismo asset,
// ya cacheado— y le desactiva la edición: bpmn-js expone el Modeler como `BpmnJS`, no el
// NavigatedViewer, así que se cancelan los eventos de edición con un listener de máxima
// prioridad y se oculta la paleta. Queda el navegado (zoom y desplazamiento), que es lo
// que se quiere para consultar. Nada de lo que haga el usuario aquí se guarda.

frappe.provide("sgc.bpmn");

sgc.bpmn.ASSETS_CSS = [
	"/assets/sgc/bpmn/diagram-js.css",
	"/assets/sgc/bpmn/bpmn-js.css",
	"/assets/sgc/bpmn/bpmn-font.css",
];

// Eventos que introducen o mueven elementos. Cancelarlos deja el diagrama inmutable.
sgc.bpmn.EVENTOS_EDICION = [
	"shape.move.start",
	"connect.start",
	"drag.init",
	"create.start",
	"contextPad.open",
	"palette.open",
	"element.dblclick",
	"directEditing.activate",
];

sgc.bpmn.cargar_css = function () {
	sgc.bpmn.ASSETS_CSS.forEach((href) => {
		if (!document.querySelector(`link[href="${href}"]`)) {
			$('<link rel="stylesheet" type="text/css">').attr("href", href).appendTo("head");
		}
	});
};

/**
 * Monta el visor en un campo HTML del formulario.
 *
 * @param {object} frm        formulario Frappe
 * @param {string} fieldname  campo HTML donde dibujar
 */
sgc.bpmn.montar = function (frm, fieldname) {
	const campo = frm.get_field(fieldname);
	if (!campo || frm.is_new()) return;
	const $wrapper = $(campo.wrapper).empty();

	frappe
		.call({
			method: "sgc.bpmn_editor.listar_bpmn",
			args: { doctype: frm.doc.doctype, docname: frm.doc.name },
		})
		.then((r) => {
			const archivos = (r && r.message) || [];
			if (!archivos.length) return; // sin diagrama: el campo no ocupa espacio
			sgc.bpmn.cargar_css();
			$wrapper.append(`
				<div class="sgc-bpmn-barra" style="display:flex;gap:8px;align-items:center;margin-bottom:6px;">
					<select class="form-control sgc-bpmn-sel" style="max-width:340px;height:28px;${
						archivos.length > 1 ? "" : "display:none;"
					}"></select>
					<span class="text-muted" style="font-size:11px;margin-left:auto;">${__(
						"Solo lectura — use «Editar BPMN» para modificarlo"
					)}</span>
				</div>
				<div class="sgc-bpmn-lienzo" style="height:460px;border:1px solid var(--border-color);border-radius:6px;background:#fff;"></div>
				<div class="sgc-bpmn-tareas" style="margin-top:12px;"></div>
			`);
			const $sel = $wrapper.find(".sgc-bpmn-sel");
			sgc.bpmn._versiones = {};
			archivos.forEach((a) => {
				sgc.bpmn._versiones[a.file_url] = a.version;
				$sel.append(
					`<option value="${a.file_url}">${frappe.utils.escape_html(a.file_name)}</option>`
				);
			});
			frappe.require("/assets/sgc/bpmn/bpmn-modeler.js", () => {
				const pintar = (url) => {
					sgc.bpmn._render($wrapper, url);
					sgc.bpmn._tareas($wrapper, frm, url);
				};
				pintar($sel.val());
				$sel.on("change", () => pintar($sel.val()));
			});
		});
};

// `zoom("fit-viewport")` divide por el tamaño del contenedor: si el formulario aún no
// terminó de dibujarse, o el campo está en una pestaña o sección cerrada, bpmn-js lanza
// «non-finite value on SVGMatrix».
//
// Ojo: no basta con exigir un tamaño mayor que cero. Un contenedor a medio dibujar mide
// unos pocos píxeles de ancho —se midieron 2— y con eso el fit falla igual. Se espera a
// que el lienzo tenga un tamaño realmente utilizable, y se reintenta mientras tanto.
// El adjunto conserva su nombre entre guardados, así que su URL no cambia nunca y
// el navegador reutiliza la copia vieja: la vista previa dibujaba el diagrama
// anterior aunque el guardado hubiese ido bien. `?v=<version>` cambia solo cuando
// cambia el diagrama, así que sigue habiendo caché entre ediciones.
sgc.bpmn.url_versionada = function (file_url, version) {
	if (!file_url || !version) return file_url;
	return `${file_url}${file_url.includes("?") ? "&" : "?"}v=${encodeURIComponent(version)}`;
};

sgc.bpmn.MIN_LIENZO = 50;

sgc.bpmn._ajustar = function ($lienzo, visor, restantes = 12) {
	const nodo = $lienzo[0];
	const min = sgc.bpmn.MIN_LIENZO;
	if (nodo && nodo.offsetWidth >= min && nodo.offsetHeight >= min) {
		try {
			visor.get("canvas").zoom("fit-viewport");
			return; // encuadrado
		} catch (e) {
			// El lienzo ya mide, pero el diagrama todavía no: se reintenta igual. No
			// basta con vigilar el tamaño del contenedor — el error salta también
			// mientras bpmn-js termina de colocar los elementos.
		}
	}
	if (restantes > 0) {
		setTimeout(() => sgc.bpmn._ajustar($lienzo, visor, restantes - 1), 150);
	}
};

sgc.bpmn._render = function ($wrapper, file_url) {
	const $lienzo = $wrapper.find(".sgc-bpmn-lienzo");
	if (!file_url || typeof BpmnJS === "undefined") return;
	if ($lienzo.data("visor")) $lienzo.data("visor").destroy();

	const visor = new BpmnJS({ container: $lienzo[0] });
	$lienzo.data("visor", visor);

	// Solo lectura: se cancela toda interacción de edición y se oculta la paleta.
	const eventBus = visor.get("eventBus");
	sgc.bpmn.EVENTOS_EDICION.forEach((evento) => eventBus.on(evento, 100000, () => false));
	$lienzo.find(".djs-palette").hide();

	fetch(sgc.bpmn.url_versionada(file_url, (sgc.bpmn._versiones || {})[file_url]))
		.then((res) => {
			if (!res.ok) throw new Error(res.status);
			return res.text();
		})
		.then((xml) => visor.importXML(xml))
		.then(() => {
			// La paleta la crea bpmn-js al importar, no antes: hay que ocultarla aquí.
			$lienzo.find(".djs-palette").hide();
			sgc.bpmn._ajustar($lienzo, visor);
		})
		.catch(() => {
			$lienzo.html(
				`<div class="text-muted" style="padding:16px;font-size:12px;">${__(
					"No se pudo dibujar el diagrama; el archivo adjunto sigue disponible."
				)}</div>`
			);
		});
};

// La secuencia por escrito, debajo del dibujo. El procedimiento se exporta como
// documento y un documento necesita el paso a paso legible: número, actividad y
// responsable. Sale del mismo BPMN que el diagrama, así que no puede contradecirlo.
sgc.bpmn._tareas = function ($wrapper, frm, file_url) {
	const $caja = $wrapper.find(".sgc-bpmn-tareas").empty();
	if (!file_url) return;

	frappe
		.call({
			method: "sgc.bpmn_editor.tareas_del_diagrama",
			args: { doctype: frm.doc.doctype, docname: frm.doc.name, file_url },
		})
		.then((r) => {
			const tareas = (r && r.message) || [];
			if (!tareas.length) return; // sin tareas legibles, no se ocupa espacio

			const filas = tareas
				.map(
					(t) => `<tr>
						<td style="width:3rem;text-align:right;padding-right:12px;color:var(--text-muted);">${t.n}</td>
						<td>${frappe.utils.escape_html(t.actividad || "")}</td>
						<td style="width:34%;">${
							t.responsable
								? frappe.utils.escape_html(t.responsable)
								: `<span class="text-muted">${__("Sin responsable en el diagrama")}</span>`
						}</td>
					</tr>`
				)
				.join("");

			$caja.append(`
				<div class="text-muted" style="font-size:11px;margin-bottom:6px;">${__(
					"Secuencia del procedimiento, leída del diagrama"
				)}</div>
				<div style="overflow-x:auto;">
					<table class="table table-bordered" style="margin:0;font-size:12px;">
						<thead>
							<tr>
								<th style="text-align:right;">Nº</th>
								<th>${__("Actividad")}</th>
								<th>${__("Responsable")}</th>
							</tr>
						</thead>
						<tbody>${filas}</tbody>
					</table>
				</div>
			`);
		});
};
