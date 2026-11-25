"""Dibuja un `.bpmn` del SGC como SVG, sin navegador ni dependencias.

Los `.bpmn` de `docs/diagramas/bpmn/` traen su geometría (BPMN-DI: cajas, carriles y rutas de las
flechas), así que el SVG solo la pinta: no recoloca nada. Sirve para meter el flujo en un manual,
un tutorial o una guía de reunión, donde nadie va a abrir un modelador.

    python3 -m sgc.bpmn_svg docs/diagramas/bpmn/03-autoevaluacion.bpmn salida.svg
    python3 -m sgc.bpmn_svg docs/diagramas/bpmn            # todos, junto a cada .bpmn

No depende de Frappe: se puede correr en cualquier máquina con Python 3.
"""

import sys
import xml.etree.ElementTree as ET
from html import escape
from pathlib import Path

NS = {
	"bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
	"bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
	"dc": "http://www.omg.org/spec/DD/20100524/DC",
	"di": "http://www.omg.org/spec/DD/20100524/DI",
}
B = "{%s}" % NS["bpmn"]

# Colores con contraste suficiente en claro; el SVG lleva fondo propio para leerse igual en oscuro.
TINTA = "#1f2933"
TENUE = "#52606d"
FONDO = "#ffffff"
CARRILES = ("#f5f7fa", "#eef2f7")
TAREA = "#ffffff"
SISTEMA = "#f0f4f8"
INICIO = "#2f855a"
FIN = "#c53030"
NOTA = "#7b8794"

ANCHO_LETRA = 6.6  # px por carácter a 12 px: basta para partir líneas sin medir fuentes


def _partir(texto, ancho_px, tam=12):
	"""Parte `texto` en líneas que quepan en `ancho_px` (aproximado)."""
	max_c = max(4, int(ancho_px / (ANCHO_LETRA * tam / 12)))
	lineas = []
	for parrafo in (texto or "").split("\n"):
		actual = ""
		for palabra in parrafo.split():
			prueba = f"{actual} {palabra}".strip()
			if len(prueba) <= max_c:
				actual = prueba
			else:
				if actual:
					lineas.append(actual)
				actual = palabra
		lineas.append(actual)
	return [l for l in lineas if l] or [""]


def _texto(x, y, lineas, tam=12, ancla="middle", color=TINTA, peso="normal", centrado_v=True):
	alto = tam * 1.25
	y0 = y - (len(lineas) - 1) * alto / 2 if centrado_v else y
	partes = [
		f'<text x="{x:.1f}" y="{y0 + i * alto:.1f}" font-size="{tam}" text-anchor="{ancla}" '
		f'dominant-baseline="middle" fill="{color}" font-weight="{peso}">{escape(l)}</text>'
		for i, l in enumerate(lineas)
	]
	return "".join(partes)


def _cajas(raiz):
	cajas = {}
	for forma in raiz.iter("{%s}BPMNShape" % NS["bpmndi"]):
		b = forma.find("dc:Bounds", NS)
		if b is None:
			continue
		etiqueta = forma.find("bpmndi:BPMNLabel/dc:Bounds", NS)
		cajas[forma.get("bpmnElement")] = {
			"x": float(b.get("x")),
			"y": float(b.get("y")),
			"w": float(b.get("width")),
			"h": float(b.get("height")),
			"etiqueta": None
			if etiqueta is None
			else tuple(float(etiqueta.get(k)) for k in ("x", "y", "width", "height")),
		}
	return cajas


def _elementos(raiz):
	"""id → (tipo, nombre, elemento) para todo lo que tenga id en el modelo."""
	out = {}
	for el in raiz.iter():
		if not el.tag.startswith(B) or not el.get("id"):
			continue
		tipo = el.tag[len(B):]
		if tipo == "textAnnotation":
			t = el.find("bpmn:text", NS)
			nombre = t.text if t is not None else ""
		else:
			nombre = el.get("name") or ""
		out[el.get("id")] = (tipo, nombre, el)
	return out


