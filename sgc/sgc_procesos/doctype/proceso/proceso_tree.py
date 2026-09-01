# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Lectura segura de la jerarquía compuesta del mapa de procesos."""

from __future__ import annotations

import xml.etree.ElementTree as ET

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
