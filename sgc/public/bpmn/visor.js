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
			`);
			const $sel = $wrapper.find(".sgc-bpmn-sel");
			archivos.forEach((a) => $sel.append(`<option value="${a.file_url}">${a.file_name}</option>`));
			frappe.require("/assets/sgc/bpmn/bpmn-modeler.js", () => {
				sgc.bpmn._render($wrapper, $sel.val());
				$sel.on("change", () => sgc.bpmn._render($wrapper, $sel.val()));
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

	fetch(file_url)
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
