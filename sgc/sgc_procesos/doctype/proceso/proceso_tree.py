# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Lectura segura de la jerarquía compuesta del mapa de procesos."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterable
from typing import Any

MAX_BPMN_BYTES = 5 * 1024 * 1024

TIPOS_TAREA_BPMN = frozenset(
	{
		"task",
		"userTask",
		"serviceTask",
		"manualTask",
		"scriptTask",
		"sendTask",
		"receiveTask",
		"businessRuleTask",
	}
)


class BpmnInvalido(ValueError):
	"""El archivo no se puede proyectar de forma segura como tareas N4."""


def get_children(
	doctype: str,
	parent: str | None = "",
	is_root: bool | str = False,
	**filters: Any,
) -> list[dict[str, Any]]:
	"""Proyecta Proceso, Procedimiento y las tareas BPMN en un Tree de Frappe."""
	frappe = _frappe()
	if frappe.session.user == "Guest":
		frappe.throw("El mapa de procesos requiere autenticación", exc=frappe.PermissionError)
	if doctype != "Proceso":
		frappe.throw("El proveedor solo admite el DocType Proceso", exc=frappe.ValidationError)
	if not frappe.permissions.has_permission("Proceso", ptype="read", print_logs=False):
		frappe.throw("Sin permiso de lectura sobre Proceso", exc=frappe.PermissionError)

	# Estos argumentos forman parte del contrato de Tree v16. No alteran la fuente
	# canónica del mapa y se aceptan para compatibilidad con Expand All.
	del is_root, filters
	if parent in (None, ""):
		return _nodos_raiz(frappe)

	prefijo, separador, identificador = str(parent).partition(":")
	if not separador or not identificador:
		_rechazar_padre(frappe)
	if prefijo == "proceso":
		return _hijos_de_proceso(frappe, identificador)
	if prefijo == "procedimiento":
		return _hijos_de_procedimiento(frappe, identificador)
	if prefijo == "tarea":
		return _validar_tarea_hoja(frappe, identificador)
	_rechazar_padre(frappe)
	return []


def _nodos_raiz(frappe) -> list[dict[str, Any]]:
	raices = _procesos_visibles(frappe, {"parent_proceso": ["is", "not set"]})
	expandibles = _procesos_con_hijos_visibles(frappe, [row.name for row in raices])
	return [_nodo_proceso(row, row.name in expandibles) for row in raices]


def _hijos_de_proceso(frappe, name: str) -> list[dict[str, Any]]:
	_proceso_visible(frappe, name)
	hijos = _procesos_visibles(frappe, {"parent_proceso": name})
	procedimientos = _procedimientos_visibles(frappe, {"proceso": name})
	expandibles = _procesos_con_hijos_visibles(frappe, [row.name for row in hijos])
	tareas = _tareas_por_procedimiento(frappe, procedimientos)

	nodos = [_nodo_proceso(row, row.name in expandibles) for row in hijos]
	nodos.extend(
		_nodo_procedimiento(row, bool(tareas.get(row.name))) for row in procedimientos
	)
	return nodos


def _hijos_de_procedimiento(frappe, name: str) -> list[dict[str, Any]]:
	procedimiento = _procedimiento_visible(frappe, name)
	tareas = _tareas_por_procedimiento(frappe, [procedimiento]).get(name, [])
	return [_nodo_tarea(procedimiento, tarea) for tarea in tareas]


def _validar_tarea_hoja(frappe, identificador: str) -> list[dict[str, Any]]:
	file_name, separador, bpmn_id = identificador.rpartition(":")
	if not separador or not file_name or not bpmn_id:
		_rechazar_padre(frappe)

	files = frappe.get_list(
		"File",
		filters={"name": file_name},
		fields=[
			"name",
			"file_url",
			"file_size",
			"modified",
			"attached_to_doctype",
			"attached_to_name",
		],
		limit=2,
		ignore_permissions=True,
	)
	if len(files) != 1 or files[0].attached_to_doctype != "Procedimiento":
		_rechazar_padre(frappe)
	procedimiento = _procedimiento_visible(frappe, files[0].attached_to_name)
	if procedimiento.diagrama_flujo != files[0].file_url:
		_rechazar_padre(frappe)
	tareas = _tareas_por_procedimiento(frappe, [procedimiento]).get(procedimiento.name, [])
	if not any(tarea["id"] == bpmn_id for tarea in tareas):
		_rechazar_padre(frappe)
	return []


