# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

"""Indicadores de desempeño por proceso — motor lector (objetivo específico 3).

Responde una sola pregunta: **qué indicadores de desempeño tiene cada proceso
del Mapa de Procesos, y cuál es su última medición**. Es el consumidor de la
cadena que arma `Ficha Caracterizacion Proceso`:

    Proceso → Ficha Caracterizacion Proceso.indicadores[] → Indicador.proceso
            → Valor Indicador (última medición) + Ficha Indicador (meta/unidad)

Dos reglas de diseño, ambas innegociables:

1. **Nunca se infiere un indicador por coincidencia de texto.** El único nexo
   válido es el Link explícito `Indicador.proceso`, que escribe el controlador
   de la ficha. Lo que no tiene enlace explícito no se adivina: se omite y se
   reporta en el bloque `omitidos`.
2. **Indicador de proceso ≠ indicador de acreditación.** El discriminador es
   `Indicador.marco_normativo`: si lo tiene, es de acreditación y aquí no entra
   (la ficha además lo bloquea al declararlo).

LÍMITE CONOCIDO: hoy hay 25 `Proceso` cargados pero prácticamente ninguna ficha
de caracterización — las fichas SIPOC del Mapa de Procesos v8.0 son un dato que
la institución todavía no ha entregado. Por eso este motor devolverá casi todo
en `omitidos` con razón `proceso_sin_ficha`. Eso NO es un fallo del motor: es el
reflejo honesto de que falta el dato. La cadena queda conectada y verificable;
cargar fichas reales la llena sin tocar una línea de código.
"""

import frappe

# Razones de omisión (contrato estable: el frontend puede agruparlas).
OMITIDO_SIN_FICHA = "proceso_sin_ficha"
OMITIDO_SIN_INDICADORES = "ficha_sin_indicadores"
OMITIDO_INDICADOR_INEXISTENTE = "indicador_inexistente"
OMITIDO_INDICADOR_ACREDITACION = "indicador_de_acreditacion"
OMITIDO_SIN_MEDICION = "indicador_sin_medicion"


def _omitido(proceso, razon, indicador=None, detalle=""):
	"""Fila del bloque `omitidos`: qué se dejó fuera y por qué."""
	return {
		"proceso": proceso,
		"indicador": indicador,
		"razon": razon,
		"detalle": detalle,
	}


def _ficha_por_proceso(procesos):
	"""Mapa {proceso: name_de_la_ficha} en una consulta."""
	fichas = frappe.get_all(
		"Ficha Caracterizacion Proceso",
		filters={"proceso": ["in", procesos]},
		fields=["name", "proceso", "estado", "version"],
	)
	return {f["proceso"]: f for f in fichas}


def _indicadores_declarados(fichas):
	"""Mapa {name_ficha: [codigo_indicador, ...]} respetando el orden de la ficha."""
	if not fichas:
		return {}

	filas = frappe.get_all(
		"Indicador Proceso Link",
		filters={
			"parent": ["in", fichas],
			"parenttype": "Ficha Caracterizacion Proceso",
			"parentfield": "indicadores",
		},
		fields=["parent", "indicador", "idx"],
		order_by="parent asc, idx asc",
	)
	mapa = {}
	for f in filas:
		if not f.get("indicador"):
			continue
		mapa.setdefault(f["parent"], []).append(f["indicador"])
	return mapa


def _ultimo_valor(indicador):
	"""Última `Valor Indicador` del indicador, o None si nunca se midió.

	"Última" = mayor `fecha`; se desempata por `creation` porque `fecha` es
	opcional y varias mediciones pueden compartirla.
	"""
	valores = frappe.get_all(
		"Valor Indicador",
		filters={"indicador": indicador},
		fields=[
			"name",
			"valor_num",
			"valor_texto",
			"fecha",
			"periodo_academico",
			"programa_sede",
			"unidad_organica",
			"fuente",
		],
		order_by="fecha desc, creation desc",
		limit=1,
	)
	return valores[0] if valores else None


