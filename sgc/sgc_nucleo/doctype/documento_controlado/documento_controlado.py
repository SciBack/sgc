# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

"""M03 — Control documental del SGC.

Implementa el ciclo de vida que exige la norma (ISO 21001 cl. 7.5, replicado en el
procedimiento DTN-Pro-01 de SUNEDU): elaboracion -> revision -> aprobacion ->
publicacion -> obsolescencia, con control de versiones, descripcion obligatoria del
cambio y prevencion del uso de documentos obsoletos.

Sustituye al puntero a Mayan EDMS: el archivo ahora es un adjunto de Frappe
(campo `archivo`) y el historico vive en la tabla `historial_cambios`.
"""

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_years, nowdate


def _siguiente_correlativo(nombres) -> int:
	"""Máximo sufijo numérico de una lista de códigos + 1 (robusto a borrados)."""
	maximo = 0
	for n in nombres:
		m = re.search(r"(\d+)$", n or "")
		if m:
			maximo = max(maximo, int(m.group(1)))
	return maximo + 1

# Transiciones permitidas. Un estado con conjunto vacio es terminal.
TRANSICIONES = {
	"Borrador": {"En revision"},
	"En revision": {"Aprobado", "Observado"},
	"Observado": {"Borrador", "En revision"},
	"Aprobado": {"Publicado", "Observado"},
	"Publicado": {"Obsoleto"},
	"Obsoleto": set(),
}

# Sigla por tipo documental, para componer el codigo SGC.
SIGLAS = {
	"Manual": "MN",
	"Política": "PO",
	"Procedimiento": "PR",
	"Instructivo": "IN",
	"Guía": "GU",
	"Formato": "RG",
	"Plan": "PL",
	"Informe": "IA",
}


class DocumentoControlado(Document):
	def before_insert(self):
		# El codigo es el `name` del documento (autoname: field:codigo). Si el
		# usuario no lo indico, se compone aqui — antes de que autoname lo lea.
		if not self.codigo:
			self.codigo = self._generar_codigo()
		if not self.version:
			self.version = "1.0"

	def validate(self):
		self._validar_transicion()
		self._validar_requisitos_por_estado()
		self._validar_descripcion_cambio()

	def on_update(self):
		# La publicacion tiene efectos sobre OTROS documentos (obsoletar al que
		# reemplaza), por eso vive aqui y no en validate().
		if self.estado == "Publicado" and self._estado_anterior() != "Publicado":
			self._al_publicar()

	# ---------------------------------------------------------------- helpers

	def _estado_anterior(self):
		"""Estado con el que este documento estaba guardado en la BD."""
		if self.is_new():
			return None
		previo = self.get_doc_before_save()
		return previo.estado if previo else None

	def _generar_codigo(self) -> str:
		"""Codigo SGC: [PROCESO]-[SIGLA]-[NNN], con correlativo por prefijo+sigla.

		El correlativo se toma del MÁXIMO sufijo existente + 1, no de count(): con
		count(), borrar un documento intermedio hace que el siguiente reuse un
		número ya usado y choque contra el `unique` del código (DuplicateEntryError).

		El correlativo se escopa al MISMO prefijo visible que forma el `name`
		(`{prefijo}-{sigla}-%`), NO al proceso completo: el prefijo trunca el
		proceso a 12 caracteres, así que dos procesos cuyos primeros 12 caracteres
		coinciden (p.ej. "PROC-GESTION-01" y "PROC-GESTION-02") comparten prefijo de
		código. Escopar al proceso les daría a ambos el correlativo 001 y colisionar-
		ían en el PK; escopar al prefijo garantiza que el `name` generado es único.
		"""
		sigla = SIGLAS.get(self.tipo_documento, "DO")
		prefijo = (self.proceso or "SGC").upper().replace(" ", "")[:12]

		existentes = frappe.get_all(
			"Documento Controlado",
			filters={"name": ["like", f"{prefijo}-{sigla}-%"]},
			pluck="name",
		)
		return f"{prefijo}-{sigla}-{_siguiente_correlativo(existentes):03d}"

	# ------------------------------------------------------------ validaciones

	def _validar_transicion(self):
		anterior = self._estado_anterior()
		if anterior is None or anterior == self.estado:
			return

		permitidos = TRANSICIONES.get(anterior, set())
		if self.estado not in permitidos:
			destino = ", ".join(sorted(permitidos)) if permitidos else _("ninguno")
			frappe.throw(
				_("No se puede pasar de «{0}» a «{1}». Destinos validos: {2}.").format(
					anterior, self.estado, destino
				),
				title=_("Transicion no permitida"),
			)

	def _validar_requisitos_por_estado(self):
		if self.estado == "En revision" and not self.archivo:
			frappe.throw(_("Adjunte el archivo del documento antes de enviarlo a revision."))

		if self.estado == "Aprobado" and not self.revisado_por:
			frappe.throw(_("Indique quien reviso el documento antes de aprobarlo."))

		if self.estado == "Publicado":
			# Sin las firmas, la norma prohibe comunicar e implementar el documento.
			faltan = []
			if not self.archivo:
				faltan.append(_("el archivo"))
			if not self.aprobado_por:
				faltan.append(_("quien lo aprobo"))
			if faltan:
				frappe.throw(
					_("No se puede publicar sin {0}.").format(" y ".join(faltan)),
					title=_("Publicacion incompleta"),
				)

	def _validar_descripcion_cambio(self):
		"""La norma exige registrar QUE cambio en cada nueva version."""
		if self.is_new():
			return

		anterior = self.get_doc_before_save()
		if anterior and anterior.version != self.version and not self.descripcion_cambio:
			frappe.throw(
				_("Al cambiar de version ({0} -> {1}) debe describir el cambio.").format(
					anterior.version, self.version
				),
				title=_("Descripcion del cambio obligatoria"),
			)

	# -------------------------------------------------------------- publicacion

	def _al_publicar(self):
		fecha = self.fecha_publicacion or nowdate()
		self.db_set(
			{
				"fecha_publicacion": fecha,
				# La norma exige revisar el documento al menos una vez al ano.
				"fecha_proxima_revision": add_years(fecha, 1),
			},
			update_modified=False,
		)

		self._archivar_cambio(fecha)
		self._obsoletar_reemplazado()

	def _archivar_cambio(self, fecha):
		"""Congela la descripcion del cambio en el historial y limpia el campo."""
		if not self.descripcion_cambio:
			return

		if any(fila.version == self.version for fila in (self.historial_cambios or [])):
			return

		fila = self.append(
			"historial_cambios",
			{
				"version": self.version,
				"fecha": fecha,
				"descripcion": self.descripcion_cambio,
				"autor": self.aprobado_por or frappe.session.user,
			},
		)
		fila.db_insert()
		self.db_set("descripcion_cambio", None, update_modified=False)

	def _obsoletar_reemplazado(self):
		"""Prevencion del uso involuntario de informacion obsoleta (ISO 21001 7.5.3.2.g)."""
		if not self.reemplaza_a:
			return

		estado_previo = frappe.db.get_value("Documento Controlado", self.reemplaza_a, "estado")
		if estado_previo == "Obsoleto":
			return

		frappe.db.set_value("Documento Controlado", self.reemplaza_a, "estado", "Obsoleto")
		frappe.msgprint(
			_("El documento {0} quedo marcado como Obsoleto.").format(self.reemplaza_a),
			indicator="orange",
			alert=True,
		)