def _procesos_con_hijos_visibles(frappe, names: list[str]) -> set[str]:
	if not names:
		return set()
	hijos = _procesos_visibles(frappe, {"parent_proceso": ["in", names]})
	resultado = {row.parent_proceso for row in hijos}
	procedimientos = _procedimientos_visibles(frappe, {"proceso": ["in", names]})
	resultado.update(row.proceso for row in procedimientos)
	return resultado


def _procesos_visibles(frappe, filters: dict[str, Any]) -> list[Any]:
	rows = frappe.get_list(
		"Proceso",
		filters=filters,
		fields=["*"],
		order_by="orden asc, name asc",
	)
	return _filtrar_permiso_documental(frappe, "Proceso", rows)


def _procedimientos_visibles(frappe, filters: dict[str, Any]) -> list[Any]:
	if not frappe.permissions.has_permission(
		"Procedimiento", ptype="read", print_logs=False
	):
		return []
	rows = frappe.get_list(
		"Procedimiento",
		filters=filters,
		fields=["*"],
		order_by="name asc",
	)
	return _filtrar_permiso_documental(frappe, "Procedimiento", rows)


def _proceso_visible(frappe, name: str):
	rows = _procesos_visibles(frappe, {"name": name})
	if len(rows) != 1:
		frappe.throw("Proceso inexistente o no visible", exc=frappe.PermissionError)
	return rows[0]


def _procedimiento_visible(frappe, name: str):
	rows = _procedimientos_visibles(frappe, {"name": name})
	if len(rows) != 1:
		frappe.throw("Procedimiento inexistente o no visible", exc=frappe.PermissionError)
	return rows[0]


def _filtrar_permiso_documental(frappe, doctype: str, rows: Iterable[Any]) -> list[Any]:
	visibles = []
	for row in rows:
		doc = frappe.get_doc({**row, "doctype": doctype})
		if frappe.permissions.has_permission(
			doctype,
			ptype="read",
			doc=doc,
			print_logs=False,
		):
			visibles.append(row)
	return visibles


def _tareas_por_procedimiento(frappe, procedimientos: Iterable[Any]) -> dict[str, list[dict[str, str]]]:
	procedimientos = [
		row
		for row in procedimientos
		if row.diagrama_flujo and str(row.diagrama_flujo).lower().endswith(".bpmn")
	]
	resultado = {row.name: [] for row in procedimientos}
	if not procedimientos:
		return resultado

	urls = [row.diagrama_flujo for row in procedimientos]
	files = frappe.get_list(
		"File",
		filters={"file_url": ["in", urls]},
		fields=[
			"name",
			"file_url",
			"file_size",
			"modified",
			"attached_to_doctype",
			"attached_to_name",
		],
		ignore_permissions=True,
	)
	por_vinculo: dict[tuple[str, str], list[Any]] = {}
	for file_row in files:
		clave = (file_row.file_url, file_row.attached_to_name)
		por_vinculo.setdefault(clave, []).append(file_row)

	for procedimiento in procedimientos:
		candidatos = por_vinculo.get(
			(procedimiento.diagrama_flujo, procedimiento.name), []
		)
		candidatos = [
			row
			for row in candidatos
			if row.attached_to_doctype == "Procedimiento"
		]
		if len(candidatos) != 1:
			continue
		file_row = candidatos[0]
		resultado[procedimiento.name] = _leer_tareas_file(frappe, file_row)
	return resultado


def _leer_tareas_file(frappe, file_row) -> list[dict[str, str]]:
	try:
		if int(file_row.file_size or 0) > MAX_BPMN_BYTES:
			raise BpmnInvalido("El BPMN excede el límite de 5 MiB")
		file_doc = frappe.get_doc("File", file_row.name)
		if not file_doc.has_permission("read"):
			return []
		return [
			{**tarea, "file_name": file_row.name}
			for tarea in extraer_tareas_bpmn(file_doc.get_content())
		]
	except (BpmnInvalido, OSError, UnicodeError) as exc:
		_log_bpmn_invalido(frappe, file_row, exc)
		return []


def _log_bpmn_invalido(frappe, file_row, exc: Exception) -> None:
	cache_key = (
		f"sgc:proceso-tree:bpmn-invalido:{file_row.name}:{file_row.modified}"
	)
	try:
		primero = frappe.cache.set(
			name=frappe.cache.make_key(cache_key),
			value=b"1",
			nx=True,
		)
	except Exception:
		# Si Redis no está disponible se omite el Error Log: fallar cerrado evita
		# que un BPMN defectuoso convierta una caída de cache en una tormenta.
		return
	if not primero:
		return
	frappe.log_error(
		message=f"No se proyectaron tareas del File {file_row.name}: {exc}",
		title="BPMN inválido en mapa de procesos",
	)