def _semantica_medicion(indicador):
	"""Meta/unidad/frecuencia del indicador, desde su `Ficha Indicador` (1:1)."""
	ficha = frappe.get_all(
		"Ficha Indicador",
		filters={"indicador": indicador},
		fields=[
			"name",
			"tipo_valor",
			"unidad",
			"formula",
			"linea_base",
			"valor_referencial",
			"frecuencia",
			"fuente_dato",
			"responsable",
		],
		limit=1,
	)
	return ficha[0] if ficha else {}


def _cumple_meta(valor_num, meta):
	"""True/False si hay meta y medición numérica; None si no se puede juzgar.

	Se compara "a mayor mejor" porque `valor_referencial` es un umbral mínimo
	(la propia descripción del campo dice "ID1 ≥ 60%"). Si algún indicador
	necesitara el sentido inverso, eso es un dato de la Ficha Indicador que hoy
	no existe: se devuelve el juicio que el dato soporta, no uno inventado.
	"""
	if meta in (None, 0) or valor_num is None:
		return None
	return valor_num >= meta


def indicadores_de_proceso(proceso):
	"""Indicadores de desempeño de UN proceso, con su última medición.

	Devuelve `{"proceso", "denominacion", "nivel", "ficha", "indicadores", "omitidos"}`.
	Un proceso sin ficha devuelve `indicadores` vacío y una fila en `omitidos`:
	no hay forma explícita de saber qué mide, y no se adivina.
	"""
	resultado = filas_por_proceso(procesos=[proceso])
	if resultado["procesos"]:
		datos = resultado["procesos"][0]
		datos["omitidos"] = resultado["omitidos"]
		return datos

	return {
		"proceso": proceso,
		"denominacion": "",
		"nivel": "",
		"ficha": None,
		"indicadores": [],
		"omitidos": resultado["omitidos"],
	}