def a_svg(xml_bytes):
	raiz = ET.fromstring(xml_bytes)
	cajas = _cajas(raiz)
	els = _elementos(raiz)
	if not cajas:
		raise ValueError("El .bpmn no trae geometría (BPMN-DI)")
	movidos = _sacar_de_la_cabecera(cajas, els)

	minx = min(c["x"] for c in cajas.values()) - 20
	miny = min(c["y"] for c in cajas.values()) - 20
	maxx = max(c["x"] + c["w"] for c in cajas.values()) + 20
	maxy = max(c["y"] + c["h"] for c in cajas.values()) + 20
	for borde in raiz.iter("{%s}BPMNEdge" % NS["bpmndi"]):
		for p in borde.findall("di:waypoint", NS):
			maxx = max(maxx, float(p.get("x")) + 20)
			maxy = max(maxy, float(p.get("y")) + 20)
	ancho, alto = maxx - minx, maxy - miny

	capas = {"pool": [], "carril": [], "flecha": [], "nodo": [], "nota": []}
	n_carril = 0

	for eid, c in cajas.items():
		tipo, nombre, el = els.get(eid, ("", "", None))
		x, y, w, h = c["x"], c["y"], c["w"], c["h"]
		cx, cy = x + w / 2, y + h / 2

		if tipo == "participant":
			capas["pool"].append(
				f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{FONDO}" stroke="{TINTA}" stroke-width="1.5"/>'
				f'<text transform="translate({x + 15} {cy}) rotate(-90)" font-size="13" text-anchor="middle" '
				f'dominant-baseline="middle" fill="{TINTA}" font-weight="600">{escape(nombre)}</text>'
			)
		elif tipo == "lane":
			relleno = CARRILES[n_carril % 2]
			n_carril += 1
			lineas = _partir(nombre, h - 10, 12)
			capas["carril"].append(
				f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{relleno}" stroke="{TENUE}" stroke-width="1"/>'
				f'<line x1="{x + 30}" y1="{y}" x2="{x + 30}" y2="{y + h}" stroke="{TENUE}" stroke-width="1"/>'
				f'<g transform="translate({x + 15} {cy}) rotate(-90)">{_texto(0, 0, lineas, 12, peso="600")}</g>'
			)
		elif tipo in ("userTask", "task", "manualTask", "serviceTask", "scriptTask", "sendTask", "receiveTask"):
			sistema = tipo in ("serviceTask", "scriptTask")
			discontinuo = ' stroke-dasharray="5 3"' if sistema else ""
			capas["nodo"].append(
				f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{SISTEMA if sistema else TAREA}" '
				f'stroke="{TINTA}" stroke-width="1.5"{discontinuo}/>'
				+ (f'<text x="{x + 8}" y="{y + 14}" font-size="11" fill="{TENUE}">⚙</text>' if sistema else "")
				+ (f'<g transform="translate({x + 6} {y + 5})" fill="none" stroke="{TENUE}" stroke-width="1">'
				   f'<circle cx="6" cy="4" r="3"/><path d="M0 13 q6 -8 12 0"/></g>' if tipo == "userTask" else "")
				+ _texto(cx, cy + 3, _partir(nombre, w - 12), 12)
			)
		elif tipo.endswith("Gateway"):
			capas["nodo"].append(
				f'<polygon points="{cx},{y} {x + w},{cy} {cx},{y + h} {x},{cy}" fill="{TAREA}" stroke="{TINTA}" stroke-width="1.5"/>'
				f'<path d="M{cx - 8},{cy - 8} L{cx + 8},{cy + 8} M{cx + 8},{cy - 8} L{cx - 8},{cy + 8}" stroke="{TINTA}" stroke-width="2.5"/>'
			)
			capas["nodo"].append(_etiqueta_debajo(c, nombre))
		elif tipo.endswith("Event"):
			r = w / 2
			if tipo == "startEvent":
				trazo, grosor = INICIO, 2
			elif tipo == "endEvent":
				trazo, grosor = FIN, 4
			else:
				trazo, grosor = TINTA, 1.5
			doble = (
				f'<circle cx="{cx}" cy="{cy}" r="{r - 3}" fill="none" stroke="{trazo}" stroke-width="1.2"/>'
				if tipo.startswith("intermediate") else ""
			)
			reloj = ""
			if el is not None and el.find("bpmn:timerEventDefinition", NS) is not None:
				reloj = (f'<circle cx="{cx}" cy="{cy}" r="{r - 7}" fill="none" stroke="{TINTA}" stroke-width="1"/>'
				         f'<path d="M{cx},{cy - r + 9} L{cx},{cy} L{cx + 5},{cy + 3}" fill="none" stroke="{TINTA}" stroke-width="1.2"/>')
			capas["nodo"].append(
				f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{TAREA}" stroke="{trazo}" stroke-width="{grosor}"/>' + doble + reloj
			)
			capas["nodo"].append(_etiqueta_debajo(c, nombre))
		elif tipo == "textAnnotation":
			lineas = _partir(" ".join((nombre or "").split()), w - 8, 11)
			capas["nota"].append(
				f'<path d="M{x + 12},{y} L{x},{y} L{x},{y + h} L{x + 12},{y + h}" fill="none" stroke="{NOTA}" stroke-width="1.2"/>'
				+ _texto(x + 6, y + 9, lineas, 11, ancla="start", color=TENUE, centrado_v=False)
			)

	for borde in raiz.iter("{%s}BPMNEdge" % NS["bpmndi"]):
		tipo, nombre, _ = els.get(borde.get("bpmnElement"), ("", "", None))
		pts = [_mover_punto(float(p.get("x")), float(p.get("y")), movidos) for p in borde.findall("di:waypoint", NS)]
		if len(pts) < 2:
			continue
		d = "M" + " L".join(f"{px},{py}" for px, py in pts)
		if tipo == "association":
			capas["flecha"].append(f'<path d="{d}" fill="none" stroke="{NOTA}" stroke-width="1" stroke-dasharray="3 3"/>')
			continue
		estilo = 'stroke-dasharray="6 4" marker-end="url(#msg)"' if tipo == "messageFlow" else 'marker-end="url(#flecha)"'
		capas["flecha"].append(f'<path d="{d}" fill="none" stroke="{TINTA}" stroke-width="1.4" {estilo}/>')
		if nombre:
			(ax, ay), (bx, by) = pts[len(pts) // 2 - 1], pts[len(pts) // 2]
			capas["flecha"].append(_texto((ax + bx) / 2, (ay + by) / 2 - 9, _partir(nombre, 140, 11), 11, color=TENUE))

	defs = (
		'<defs>'
		f'<marker id="flecha" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
		f'<path d="M0,0 L10,5 L0,10 z" fill="{TINTA}"/></marker>'
		f'<marker id="msg" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
		f'<path d="M0,0 L10,5 L0,10 z" fill="{FONDO}" stroke="{TINTA}"/></marker>'
		'</defs>'
	)
	cuerpo = "".join(capas["pool"] + capas["carril"] + capas["nota"] + capas["flecha"] + capas["nodo"])
	return (
		f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{minx} {miny} {ancho} {alto}" '
		f'width="{ancho:.0f}" height="{alto:.0f}" role="img" '
		f'font-family="system-ui, -apple-system, Segoe UI, Roboto, sans-serif">'
		f'<rect x="{minx}" y="{miny}" width="{ancho}" height="{alto}" fill="{FONDO}"/>'
		f"{defs}{cuerpo}</svg>\n"
	)


def _sacar_de_la_cabecera(cajas, els):
	"""Un evento dibujado sobre la franja del nombre del carril tapa ese nombre: se corre a la derecha.

	Es lo único que el dibujo corrige del layout, y solo en el SVG: el `.bpmn` no se toca.
	Devuelve [(caja_original, desplazamiento)] para mover también las puntas de sus flechas.
	"""
	carriles = [c for eid, c in cajas.items() if els.get(eid, ("",))[0] == "lane"]
	movidos = []
	for eid, c in cajas.items():
		if not els.get(eid, ("",))[0].endswith("Event"):
			continue
		for carril in carriles:
			dentro = carril["y"] <= c["y"] + c["h"] / 2 <= carril["y"] + carril["h"]
			limite = carril["x"] + 34
			if dentro and c["x"] < limite:
				original = dict(c)
				delta = limite + 6 - c["x"]
				c["x"] += delta
				if c["etiqueta"]:
					lx, ly, lw, lh = c["etiqueta"]
					c["etiqueta"] = (lx + delta, ly, lw, lh)
				movidos.append((original, delta))
				break
	return movidos


def _mover_punto(x, y, movidos):
	for c, delta in movidos:
		if c["x"] - 1 <= x <= c["x"] + c["w"] + 1 and c["y"] - 1 <= y <= c["y"] + c["h"] + 1:
			return (x + delta, y)
	return (x, y)


def _etiqueta_debajo(c, nombre):
	if not nombre:
		return ""
	if c["etiqueta"]:
		lx, ly, lw, lh = c["etiqueta"]
		return _texto(lx + lw / 2, ly + lh / 2, _partir(nombre, max(lw, 90), 11), 11, color=TENUE)
	return _texto(c["x"] + c["w"] / 2, c["y"] + c["h"] + 14, _partir(nombre, 110, 11), 11, color=TENUE, centrado_v=False)


def exportar(origen, destino=None):
	origen = Path(origen)
	destino = Path(destino) if destino else origen.with_suffix(".svg")
	destino.write_text(a_svg(origen.read_bytes()), encoding="utf-8")
	return destino


def exportar_carpeta(carpeta):
	return [exportar(p) for p in sorted(Path(carpeta).glob("*.bpmn"))]


if __name__ == "__main__":
	arg = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/diagramas/bpmn")
	if arg.is_dir():
		for p in exportar_carpeta(arg):
			print(p)
	else:
		print(exportar(arg, sys.argv[2] if len(sys.argv) > 2 else None))