def _nodo_proceso(row, expandable: bool) -> dict[str, Any]:
	niveles = {"Macroproceso": "N0", "Proceso": "N1", "Subproceso": "N2"}
	return _payload_nodo(
		value=f"proceso:{row.name}",
		title=row.proceso or row.name,
		expandable=expandable,
		node_type=niveles.get(row.nivel_bpm, "N1"),
		doctype="Proceso",
		docname=row.name,
	)


def _nodo_procedimiento(row, expandable: bool) -> dict[str, Any]:
	return _payload_nodo(
		value=f"procedimiento:{row.name}",
		title=row.titulo or row.name,
		expandable=expandable,
		node_type="N3",
		doctype="Procedimiento",
		docname=row.name,
	)


def _nodo_tarea(procedimiento, tarea: dict[str, str]) -> dict[str, Any]:
	file_name = tarea["file_name"]
	return _payload_nodo(
		value=f"tarea:{file_name}:{tarea['id']}",
		title=tarea["name"],
		expandable=False,
		node_type="N4",
		doctype="Procedimiento",
		docname=procedimiento.name,
		file_name=file_name,
		bpmn_id=tarea["id"],
	)


def _payload_nodo(
	*,
	value: str,
	title: str,
	expandable: bool,
	node_type: str,
	doctype: str,
	docname: str,
	file_name: str | None = None,
	bpmn_id: str | None = None,
) -> dict[str, Any]:
	return {
		"value": value,
		"title": title,
		"expandable": bool(expandable),
		"node_type": node_type,
		"doctype": doctype,
		"docname": docname,
		"file_name": file_name,
		"bpmn_id": bpmn_id,
	}


def _rechazar_padre(frappe) -> None:
	frappe.throw("Nodo padre desconocido", exc=frappe.ValidationError)


def _frappe():
	import frappe

	return frappe


try:
	import frappe as _frappe_module
except ModuleNotFoundError:
	pass
else:
	get_children = _frappe_module.whitelist()(get_children)


def extraer_tareas_bpmn(content: str | bytes) -> list[dict[str, str]]:
	"""Devuelve las tareas BPMN reales en su orden documental.

	El parser no interpreta DTD ni entidades y exige identificadores únicos para
	evitar colisiones entre los nodos virtuales del Tree View.
	"""
	texto = _normalizar_contenido(content)
	texto_mayusculas = texto.upper()
	if "<!DOCTYPE" in texto_mayusculas or "<!ENTITY" in texto_mayusculas:
		raise BpmnInvalido("El BPMN no puede contener DTD ni declaraciones ENTITY")

	try:
		raiz = ET.fromstring(texto)
	except ET.ParseError as exc:
		raise BpmnInvalido("El contenido no es XML BPMN válido") from exc

	_ids_vistos: set[str] = set()
	for elemento in raiz.iter():
		identificador = elemento.get("id")
		if identificador is None:
			continue
		identificador = identificador.strip()
		if not identificador:
			continue
		if identificador in _ids_vistos:
			raise BpmnInvalido(f"El identificador BPMN está duplicado: {identificador}")
		_ids_vistos.add(identificador)

	tareas = []
	for elemento in raiz.iter():
		tipo = _nombre_local(elemento.tag)
		if tipo not in TIPOS_TAREA_BPMN:
			continue

		identificador = (elemento.get("id") or "").strip()
		if not identificador:
			raise BpmnInvalido("Todas las tareas BPMN deben tener un identificador")
		nombre = (elemento.get("name") or "").strip() or identificador
		tareas.append({"id": identificador, "name": nombre, "task_type": tipo})

	return tareas


def _normalizar_contenido(content: str | bytes) -> str:
	if isinstance(content, bytes):
		contenido_bytes = content
		try:
			texto = content.decode("utf-8-sig")
		except UnicodeDecodeError as exc:
			raise BpmnInvalido("El BPMN debe usar codificación UTF-8") from exc
	elif isinstance(content, str):
		texto = content
		contenido_bytes = content.encode("utf-8")
	else:
		raise BpmnInvalido("El contenido BPMN debe ser texto o bytes")

	if len(contenido_bytes) > MAX_BPMN_BYTES:
		raise BpmnInvalido("El BPMN excede el límite de 5 MiB")
	return texto


def _nombre_local(tag: str) -> str:
	return tag.rsplit("}", 1)[-1]
