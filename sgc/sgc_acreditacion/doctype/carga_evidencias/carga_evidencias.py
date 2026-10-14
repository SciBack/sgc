# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

"""Carga masiva de evidencias desde un ZIP (TDR SGC-UPeU, M09 y entregable E6 «carga masiva»).

Por qué existe: las evidencias de acreditación viven hoy en carpetas (OneDrive, Drive) ordenadas
por estándar y criterio. Subirlas una a una no es realista (el MVP pide 500). Se descarga la
carpeta como ZIP, se sube aquí y, al validar la carga, se crea cada `Evidencia` con su
`Trazabilidad` al criterio.

Cómo se reconoce el criterio de cada archivo, por orden:
1. Un `indice.csv` en el ZIP con las columnas `archivo,elemento[,titulo]` (lo más preciso).
2. El nombre de las carpetas: la más profunda que empiece por un código del marco
   («1.1 Propósitos…», «Criterio 1.1», «C1.1», «E1», «Estándar 1», «I.1» en las CBC).
Lo que no se reconoce se crea igual, sin vínculo, y queda señalado en el detalle para
vincularlo a mano.

Se omiten los archivos repetidos (misma huella que una evidencia existente o que otro archivo del
ZIP), los tipos no admitidos y la basura del sistema operativo. Nada se borra ni se sobrescribe.
"""

import csv
import io
import os
import re
import unicodedata
import zipfile

import frappe
from frappe import _
from frappe.core.doctype.file.utils import get_content_hash
from frappe.model.document import Document
from frappe.utils import cint

EXTENSIONES = {
	"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt", "ods", "odp", "rtf", "txt", "csv",
	"md", "jpg", "jpeg", "png", "gif", "webp", "mp4", "mp3", "zip",
}
BASURA = re.compile(r"(^|/)(__MACOSX|\.DS_Store|Thumbs\.db|desktop\.ini|~\$[^/]*|\._[^/]*)(/|$)", re.IGNORECASE)
MAX_ARCHIVOS = 3000
MAX_DESCOMPRIMIDO = 3 * 1024 * 1024 * 1024  # 3 GB: corta un ZIP bomba antes de leerlo
TIPO_POR_EXTENSION = {"csv": "Dataset", "xls": "Dataset", "xlsx": "Dataset", "ods": "Dataset"}
PALABRAS = re.compile(r"^(criterio|estandar|est|condicion|cbc|componente|indicador|factor|dimension)[\s._-]*")


def _sin_tildes(texto):
	return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn").lower()


def _clave(texto):
	"""El código que encabeza un nombre de carpeta: «Criterio 1.1 Propósitos» -> «1.1», «E1 …» -> «e1».

	«Estándar 1» -> «e1». Un número suelto («1. Inventario») NO es un estándar: las carpetas
	numeradas son lo más común y casarían por error con el Estándar 1.
	"""
	t = _sin_tildes(texto).strip()
	estandar = re.match(r"^(estandar|est)[\s._-]*(\d+)(?=$|[\s._)\-])", t)
	if estandar:
		return "e" + estandar.group(2)
	t = PALABRAS.sub("", t)
	m = re.match(r"^([a-z]?\d+(?:\.\d+)*|[ivxlc]+(?:\.\d+)*)(?=$|[\s._)\-])", t)
	return m.group(1) if m else None


