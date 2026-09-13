#!/usr/bin/env python3
"""Comprueba los BPMN versionados contra el generador sin modificar archivos."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sgc.bpmn import construir, layout_de, nombre_archivo, specs_de_workflows


def comprobar(directorio):
	errores = []
	specs = specs_de_workflows()
	if not specs:
		return ["No se descubrieron workflows; no se puede verificar la concordancia."]
	esperados = {nombre_archivo(s["document_type"]) for _, s in specs}
	actuales = {p.name for p in directorio.glob("*.bpmn")}
	for nombre in sorted(esperados - actuales):
		errores.append(f"Falta: {nombre}")
	for nombre in sorted(actuales - esperados):
		errores.append(f"Sin workflow de origen: {nombre}")
	for _, spec in specs:
		nombre = nombre_archivo(spec["document_type"])
		if nombre not in actuales:
			continue
		try:
			actual = (directorio / nombre).read_text(encoding="utf-8")
			esperado = construir(spec, layout_previo=layout_de(actual))
			if actual != esperado:
				errores.append(f"Diverge del código (regenerar): {nombre}")
		except (ValueError, OSError) as exc:
			errores.append(f"No verificable: {nombre}: {exc}")
	return errores


if __name__ == "__main__":
	carpeta = Path(__file__).resolve().parents[1] / "docs/diagramas/bpmn"
	fallos = comprobar(carpeta)
	if fallos:
		print("\n".join(fallos), file=sys.stderr)
		sys.exit(1)
	print("BPMN: inventario y contenido coinciden con el generador y sus specs.")
