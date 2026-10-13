"""
Cargador de marcos normativos desde un YAML en formato intuitem
===============================================================
Puebla los DocTypes del marco (Marco Normativo, Escala Valoracion + Nivel Escala,
Elemento Marco [Tree], Indicador, Ficha Indicador, Indicador Criterio) a partir
de un YAML de biblioteca intuitem. Nació para el modelo CONEAU Programas 2025 y
conserva el nombre del módulo, pero desde #47 no sabe nada de ningún marco: los
códigos salen del bloque `sgc:` del propio YAML.

**No corre solo.** Hasta #47 el arranque común cargaba CONEAU en TODA instancia
nueva, fuera o no de una institución que acredita con él. Ahora qué marcos carga
una instancia lo declara su `site_config` (`sgc_marcos`) y lo aplica
`sgc.setup.marcos_normativos`, que es quien llama a este cargador.

Idempotente: busca por código antes de crear. Reejecutable sin duplicar, y nunca
modifica ni borra lo ya cargado.

Bloque `sgc:` del YAML (todo opcional):
    escala              código de la Escala Valoracion     (def.: <ref_id>-ESCALA)
    escala_nombre       su nombre                          (def.: «<nombre del marco> — escala»)
    ente                ente emisor del Marco Normativo    (def.: vacío; es un Select con opciones fijas)
    prefijo_elementos   prefijo de los Elemento Marco      (def.: el ref_id del marco)
    prefijo_indicadores prefijo de los Indicador           (def.: el ref_id del marco + «-»)

Mapeo YAML -> DocTypes (F2-CONTRATO.md §3, verificado contra los .json F1):
  scores_definition          -> Escala Valoracion + hijos Nivel Escala (tabla `niveles`)
  objects.framework          -> Marco Normativo (código = ref_id del framework)
  requirement_nodes          -> Elemento Marco (Tree), padres antes que hijos (orden por depth)
  objects.reference_controls -> Indicador + Ficha Indicador
  reference_controls por nodo -> Indicador Criterio (indicador <-> Elemento Marco)
"""

import os
import re

import frappe
import yaml