class CargaEvidencias(Document):
	def validate(self):
		if not (self.archivo_zip or "").lower().endswith(".zip"):
			frappe.throw(_("Adjunte un archivo .zip con las evidencias."))

	def on_submit(self):
		self.db_set("estado", "En proceso")
		frappe.enqueue(
			"sgc.sgc_acreditacion.doctype.carga_evidencias.carga_evidencias.procesar",
			queue="long", timeout=3600, carga=self.name, enqueue_after_commit=True,
			now=frappe.in_test,
		)

	# ------------------------------------------------------------ lectura

	def _elementos(self):
		"""{clave: name} de los elementos del marco, por el último tramo del código.

		«CONEAU-1.1» y «CONEAU-INST-1.1» -> «1.1»; «CONEAU-E1» -> «e1»; «CBC-I.1» -> «i.1».
		Se salta la raíz del marco: su código acaba en un año y casaría con cualquier carpeta «2025».
		"""
		claves = {}
		for e in frappe.get_all("Elemento Marco", filters={"marco_normativo": self.marco_normativo},
								fields=["name", "codigo", "tipo", "parent_elemento_marco"], order_by="lft asc"):
			if not e.parent_elemento_marco and e.tipo == "Dimension":
				continue
			sufijo = (e.codigo or e.name).rsplit("-", 1)[-1]
			for k in {_sin_tildes(sufijo), _clave(sufijo) or ""} - {""}:
				if k not in claves or e.tipo == "Criterio":
					claves[k] = e.name
		return claves

	def _indice(self, zf):
		nombre = next((n for n in zf.namelist() if os.path.basename(n).lower() == "indice.csv"), None)
		if not nombre:
			return {}
		texto = zf.read(nombre).decode("utf-8-sig", errors="replace")
		indice = {}
		for fila in csv.DictReader(io.StringIO(texto)):
			archivo = (fila.get("archivo") or "").strip().replace("\\", "/")
			if archivo:
				indice[archivo.lstrip("./")] = {"elemento": (fila.get("elemento") or "").strip(),
												"titulo": (fila.get("titulo") or "").strip()}
		return indice

	def _resolver(self, ruta, indice, claves):
		fila = indice.get(ruta) or indice.get(os.path.basename(ruta))
		if fila and fila["elemento"]:
			e = fila["elemento"]
			if frappe.db.exists("Elemento Marco", e):
				return e, fila.get("titulo")
			return claves.get(_sin_tildes(e)) or claves.get(_clave(e) or ""), fila.get("titulo")
		for carpeta in reversed(ruta.split("/")[:-1]):
			k = _clave(carpeta) or ""
			if k.isdigit():
				continue  # «1. Inventario»: carpeta numerada, no un código del marco
			for candidata in (k, k[1:] if k[:1].isalpha() and k[1:2].isdigit() else ""):
				if candidata in claves:  # «C1.1» vale como «1.1»
					return claves[candidata], None
		return None, None

	# ------------------------------------------------------------ proceso

	def procesar(self):
		with open(frappe.get_doc("File", {"file_url": self.archivo_zip}).get_full_path(), "rb") as f:
			contenido = f.read()  # bytes tal cual: get_content() decodifica a texto y rompe el ZIP
		try:
			zf = zipfile.ZipFile(io.BytesIO(contenido))
		except zipfile.BadZipFile:
			frappe.throw(_("El archivo adjunto no es un ZIP válido."))

		entradas = [i for i in zf.infolist() if not i.is_dir()]
		if len(entradas) > MAX_ARCHIVOS:
			frappe.throw(_("El ZIP tiene {0} archivos; el máximo por carga es {1}. Divídalo.").format(len(entradas), MAX_ARCHIVOS))
		if sum(i.file_size for i in entradas) > MAX_DESCOMPRIMIDO:
			frappe.throw(_("El ZIP descomprimido supera 3 GB. Divídalo en varias cargas."))

		indice, claves = self._indice(zf), self._elementos()
		existentes = set(frappe.get_all("Evidencia", filters={"hash_sha256": ["is", "set"]}, pluck="hash_sha256"))
		limite = cint(frappe.get_system_settings("max_file_size")) * 1024 * 1024 or 25 * 1024 * 1024
		self.filas = []
		creadas = vinculadas = sin_vinculo = omitidos = 0

		for info in entradas:
			ruta = info.filename.replace("\\", "/")
			nombre = os.path.basename(ruta)
			if BASURA.search(ruta) or nombre.lower() == "indice.csv":
				continue
			ext = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
			datos = huella = None
			if ruta.startswith("/") or ".." in ruta.split("/"):
				motivo = _("Omitido: ruta no permitida")
			elif ext not in EXTENSIONES:
				motivo = _("Omitido: tipo no admitido")
			elif info.file_size > limite:
				motivo = _("Omitido: supera el tamaño máximo")
			else:
				datos = zf.read(info)
				huella = get_content_hash(datos)
				motivo = _("Omitido: ya cargado") if huella in existentes else None
			if motivo:
				self._fila(ruta, resultado=motivo)
				omitidos += 1
				continue
			existentes.add(huella)

			elemento, titulo = self._resolver(ruta, indice, claves)
			frappe.db.savepoint("carga_archivo")
			try:
				evidencia = self._crear_evidencia(nombre, datos, titulo, ext)
			except Exception as e:
				# Un PDF o imagen dañado no debe tumbar la carga de los otros 499.
				frappe.db.rollback(save_point="carga_archivo")
				existentes.discard(huella)
				self._fila(ruta, resultado=_("Omitido: archivo dañado o no válido ({0})").format(type(e).__name__))
				omitidos += 1
				continue
			creadas += 1
			if elemento or self.proceso:
				self._vincular(evidencia, elemento)
				vinculadas += 1
				self._fila(ruta, evidencia, elemento,
						   _("Creada y vinculada") if elemento else _("Creada y vinculada solo al proceso"))
			else:
				sin_vinculo += 1
				self._fila(ruta, evidencia, None, _("Creada sin criterio: vincúlela a mano"))

		for fila in self.filas:
			fila.db_insert()
		self.db_set({
			"n_archivos": len(self.filas), "n_creadas": creadas, "n_vinculadas": vinculadas,
			"n_sin_vinculo": sin_vinculo, "n_omitidos": omitidos,
			"estado": "Procesada" if not sin_vinculo else "Con observaciones",
		})

	def _fila(self, archivo, evidencia=None, elemento=None, resultado=None):
		self.append("filas", {"archivo": archivo[:140], "evidencia": evidencia, "elemento_marco": elemento,
							  "resultado": resultado, "docstatus": 1})

	def _crear_evidencia(self, nombre, datos, titulo, ext):
		"""Primero el File (la Evidencia exige su soporte al validar), luego la Evidencia, y se enlazan."""
		archivo = frappe.get_doc({"doctype": "File", "file_name": nombre, "content": datos, "is_private": 1}).insert()
		evidencia = frappe.get_doc({
			"doctype": "Evidencia",
			"titulo": (titulo or os.path.splitext(nombre)[0].replace("_", " ").strip() or nombre)[:140],
			"tipo": TIPO_POR_EXTENSION.get(ext, "Documento"),
			"archivo": archivo.file_url,
			"programa_sede": self.programa_sede, "periodo_academico": self.periodo_academico,
			"unidad_organica": self.unidad_organica,
			"origen_doctype": self.doctype, "origen_id": self.name,
		}).insert()
		archivo.db_set({"attached_to_doctype": "Evidencia", "attached_to_name": evidencia.name,
						"attached_to_field": "archivo"})
		return evidencia.name

	def _vincular(self, evidencia, elemento):
		frappe.get_doc({"doctype": "Trazabilidad", "evidencia": evidencia, "elemento_marco": elemento,
						"proceso": self.proceso, "tipo_vinculo": self.tipo_vinculo or "Soporta",
						"origen": "Directo"}).insert()


def procesar(carga):
	"""Trabajo en segundo plano: procesa la carga y deja el resultado o el error en el registro."""
	doc = frappe.get_doc("Carga Evidencias", carga)
	if frappe.in_test:
		doc.procesar()  # en línea y dentro de la transacción del test
		return
	try:
		doc.procesar()
		frappe.db.commit()
	except Exception as e:
		frappe.db.rollback()
		frappe.db.set_value("Carga Evidencias", carga, "estado", "Con observaciones")
		doc.add_comment("Comment", _("La carga no se pudo procesar: {0}").format(e))
		frappe.db.commit()
