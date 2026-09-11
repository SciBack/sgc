// Copyright (c) 2026, SciBack and contributors
// For license information, please see license.txt

// Vista previa del documento dentro de la ficha.
//
// Lo pidió la DPGC el 10-sep-2026: hasta ahora el adjunto solo se podía descargar,
// y revisar 75 manuales bajándolos uno a uno no es revisar, es coleccionar
// ficheros. El PDF se dibuja aquí mismo; quien revisa lee y decide sin salir.
//
// Solo se embebe lo que el navegador sabe dibujar de forma segura (PDF e imagen).
// Para lo demás —un .docx, un .xlsx— se ofrece abrir en pestaña, que es lo único
// honesto: fingir una vista previa que no se ve sería peor que no ofrecerla.

frappe.provide("sgc.documento");

frappe.ui.form.on("Documento Controlado", {
	refresh(frm) {
		sgc.documento.montar_visor(frm);
	},
	archivo(frm) {
		// Al cambiar el adjunto, la vista previa tiene que seguirlo.
		sgc.documento.montar_visor(frm);
	},
});

sgc.documento.EXTENSIONES_EMBEBIBLES = {
	pdf: "pdf",
	png: "imagen",
	jpg: "imagen",
	jpeg: "imagen",
	gif: "imagen",
	webp: "imagen",
	svg: "imagen",
};

sgc.documento.montar_visor = function (frm) {
	const campo = frm.get_field("visor_documento");
	if (!campo) return;
	const $envoltorio = $(campo.wrapper).empty();
	if (frm.is_new() || !frm.doc.archivo) return;

	const url = frm.doc.archivo;
	const extension = (url.split("?")[0].split(".").pop() || "").toLowerCase();
	const tipo = sgc.documento.EXTENSIONES_EMBEBIBLES[extension];

	const $barra = $(`
		<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
			<span class="text-muted" style="font-size:11px;">${__("Vista previa del documento")}</span>
			<a class="text-muted" style="font-size:11px;margin-left:auto;" target="_blank" rel="noopener"
			   href="${frappe.utils.escape_html(url)}">${__("Abrir en pestaña nueva")}</a>
		</div>
	`);
	$envoltorio.append($barra);

	if (tipo === "pdf") {
		// `#view=FitH` encuadra a lo ancho: el documento se lee sin tocar el zoom.
		$envoltorio.append(
			`<embed src="${frappe.utils.escape_html(url)}#view=FitH" type="application/pdf"
			        style="width:100%;height:620px;border:1px solid var(--border-color);border-radius:6px;background:#fff;">`
		);
		return;
	}

	if (tipo === "imagen") {
		$envoltorio.append(
			`<img src="${frappe.utils.escape_html(url)}" alt=""
			      style="max-width:100%;border:1px solid var(--border-color);border-radius:6px;background:#fff;">`
		);
		return;
	}

	$envoltorio.append(
		`<div class="text-muted" style="padding:14px;border:1px solid var(--border-color);border-radius:6px;font-size:12px;">
			${__("Este formato no se puede previsualizar aquí")} (<code>.${frappe.utils.escape_html(extension || "?")}</code>).
			${__("Use «Abrir en pestaña nueva» para consultarlo.")}
		 </div>`
	);
};