# Siglas por score cuando el nombre del nivel no la trae («NL — Estándar no logrado» sí).
SCORE_SIGLA = {0: "NL", 1: "L", 2: "LP"}


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _load_yaml(yaml_path):
    if not yaml_path or not os.path.exists(yaml_path):
        frappe.throw("No se encontró el YAML del marco en '{0}'.".format(yaml_path))
    with open(yaml_path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def configuracion(data):
    """Los códigos con los que se carga el marco: bloque `sgc:` del YAML o sus valores por defecto."""
    framework = ((data or {}).get("objects") or {}).get("framework") or {}
    marco = framework.get("ref_id") or (data or {}).get("ref_id")
    if not marco:
        frappe.throw("El YAML del marco no declara `ref_id` en objects.framework: no hay código de marco.")
    extra = (data or {}).get("sgc") or {}
    nombre = framework.get("name") or data.get("name") or marco
    return {
        "marco": marco,
        "escala": extra.get("escala") or f"{marco}-ESCALA",
        "escala_nombre": extra.get("escala_nombre") or f"{nombre} — escala",
        "ente": extra.get("ente") or "",
        "prefijo_elementos": extra.get("prefijo_elementos") or marco,
        "prefijo_indicadores": extra["prefijo_indicadores"] if "prefijo_indicadores" in extra else f"{marco}-",
    }


def _urn_ref_id(urn):
    """El sufijo tras el último ':' de un urn de req_node (root, e1, e1.1, ...)."""
    return urn.rsplit(":", 1)[-1]


def _sigla_from_urn_function(urn, cfg):
    """urn ...:function:...:id8 -> '<prefijo>ID8' (para casar con reference_controls)."""
    return cfg["prefijo_indicadores"] + urn.rsplit(":", 1)[-1].upper()


# ---------------------------------------------------------------------------
# 1. Escala + Niveles
# ---------------------------------------------------------------------------
def _cargar_escala(framework, cfg, contadores):
    scores = framework.get("scores_definition") or []

    if frappe.db.exists("Escala Valoracion", cfg["escala"]):
        contadores["escalas_existentes"] += 1
        return

    escala = frappe.new_doc("Escala Valoracion")
    escala.codigo = cfg["escala"]
    escala.nombre = cfg["escala_nombre"]
    escala.tipo = "ordinal"
    escala.min_score = framework.get("min_score", 0)
    escala.max_score = framework.get("max_score", 2)

    for sc in scores:
        score = sc.get("score")
        # name viene como "NL — Estándar no logrado"; separamos sigla/etiqueta.
        nombre_full = sc.get("name", "") or ""
        sigla, etiqueta = SCORE_SIGLA.get(score, ""), nombre_full
        for sep in ("—", "-"):
            if sep in nombre_full:
                sigla, etiqueta = (t.strip() for t in nombre_full.split(sep, 1))
                break
        escala.append(
            "niveles",
            {
                "codigo": sigla or str(score),
                "sigla": sigla,
                "etiqueta": etiqueta,
                "score": score,
                "orden": score,
                # LP (score máximo) = logrado plenamente -> aprobatorio pleno; L también cumple.
                "es_aprobatorio": 1 if score >= 1 else 0,
                "definicion": sc.get("description", ""),
            },
        )
        contadores["niveles"] += 1

    escala.flags.ignore_permissions = True
    escala.insert()
    contadores["escalas"] += 1


# ---------------------------------------------------------------------------
# 2. Marco Normativo
# ---------------------------------------------------------------------------
def _cargar_marco(data, framework, cfg, contadores):
    if frappe.db.exists("Marco Normativo", cfg["marco"]):
        contadores["marcos_existentes"] += 1
        return

    marco = frappe.new_doc("Marco Normativo")
    marco.codigo = cfg["marco"]
    marco.nombre = framework.get("name") or data.get("name") or cfg["marco"]
    marco.ente = cfg["ente"]
    marco.version = str(data.get("version", "1"))
    pub = data.get("publication_date")
    if pub:
        marco.vigente_desde = str(pub)
    marco.estado = "vigente"
    marco.escala_valoracion = cfg["escala"]
    marco.nota_normativa = framework.get("description") or data.get("description") or ""
    marco.flags.ignore_permissions = True
    marco.insert()
    contadores["marcos"] += 1


# ---------------------------------------------------------------------------
# 3. Elemento Marco (Tree)
# ---------------------------------------------------------------------------
# depth -> tipo del DocType Elemento Marco (Select).
DEPTH_TIPO = {1: "Dimension", 2: "Estandar", 3: "Criterio"}


def _codigo_elemento(ref_id, urn, cfg):
    """
    Código único y estable del Elemento Marco.
    Prefijamos con el marco para no colisionar con otros marcos ya cargados
    que también usan ref_id tipo '1.1'.
    """
    base = ref_id if ref_id else _urn_ref_id(urn)
    return "{0}-{1}".format(cfg["prefijo_elementos"], base)


def _cargar_elementos(framework, cfg, contadores):
    nodes = framework.get("requirement_nodes") or []

    # urn -> codigo (para resolver parent_urn -> parent_elemento_marco)
    urn_a_codigo = {}
    for n in nodes:
        urn_a_codigo[n["urn"]] = _codigo_elemento(n.get("ref_id"), n["urn"], cfg)

    # Crear en orden de depth ascendente (padres antes que hijos) para que el Tree resuelva.
    for node in sorted(nodes, key=lambda n: n.get("depth", 99)):
        codigo = _codigo_elemento(node.get("ref_id"), node["urn"], cfg)
        if frappe.db.exists("Elemento Marco", codigo):
            contadores["elementos_existentes"] += 1
            continue

        depth = node.get("depth", 0)
        parent_urn = node.get("parent_urn")
        parent_codigo = urn_a_codigo.get(parent_urn) if parent_urn else None
        assessable = 1 if node.get("assessable") else 0

        doc = frappe.new_doc("Elemento Marco")
        doc.codigo = codigo
        doc.denominacion = node.get("name") or ""
        doc.marco_normativo = cfg["marco"]
        doc.nivel = str(depth)
        doc.tipo = DEPTH_TIPO.get(depth, "Componente")
        doc.texto_oficial = node.get("description") or ""
        doc.nota_normativa = node.get("annotation") or ""
        doc.es_valorable = assessable
        # atributos: guardamos ref_id, urn y depth para trazabilidad (no hay campo dedicado).
        doc.atributos = frappe.as_json(
            {
                "ref_id": node.get("ref_id"),
                "urn": node["urn"],
                "depth": depth,
                "assessable": bool(assessable),
            }
        )
        # is_group para no-hojas (raíz y estándares con criterios).
        doc.is_group = 1 if depth < 3 else 0
        if parent_codigo:
            doc.parent_elemento_marco = parent_codigo

        doc.flags.ignore_permissions = True
        doc.insert()
        contadores["elementos"] += 1
        if depth == 2:
            contadores["estandares"] += 1
        elif depth == 3:
            contadores["criterios"] += 1

    return urn_a_codigo


# ---------------------------------------------------------------------------
# 4. Indicador + Ficha Indicador
# ---------------------------------------------------------------------------
# Etiquetas del bloque description de cada ficha ID#.
_LABELS = {
    "objetivo": "OBJETIVO DE MEDICIÓN:",
    "referencial": "VALOR REFERENCIAL / UMBRAL:",
    "interpretacion": "INTERPRETACIÓN:",
    "fuente": "FUENTE DE INFORMACIÓN:",
    "variables": "VARIABLES:",
    "formula": "FORMA DE CÁLCULO:",
    "periodicidad": "PERIODICIDAD (frecuencia de cálculo):",
    "notas": "NOTAS:",
    "tipo_dato": "Tipo de dato:",
}


def _parse_ficha(description):
    """Extrae los campos etiquetados del `description` de un indicador."""
    text = description or ""
    out = {}
    for key, label in _LABELS.items():
        # Captura desde la etiqueta hasta la siguiente etiqueta conocida (o el 📖 Fuente / fin).
        # Construimos un lookahead con todas las demás etiquetas.
        others = [re.escape(l) for k, l in _LABELS.items() if k != key]
        others.append(re.escape("📖 Fuente"))
        stop = "|".join(others)
        pat = re.compile(
            re.escape(label) + r"\s*(.*?)(?=\n\s*(?:" + stop + r")|\Z)",
            re.DOTALL,
        )
        m = pat.search(text)
        if m:
            out[key] = m.group(1).strip()
    return out


# valor_referencial: primer número (%, con o sin decimales) en el texto "ID# ≥ 60%".
_RE_NUM = re.compile(r"(\d+(?:[.,]\d+)?)\s*%?")


def _num_from(txt):
    if not txt:
        return None
    m = _RE_NUM.search(txt)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


# margen de error: "±3%" -> 3.0
_RE_MARGEN = re.compile(r"±\s*(\d+(?:[.,]\d+)?)\s*%")


def _margen_from(txt):
    if not txt:
        return None
    m = _RE_MARGEN.search(txt)
    if not m:
        return None
    return float(m.group(1).replace(",", "."))


def _tipo_valor_from(tipo_dato_txt):
    """'Tipo de dato: Porcentaje' -> 'porcentaje'; 'Promedio' -> 'numerico'."""
    t = (tipo_dato_txt or "").lower()
    if "porcentaje" in t:
        return "porcentaje"
    if "promedio" in t or "ratio" in t:
        return "ratio" if "ratio" in t else "numerico"
    if "número" in t or "numero" in t or "cantidad" in t:
        return "numerico"
    return "numerico"


def _frecuencia_from(periodicidad_txt):
    p = (periodicidad_txt or "").lower()
    if "semestr" in p:
        return "semestral"
    if "promoc" in p:
        return "por_promocion"
    if "anual" in p:
        return "anual"
    return None


def _categoria_from(indicador):
    """Naturaleza del dato: de satisfacción si lo es, de proceso en los demás casos.

    Todos los ID vienen con category=process en el YAML. Afinamos según naturaleza
    del indicador (el DocType tiene: Acreditacion/Gestion/Proceso/Satisfaccion/Otra).

    **Que no devuelva nunca `Acreditacion` es deliberado, no un olvido.** Estos
    indicadores son del modelo Coneau, así que acreditan — pero eso lo declara su
    `marco_normativo`, que es el campo que consulta `sgc.marcos`. La categoría dice
    de qué naturaleza es el dato. Marcarlos aquí como `Acreditacion` perdería esa
    distinción y además ocultaría el Link a `proceso`, que depende de esta misma
    categoría. Ver `f20_categoria_indicador`.
    """
    nombre = (indicador.get("name") or "").lower()
    if "satisf" in nombre:
        return "Satisfaccion"
    return "Proceso"


def _cargar_indicadores(framework, cfg, contadores):
    controls = framework.get("reference_controls") or []
    for ctrl in controls:
        codigo = cfg["prefijo_indicadores"] + ctrl.get("ref_id")  # CONEAU: 'ID1'..'ID29', sin prefijo
        if frappe.db.exists("Indicador", codigo):
            contadores["indicadores_existentes"] += 1
            continue

        parsed = _parse_ficha(ctrl.get("description"))

        ind = frappe.new_doc("Indicador")
        ind.codigo = codigo
        ind.nombre = ctrl.get("name") or codigo
        ind.marco_normativo = cfg["marco"]
        ind.categoria = _categoria_from(ctrl)
        ind.flags.ignore_permissions = True
        ind.insert()
        contadores["indicadores"] += 1

        # Ficha Indicador (1:1 con el indicador). Idempotente por link `indicador`.
        if not frappe.db.exists("Ficha Indicador", {"indicador": codigo}):
            ficha = frappe.new_doc("Ficha Indicador")
            ficha.indicador = codigo
            ficha.objetivo = parsed.get("objetivo", "")
            ficha.tipo_valor = _tipo_valor_from(parsed.get("tipo_dato"))
            ficha.formula = parsed.get("formula", "")
            # variables: texto libre "SIGLA: definición · SIGLA: ..." -> JSON como lista.
            var_txt = parsed.get("variables", "")
            if var_txt:
                partes = [v.strip() for v in var_txt.split("·") if v.strip()]
                ficha.variables = frappe.as_json(partes)
            ficha.valor_referencial = _num_from(parsed.get("referencial"))
            margen = _margen_from(parsed.get("referencial"))
            if margen is not None:
                ficha.margen_error = margen
                ficha.regla_evolucion = 1  # ±3% + evolución (Sección IX)
            ficha.interpretacion = parsed.get("interpretacion", "")
            ficha.frecuencia = _frecuencia_from(parsed.get("periodicidad"))
            ficha.fuente_dato = parsed.get("fuente", "")
            ficha.notas = parsed.get("notas", "")
            # dominio_dato: satisfacción -> D4; estadístico/porcentaje calculado -> D2. Si dudoso, en blanco.
            cat = ind.categoria
            if cat == "Satisfaccion":
                ficha.dominio_dato = "D4"
            elif ficha.tipo_valor in ("porcentaje", "numerico", "ratio"):
                ficha.dominio_dato = "D2"
            ficha.flags.ignore_permissions = True
            ficha.insert()
            contadores["fichas"] += 1


# ---------------------------------------------------------------------------
# 5. Indicador Criterio (link Indicador <-> Elemento Marco del estándar)
# ---------------------------------------------------------------------------
def _cargar_indicador_criterio(framework, urn_a_codigo, cfg, contadores):
    # Indicador Criterio es CHILD de Indicador (tabla `criterios`): se ANEXA al
    # padre, no se inserta suelto. Agrupamos estándares por indicador.
    from collections import defaultdict
    pares = defaultdict(set)  # sigla indicador -> {codigo elemento_marco (estándar)}
    for node in framework.get("requirement_nodes") or []:
        controls = node.get("reference_controls") or []
        if not controls:
            continue
        elem_codigo = urn_a_codigo.get(node["urn"])
        if not elem_codigo:
            continue
        for ctrl_urn in controls:
            sigla = _sigla_from_urn_function(ctrl_urn, cfg)  # 'ID8'
            if not frappe.db.exists("Indicador", sigla):
                contadores["links_indicador_faltante"] += 1
                continue
            pares[sigla].add(elem_codigo)
    for sigla, elems in pares.items():
        ind = frappe.get_doc("Indicador", sigla)
        existentes = {r.elemento_marco for r in (ind.get("criterios") or [])}
        nuevos = sorted(elems - existentes)
        contadores["links_existentes"] += len(elems) - len(nuevos)
        for elem in nuevos:
            ind.append("criterios", {"indicador": sigla, "elemento_marco": elem})
            contadores["links"] += 1
        if nuevos:
            ind.flags.ignore_permissions = True
            ind.save()


# ---------------------------------------------------------------------------
# Orquestación
# ---------------------------------------------------------------------------
def run(yaml_path, commit=True):
    """Carga el marco del YAML. Devuelve los contadores (creados / ya existentes).

    `commit=False` deja la transacción abierta: lo usan los tests, que la deshacen.
    """
    in_patch = frappe.flags.in_patch
    frappe.flags.in_patch = True
    try:
        data = _load_yaml(yaml_path)
        cfg = configuracion(data)
        objects = (data or {}).get("objects") or {}
        framework = objects.get("framework") or {}
        # reference_controls está a nivel de `objects`, no de framework, en intuitem.
        framework.setdefault("reference_controls", objects.get("reference_controls") or [])

        contadores = {
            "escalas": 0, "escalas_existentes": 0, "niveles": 0,
            "marcos": 0, "marcos_existentes": 0,
            "elementos": 0, "elementos_existentes": 0, "estandares": 0, "criterios": 0,
            "indicadores": 0, "indicadores_existentes": 0, "fichas": 0,
            "links": 0, "links_existentes": 0, "links_indicador_faltante": 0,
        }

        _cargar_escala(framework, cfg, contadores)
        _cargar_marco(data, framework, cfg, contadores)
        urn_a_codigo = _cargar_elementos(framework, cfg, contadores)
        _cargar_indicadores(framework, cfg, contadores)
        _cargar_indicador_criterio(framework, urn_a_codigo, cfg, contadores)
    finally:
        frappe.flags.in_patch = in_patch

    if commit:
        frappe.db.commit()

    print("  Marco {0}: {1}".format(cfg["marco"], resumen(contadores)))
    return contadores


def resumen(c):
    """Una línea: lo creado y lo que ya estaba."""
    return (
        "marco {marcos}/{marcos_existentes} · escala {escalas}/{escalas_existentes} ({niveles} niveles) · "
        "elementos {elementos}/{elementos_existentes} · indicadores {indicadores}/{indicadores_existentes} "
        "({fichas} fichas) · vínculos {links}/{links_existentes}  [creados/ya existentes]"
    ).format(**c)