def filas_por_proceso(procesos=None, nivel=None, estado_proceso=None):
	"""Núcleo del motor: un bloque por proceso + el bloque global de omitidos.

	Filtros opcionales:
	  - `procesos`: lista de códigos de `Proceso` (por defecto, todos).
	  - `nivel`: Estratégico / Clave / Soporte.
	  - `estado_proceso`: Borrador / Vigente / Obsoleto.
	"""
	filtros = {}
	if procesos:
		filtros["name"] = ["in", list(procesos)]
	if nivel:
		filtros["nivel"] = nivel
	if estado_proceso:
		filtros["estado"] = estado_proceso

	docs_proceso = frappe.get_all(
		"Proceso",
		filters=filtros,
		fields=["name", "proceso", "nivel", "estado", "responsable"],
		order_by="nivel asc, name asc",
	)

	fichas = _ficha_por_proceso([p["name"] for p in docs_proceso]) if docs_proceso else {}
	declarados = _indicadores_declarados([f["name"] for f in fichas.values()])

	salida = []
	omitidos = []

	for p in docs_proceso:
		ficha = fichas.get(p["name"])
		bloque = {
			"proceso": p["name"],
			"denominacion": p.get("proceso") or p["name"],
			"nivel": p.get("nivel") or "",
			"estado_proceso": p.get("estado") or "",
			"responsable": p.get("responsable") or "",
			"ficha": ficha["name"] if ficha else None,
			"estado_ficha": ficha.get("estado") if ficha else "",
			"indicadores": [],
		}

		if not ficha:
			omitidos.append(_omitido(
				p["name"], OMITIDO_SIN_FICHA,
				detalle="El proceso no tiene Ficha de Caracterización: no declara indicadores.",
			))
			salida.append(bloque)
			continue

		codigos = declarados.get(ficha["name"], [])
		if not codigos:
			omitidos.append(_omitido(
				p["name"], OMITIDO_SIN_INDICADORES,
				detalle="La ficha {0} no declara ningún indicador.".format(ficha["name"]),
			))
			salida.append(bloque)
			continue

		for codigo in codigos:
			ind = frappe.db.get_value(
				"Indicador", codigo, ["name", "nombre", "categoria", "marco_normativo"],
				as_dict=True,
			)
			if not ind:
				omitidos.append(_omitido(
					p["name"], OMITIDO_INDICADOR_INEXISTENTE, indicador=codigo,
					detalle="Declarado en {0} pero el Indicador no existe.".format(ficha["name"]),
				))
				continue

			if ind.get("marco_normativo"):
				# No debería llegar aquí (la ficha lo bloquea al guardar), pero
				# un dato histórico puede haberse cargado antes de esa regla.
				omitidos.append(_omitido(
					p["name"], OMITIDO_INDICADOR_ACREDITACION, indicador=codigo,
					detalle="Pertenece al marco {0}: es indicador de acreditación.".format(
						ind["marco_normativo"]
					),
				))
				continue

			ficha_ind = _semantica_medicion(codigo)
			valor = _ultimo_valor(codigo)
			meta = ficha_ind.get("valor_referencial")

			if not valor:
				omitidos.append(_omitido(
					p["name"], OMITIDO_SIN_MEDICION, indicador=codigo,
					detalle="Sin ningún Valor Indicador registrado.",
				))

			bloque["indicadores"].append({
				"indicador": codigo,
				"nombre": ind.get("nombre") or codigo,
				"categoria": ind.get("categoria") or "",
				"tipo_valor": ficha_ind.get("tipo_valor") or "",
				"unidad": ficha_ind.get("unidad") or "",
				"formula": ficha_ind.get("formula") or "",
				"frecuencia": ficha_ind.get("frecuencia") or "",
				"linea_base": ficha_ind.get("linea_base"),
				"meta": meta,
				"responsable": ficha_ind.get("responsable") or "",
				"valor_num": valor.get("valor_num") if valor else None,
				"valor_texto": (valor.get("valor_texto") or "") if valor else "",
				"fecha": valor.get("fecha") if valor else None,
				"periodo_academico": (valor.get("periodo_academico") or "") if valor else "",
				"fuente": (valor.get("fuente") or "") if valor else "",
				"medido": bool(valor),
				"cumple_meta": _cumple_meta(valor.get("valor_num") if valor else None, meta),
			})

		salida.append(bloque)

	return {"procesos": salida, "omitidos": omitidos}


@frappe.whitelist()
def tablero_indicadores_proceso(nivel=None, estado_proceso=None):
	"""Contrato del tablero de indicadores de proceso (objetivo específico 3).

	Añade a `filas_por_proceso` los totales de cabecera. Los totales cuentan
	SOLO lo que tiene enlace explícito; `procesos_sin_ficha` es la métrica que
	dice, sin maquillaje, cuánto del Mapa de Procesos sigue sin caracterizar.
	"""
	datos = filas_por_proceso(nivel=nivel, estado_proceso=estado_proceso)

	total_indicadores = sum(len(p["indicadores"]) for p in datos["procesos"])
	medidos = sum(
		1 for p in datos["procesos"] for i in p["indicadores"] if i["medido"]
	)
	cumplen = sum(
		1 for p in datos["procesos"] for i in p["indicadores"] if i["cumple_meta"] is True
	)
	sin_ficha = sum(1 for o in datos["omitidos"] if o["razon"] == OMITIDO_SIN_FICHA)

	datos["totales"] = {
		"procesos": len(datos["procesos"]),
		"procesos_sin_ficha": sin_ficha,
		"procesos_con_indicadores": sum(1 for p in datos["procesos"] if p["indicadores"]),
		"indicadores": total_indicadores,
		"indicadores_medidos": medidos,
		"indicadores_sin_medicion": total_indicadores - medidos,
		"indicadores_cumplen_meta": cumplen,
	}
	return datos
