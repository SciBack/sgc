// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// Vista previa del documento dentro de la ficha.
//
// Lo pidió la DPGC el 10-sep-2026: hasta ahora el adjunto solo se podía descargar,
// y revisar 75 manuales bajándolos uno a uno no es revisar, es coleccionar
// ficheros. El PDF se dibuja aquí mismo; quien revisa lee y decide sin salir.
//
// Solo se embebe lo que el navegador sabe dibujar de forma segura (PDF e imagen).
// Para lo demás —un .docx, un .xlsx— se ofrece descargarlo, que es lo único
// honesto: fingir una vista previa que no se ve sería peor que no ofrecerla.

// Solo consulta (#36): el visor ya no apunta a la URL del fichero, sino a
// `sgc.documentos.ver`, que comprueba la lectura y registra la consulta. Quien
// no puede descargar el documento no ve «Descargar», ni el enlace del campo
// `archivo`, ni la barra del visor de PDF. Es disuasorio: el servidor es quien
// de verdad no entrega el fichero (ver sgc/documentos.py).

frappe.provide("sgc.documento");

frappe.ui.form.on("Documento Controlado", {
	refresh(frm) {
		const puede = sgc.documento.puede_descargar(frm);
		// El campo Attach enseña el enlace directo al fichero: a quien no puede
		// descargarlo le devolvería «sin permiso». Mejor no ofrecerlo.
		frm.toggle_display("archivo", puede || !frm.doc.archivo);
		sgc.documento.montar_visor(frm);
		// Enviar por correo lo publicado (#92): ver sgc/public/js/envio_correo.js.
		frappe.require("/assets/sgc/js/envio_correo.js", () => sgc.envio.boton(frm));
	},
	archivo(frm) {
		// Al cambiar el adjunto, la vista previa tiene que seguirlo.
		sgc.documento.montar_visor(frm);
	},
	url_externa(frm) {
		sgc.documento.montar_visor(frm);
	},
});

sgc.documento.puede_descargar = function (frm) {
	const onload = frm.doc.__onload || {};
	// Un documento nuevo, o sin el dato: lo decide el servidor al pedirlo.
	return onload.puede_descargar !== false;
};

sgc.documento.EXTENSIONES_EMBEBIBLES = {
	pdf: "pdf",
	png: "imagen",
	jpg: "imagen",
	jpeg: "imagen",
	gif: "imagen",
	webp: "imagen",
};

sgc.documento.url_metodo = function (metodo, frm) {
	// El sello de tiempo evita que el navegador reutilice la respuesta anterior:
	// cada apertura es una consulta y queda registrada.
	return `/api/method/sgc.documentos.${metodo}?nombre=${encodeURIComponent(frm.doc.name)}&_=${Date.now()}`;
};

sgc.documento.montar_visor = function (frm) {
	const campo = frm.get_field("visor_documento");
	if (!campo) return;
	const $envoltorio = $(campo.wrapper).empty();
	if (frm.is_new()) return;

	if (frm.doc.url_externa) {
		$envoltorio.append(`
			<div style="padding:10px 14px;margin-bottom:8px;border:1px solid var(--border-color);border-radius:6px;font-size:12px;">
				${__("Documento externo")}:
				<a target="_blank" rel="noopener noreferrer" href="${frappe.utils.escape_html(frm.doc.url_externa)}">${frappe.utils.escape_html(frm.doc.url_externa)}</a>
			</div>
		`);
	}
	if (!frm.doc.archivo) return;

	const extension = (frm.doc.archivo.split("?")[0].split(".").pop() || "").toLowerCase();
	const tipo = sgc.documento.EXTENSIONES_EMBEBIBLES[extension];
	const puede = sgc.documento.puede_descargar(frm);

	const aviso = puede
		? `<a class="text-muted" style="font-size:11px;margin-left:auto;" target="_blank" rel="noopener"
		      href="${sgc.documento.url_metodo("descargar", frm)}">${__("Descargar")}</a>`
		: `<span class="text-muted" style="font-size:11px;margin-left:auto;">${__("Solo consulta en pantalla")}</span>`;
	$envoltorio.append(`
		<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
			<span class="text-muted" style="font-size:11px;">${__("Vista previa del documento")}</span>
			${aviso}
		</div>
	`);

	const src = sgc.documento.url_metodo("ver", frm);
	if (tipo === "pdf") {
		// `#view=FitH` encuadra a lo ancho: el documento se lee sin tocar el zoom.
		// `toolbar=0` esconde la barra (y su botón de descarga) en los navegadores
		// que lo respetan. Disuasorio: no todos lo hacen.
		const vista = puede ? "view=FitH" : "toolbar=0&view=FitH";
		$envoltorio.append(
			`<embed src="${src}#${vista}" type="application/pdf"
			        style="width:100%;height:620px;border:1px solid var(--border-color);border-radius:6px;background:#fff;">`
		);
		return;
	}

	if (tipo === "imagen") {
		$envoltorio.append(
			`<img src="${src}" alt="" ${puede ? "" : 'oncontextmenu="return false" draggable="false"'}
			      style="max-width:100%;border:1px solid var(--border-color);border-radius:6px;background:#fff;">`
		);
		return;
	}

	$envoltorio.append(
		`<div class="text-muted" style="padding:14px;border:1px solid var(--border-color);border-radius:6px;font-size:12px;">
			${__("Este formato no se puede previsualizar aquí")} (<code>.${frappe.utils.escape_html(extension || "?")}</code>).
			${puede ? __("Use «Descargar» para consultarlo.") : ""}
		 </div>`
	);
};
