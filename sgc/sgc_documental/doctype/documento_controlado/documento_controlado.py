# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

"""M03 — Control documental del SGC.

Implementa el ciclo de vida que exige ISO 21001:2018 cl. 7.5 (informacion
documentada, norma de sistema de gestion de adopcion voluntaria): elaboracion ->
revision -> aprobacion -> publicacion -> obsolescencia, con control de versiones,
descripcion obligatoria del cambio y prevencion del uso de documentos obsoletos.

El «procedimiento DTN-Pro-01 de SUNEDU» que se citaba aqui como fuente del mismo
requisito NO esta verificado contra ninguna norma publicada de la Sunedu, asi que
no se apoya nada en el. Mismo aviso en `sgc/lista_maestra.py`.

Sustituye al puntero a Mayan EDMS: el archivo ahora es un adjunto de Frappe
(campo `archivo`) y el historico vive en la tabla `historial_cambios`.
"""


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_years, getdate, now_datetime, nowdate

from sgc import documentos, tareas
from sgc.naming import siguiente_correlativo

# Días antes de que venza la vigencia en que el responsable recibe la tarea de
# revisarlo. Los mismos que el aviso por correo «SGC - Documento por revisar».
DIAS_TAREA_REVISION = 15

# Roles que, además del dueño del proceso y de quien lo elaboró, pueden dejar
# constancia de una revisión sin cambios.
ROLES_REVISION = {"DPGC", "Analista de Calidad (DPGC)"}

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
	"Documentación externa": "DE",
}


class DocumentoControlado(Document):
	def before_insert(self):
		# El codigo es el `name` del documento (autoname: field:codigo). Si el
		# usuario no lo indico, se compone aqui — antes de que autoname lo lea.
		if not self.codigo:
			self.codigo = self._generar_codigo()
		if not self.version:
			# Entero, no "1.0": UPeU decidió el 2026-08-24 que una versión solo
			# existe cuando se aprueba, así que no hay medias versiones. Es
			# además lo habitual en gestión documental ISO — ninguna norma
			# prescribe el formato, es convención de la casa.
			self.version = 1
		# Quien crea el documento es quien lo elabora, salvo que se diga otra cosa.
		# Sin esto el campo se quedaba vacio para siempre: ninguna validacion lo
		# pedia y nadie lo rellena a mano, asi que un documento podia publicarse
		# sin constar quien lo redacto —y la alerta "documento por revisar", que
		# se dirige a `elaborado_por`, no llegaba a nadie mas que a la DPGC.
		if not self.elaborado_por:
			self.elaborado_por = frappe.session.user

	def onload(self):
		# El formulario decide con esto si ofrece descargar o solo el visor (#36).
		self.set_onload("puede_descargar", documentos.puede_descargar(self))

	def validate(self):
		self._validar_transicion()
		self._completar_dueno_proceso()
		self._validar_relacionados()
		self._registrar_observacion()
		self._sellar_aprobacion()
		self._validar_documentacion_externa()
		self._validar_solo_consulta()
		self._validar_requisitos_por_estado()
		self._validar_descripcion_cambio()

	def on_update(self):
		# La publicacion tiene efectos sobre OTROS documentos (obsoletar al que
		# reemplaza), por eso vive aqui y no en validate().
		if self.estado == "Publicado" and self._estado_anterior() != "Publicado":
			self._al_publicar()
		sincronizar_tarea_revision(self)

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
		return f"{prefijo}-{sigla}-{siguiente_correlativo(existentes):03d}"

	# ------------------------------------------------------------ validaciones

	def _validar_transicion(self):
		anterior = self._estado_anterior()
		if anterior is None or anterior == self.estado:
			return

		permitidos = TRANSICIONES.get(anterior, set())
		if self.estado not in permitidos:
			destino = ", ".join(sorted(permitidos)) if permitidos else _("ninguno")
			frappe.throw(
				_("No se puede pasar de «{0}» a «{1}». Destinos válidos: {2}.").format(
					anterior, self.estado, destino
				),
				title=_("Transición no permitida"),
			)

	def _completar_dueno_proceso(self):
		"""El dueño del proceso recibe el aviso de publicación: a él le afecta la versión."""
		self.dueno_proceso = (
			frappe.db.get_value("Proceso", self.proceso, "responsable") if self.proceso else None
		)

	def _validar_relacionados(self):
		vistos = set()
		for fila in self.documentos_relacionados or []:
			if fila.documento == self.name:
				frappe.throw(_("Un documento no se relaciona consigo mismo."))
			clave = (fila.documento, fila.relacion)
			if clave in vistos:
				frappe.throw(_("La relación con {0} está repetida.").format(fila.documento))
			vistos.add(clave)

	def _registrar_observacion(self):
		"""Lo que dice un revisor queda como evidencia, ligado al paso del flujo.

		Observar exige escribir la observación. Al cambiar de estado, el texto pasa
		al registro con quién, cuándo, en qué paso y sobre qué versión —lo sella el
		sistema— y el campo se vacía para la siguiente ronda. Aprobar con un
		comentario también lo registra.
		"""
		anterior = self._estado_anterior()
		if anterior is None or anterior == self.estado:
			return
		texto = (self.observacion or "").strip()
		if self.estado == "Observado" and not texto:
			frappe.throw(
				_("Escriba la observación del revisor antes de observar el documento: es lo que "
				  "tiene que corregir quien lo elaboró."),
				title=_("Observación obligatoria"),
			)
		if not texto:
			return
		self.append("observaciones_revision", {
			"fecha": now_datetime(),
			"revisor": frappe.session.user,
			"paso": f"{anterior} → {self.estado}",
			"version": self.version,
			"observacion": texto,
		})
		self.observacion = None

	def _sellar_aprobacion(self):
		"""Aprobar ES firmar: lo registra quien ejecuta la transición.

		De las tres firmas que pide el ciclo documental de la ISO 21001 (cl.
		7.5) —quien elabora, quien revisa, quien aprueba— la tercera no la
		escribía NADIE. Y no era un hueco cosmético: publicar la exige, así que
		el flujo moría en «Aprobado» sin salida posible. Comprobado en el
		recorrido del 2026-08-23: la DPGC aprobaba, la Autoridad Aprobadora
		intentaba publicar y recibía «No se puede publicar sin quien lo aprobo»,
		un requisito que ninguna acción del sistema podía satisfacer. La única
		escapatoria era que alguien tecleara el campo a mano — justo lo que
		convierte una firma en un dato inventado.

		Mismo patrón que `elaborado_por` (v88): la firma la pone el acto, no un
		formulario. Se sella al ENTRAR en «Aprobado», comparando con el estado
		anterior, para que una segunda aprobación tras una observación registre
		a quien aprueba esta vez y no conserve al de la ronda anterior.

		`revisado_por` se queda fuera a propósito: quien revisa puede no ser
		quien pulsa «Aprobar», y el sistema no puede adivinarlo. Por eso hay una
		validación que obliga a declararlo — esa sí funciona.
		"""
		anterior = self.get_doc_before_save()
		if self.estado == "Aprobado" and (not anterior or anterior.estado != "Aprobado"):
			self.aprobado_por = frappe.session.user

	def _tiene_contenido(self):
		"""El archivo; o, solo en la documentación externa, el enlace a donde vive."""
		return bool(self.archivo) or (self._es_externo() and bool(self.url_externa))

	def _es_externo(self):
		return self.tipo_documento == documentos.EXTERNA

	def _validar_documentacion_externa(self):
		"""Documentación de origen externo (ISO 9001 §7.5.3.2): se identifica y se
		controla aunque no se aloje aquí (#36)."""
		if self.url_externa:
			self.url_externa = self.url_externa.strip()
			if not documentos.url_externa_valida(self.url_externa):
				frappe.throw(_("El enlace externo debe empezar por http:// o https://."))

	def _validar_solo_consulta(self):
		"""Solo se puede restringir la descarga de lo que se puede ver en pantalla (#36).

		- Sin archivo aquí no hay nada que restringir: un enlace externo lo abre
		  cualquiera.
		- Un .docx no se dibuja en el navegador: quien no puede descargarlo no
		  podría leerlo de ninguna forma.
		- Un fichero PÚBLICO lo sirve el servidor web sin pasar por Frappe: la
		  restricción sería papel mojado.
		"""
		if not self.solo_consulta:
			return
		if not self.archivo:
			frappe.throw(_("«Solo consulta en pantalla» necesita un archivo adjunto."))
		if not documentos.se_puede_ver_en_pantalla(self.archivo):
			frappe.throw(
				_("«Solo consulta en pantalla» necesita un PDF o una imagen: un .{0} no se "
				  "puede ver en pantalla. Adjunte la versión en PDF.").format(
					documentos.extension(self.archivo) or "?"
				)
			)
		if not self.archivo.startswith("/private/"):
			frappe.throw(
				_("«Solo consulta en pantalla» necesita un archivo privado: uno público lo "
				  "puede abrir cualquiera con el enlace. Vuelva a adjuntarlo marcado como privado.")
			)

	def _validar_requisitos_por_estado(self):
		if self.estado == "En revision":
			if not self._tiene_contenido():
				if self._es_externo():
					frappe.throw(
						_("Adjunte el archivo o indique el enlace al documento externo antes de "
						  "enviarlo a revisión.")
					)
				frappe.throw(_("Adjunte el archivo del documento antes de enviarlo a revisión."))
			if not self.elaborado_por:
				frappe.throw(_("Indique quién elaboró el documento antes de enviarlo a revisión."))

		if self.estado == "Aprobado" and not self.revisado_por:
			frappe.throw(_("Indique quién revisó el documento antes de aprobarlo."))

		if self.estado == "Publicado":
			# Sin las firmas, la norma prohibe comunicar e implementar el documento.
			faltan = []
			if not self._tiene_contenido():
				faltan.append(_("el archivo o el enlace externo") if self._es_externo() else _("el archivo"))
			if not self.elaborado_por:
				faltan.append(_("quién lo elaboró"))
			if not self.aprobado_por:
				faltan.append(_("quién lo aprobó"))
			if faltan:
				frappe.throw(
					_("No se puede publicar sin {0}.").format(" y ".join(faltan)),
					title=_("Publicación incompleta"),
				)

	def _validar_descripcion_cambio(self):
		"""La norma exige registrar QUE cambio en cada nueva version."""
		if self.is_new():
			return

		anterior = self.get_doc_before_save()
		if anterior and anterior.version != self.version and not self.descripcion_cambio:
			frappe.throw(
				_("Al cambiar de versión ({0} → {1}) debe describir el cambio.").format(
					anterior.version, self.version
				),
				title=_("Descripción del cambio obligatoria"),
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

	# ------------------------------------------------------------- revisión

	@frappe.whitelist()
	def preparar_observacion(self, texto):
		"""Deja escrita la observación ANTES de la acción «Observar» del workflow.

		`apply_workflow` recarga el documento desde la base (`load_from_db`): lo que
		se escriba en pantalla sin guardar no llega a la transición. Y guardar no
		siempre se puede: en «Aprobado» edita la Autoridad Aprobadora, no la DPGC
		que observa. Solo quien tiene disponible la acción «Observar» puede
		dejarla; el registro sellado lo hace `_registrar_observacion` al transitar.
		"""
		from frappe.model.workflow import get_transitions

		texto = (texto or "").strip()
		if not texto:
			frappe.throw(_("Escriba la observación del revisor."))
		if "Observar" not in {t.action for t in get_transitions(self)}:
			frappe.throw(_("No puede observar este documento en su estado actual."), frappe.PermissionError)
		self.db_set("observacion", texto, update_modified=False)

	@frappe.whitelist()
	def registrar_revision(self, observacion=None):
		"""Constancia de una revisión SIN cambios: el documento sigue vigente un año más.

		La norma pide revisar el documento al menos una vez al año, no reescribirlo.
		Cuando la revisión concluye que sigue siendo válido, esto lo deja escrito en
		el historial, renueva la vigencia y cierra la tarea de revisión.
		"""
		if self.estado != "Publicado":
			frappe.throw(_("Solo se revisa la vigencia de un documento publicado."))
		usuario = frappe.session.user
		if not (usuario in (self.dueno_proceso, self.elaborado_por)
				or ROLES_REVISION & set(frappe.get_roles(usuario))):
			frappe.throw(
				_("Registra la revisión el dueño del proceso, quien elaboró el documento o la DPGC."),
				frappe.PermissionError,
			)
		hoy = nowdate()
		fila = self.append("historial_cambios", {
			"version": self.version,
			"fecha": hoy,
			"descripcion": _("Revisión sin cambios: sigue vigente.") + (
				" " + observacion.strip() if (observacion or "").strip() else ""),
			"autor": usuario,
		})
		fila.db_insert()
		self.db_set("fecha_proxima_revision", add_years(hoy, 1), update_modified=False)
		sincronizar_tarea_revision(self)
		return self.fecha_proxima_revision


def sincronizar_tarea_revision(doc):
	"""La tarea de revisar el documento, abierta solo mientras toca revisarlo.

	Se abre cuando faltan `DIAS_TAREA_REVISION` días (o menos) para que venza la
	vigencia de un documento publicado, a nombre del dueño del proceso o, si no
	lo hay, de quien lo elaboró. Se cierra al renovarse la vigencia (una revisión
	sin cambios o una nueva publicación) y al dejar de estar publicado.
	"""
	responsable = doc.dueno_proceso or doc.elaborado_por
	fecha = doc.fecha_proxima_revision
	abierta = bool(
		doc.estado == "Publicado" and fecha
		and getdate(fecha) <= getdate(add_days(nowdate(), DIAS_TAREA_REVISION))
	)
	descripcion = _("Revisar el documento {0} ({1}): su vigencia vence el {2}.").format(
		doc.name, doc.titulo or "", frappe.utils.formatdate(fecha) if fecha else "")
	tareas.sincronizar(doc, responsable, fecha, descripcion, abierta)


def tareas_revision_diaria():
	"""Scheduler diario: abre las tareas que entran en plazo y cierra las que sobran."""
	limite = add_days(nowdate(), DIAS_TAREA_REVISION)
	candidatos = set(frappe.get_all(
		"Documento Controlado",
		filters={"estado": "Publicado", "fecha_proxima_revision": ["<=", limite]},
		pluck="name", limit=0,
	))
	candidatos |= set(frappe.get_all(
		"ToDo",
		filters={"reference_type": "Documento Controlado", "status": tareas.ABIERTA},
		pluck="reference_name", limit=0,
	))
	for nombre in candidatos:
		if frappe.db.exists("Documento Controlado", nombre):
			sincronizar_tarea_revision(frappe.get_doc("Documento Controlado", nombre))
