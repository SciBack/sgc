# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Consolidador + generador del Informe de Autoevaluación (formato oficial SINEACE).

Dos piezas, alineadas al insumo D (`doc/specs/sgc-frappe/insumos/D-informe-e-indicadores.md`):

- `consolidar(autoevaluacion)`  -> dict tipado que la plantilla del Print Format itera.
  Es el "Script Report" del §1.2.3: un único punto que junta cabecera + estándares
  (con nivel, semáforo, criterios y evidencias) + vigencia. NO calcula juicios: solo
  ensambla lo que ya existe (Valoracion Estandar / Valoracion Criterio / Trazabilidad).

- `generar_pdf(autoevaluacion)` -> renderiza el Print Format a PDF con el motor Chrome
  de Frappe v16, fijando `frappe.local.lang = "es"` (evita el bug de locale de v16).

Reglas de datos (verificadas contra los .json reales del app):
- `Valoracion Estandar` y `Valoracion Criterio` son DocTypes NORMALES (no child tables);
  se consultan por su campo `autoevaluacion` (Link).
- `Valoracion Estandar.nivel` es un Link a `Nivel Escala` (istable); su valor es el `name`
  de la fila; se resuelve a la sigla NL/L/LP vía `sgc.scoring._sigla_nivel`.
- El árbol del marco (Elemento Marco, is_tree) da estándares (tipo=Estandar) y sus criterios
  (hijos por `parent_elemento_marco`). Reusamos los helpers de `sgc.scoring` cuando NO hay
  snapshot; si hay snapshot congelado, se recorren sus propias claves (ver abajo).
- Evidencias por estándar: `Trazabilidad` (evidencia + elemento_marco), sobre el estándar
  y sobre cada uno de sus criterios. Esto NO depende de Marco Normativo/Elemento Marco
  (es Trazabilidad + Evidencia + Documento Controlado), así que no ramifica por snapshot.

Inmutabilidad (Fase 3+4, fusionadas): `Autoevaluacion` es `is_submittable=1`; el workflow
nativo (`sgc.setup.f2_workflow.WF_AUTOEVAL`) dispara el submit automático (docstatus 0->1)
al llegar a "Cerrada". Justo antes de ese submit, otro módulo congela un snapshot INMUTABLE
del árbol del marco en `Autoevaluacion.marco_snapshot` (fieldtype JSON). Mientras la
Autoevaluación esté en curso (docstatus=0) este módulo sigue leyendo Marco Normativo/
Elemento Marco EN VIVO, tal como antes. Una vez enviada (docstatus=1), lee del snapshot
congelado — así una edición posterior al marco (reparenteo, texto corregido) NO cambia
retroactivamente un informe ya cerrado.

Contrato de `marco_snapshot` (lo puebla `sgc.sgc_nucleo.doctype.autoevaluacion` +
`sgc.scoring` antes del submit; este módulo SOLO lo lee):

    {
      "tomado_en": "<frappe.utils.now() -- datetime string>",
      "marco_normativo": "<Marco Normativo.name>",
      "escala_valoracion": "<Escala Valoracion.name o null>",
      "niveles": [{"sigla", "score", "orden", "es_aprobatorio"}, ...],
      "elementos": {
        "<Elemento Marco.name>": {
          "codigo", "denominacion", "texto_oficial", "tipo",
          "es_valorable", "peso", "parent_elemento_marco", "orden"
        }, ...
      }
    }

NOTA: el contrato NO incluye `nombre`/`ente` del propio Marco Normativo (solo su `name`
en "marco_normativo") — la cabecera sigue resolviendo esos dos campos en vivo contra
`Marco Normativo` siempre (con o sin snapshot). Tampoco se usa aquí `niveles`/
`escala_valoracion`: `_nivel_de_estandar` sigue resolviendo la sigla NL/L/LP vía
`sgc.scoring._sigla_nivel` (Nivel Escala), que queda fuera del alcance de este módulo.

MCP seam: la plantilla NO llama a estas funciones directamente. Consume el método
whitelisted `Autoevaluacion.datos_informe()` (contrato tipado, reservado para MCP),
que devuelve exactamente `consolidar(self.name)`.
"""

import frappe
from frappe.utils import formatdate

from sgc.scoring import (
    _sigla_nivel,
    _estandares_de_autoevaluacion,
    _criterios_de_estandar,
)

# --- Semáforo por nivel de logro (insumo D §1.2.4) --------------------------
#   NL  -> rojo   (No Logrado)
#   L   -> ámbar  (Logrado)
#   LP  -> verde  (Logrado Plenamente)
SEMAFORO_POR_NIVEL = {
    "NL": {"color": "rojo", "hex": "#cf222e"},
    "L": {"color": "ambar", "hex": "#bf8700"},
    "LP": {"color": "verde", "hex": "#1a7f37"},
}
SEMAFORO_SIN_DATO = {"color": "gris", "hex": "#57606a"}


# ===========================================================================
# Helpers internos de consolidación
# ===========================================================================

def _codigo_orden(codigo):
    """Clave de orden natural para códigos de estándar 'E1'..'E10'.

    Devuelve el entero tras el primer prefijo alfabético ('E10' -> 10) para que
    E2 quede antes de E10; si no parsea, cae a orden lexicográfico estable.
    """
    if not codigo:
        return (1, "")
    digits = "".join(ch for ch in codigo if ch.isdigit())
    if digits:
        return (0, int(digits))
    return (1, codigo)


def _snapshot_o_vivo(autoevaluacion):
    """El `marco_snapshot` congelado de la Autoevaluación, o `None` si no aplica.

    Solo se usa cuando la Autoevaluación ya fue enviada (`docstatus == 1` — lo
    dispara el submit automático del workflow nativo al llegar a "Cerrada").
    Mientras está en curso (`docstatus == 0`) devuelve `None` y el caller cae
    al camino en vivo de siempre (comportamiento SIN cambios para Draft).

    Defensivo a propósito: autoevaluacion inexistente, `marco_snapshot` vacío/
    ausente, o JSON corrupto -> `None` (nunca revienta el informe; simplemente
    no congela). Un informe de una Autoevaluación EN CURSO jamás debe romperse
    por esto.

    `marco_snapshot` es fieldtype JSON: según el backend de BD, Frappe puede
    entregarlo ya parseado (dict, típico en Postgres vía psycopg2) o como
    string JSON crudo (típico si el driver no autoconvierte) — `frappe.parse_json`
    soporta ambos casos (passthrough si ya es dict). Mismo patrón que
    `sgc.scoring._snapshot_de_autoevaluacion`, que congela/lee el mismo campo.
    """
    row = frappe.db.get_value(
        "Autoevaluacion", autoevaluacion, ["docstatus", "marco_snapshot"], as_dict=True
    )
    if not row or frappe.utils.cint(row.get("docstatus")) != 1 or not row.get("marco_snapshot"):
        return None
    snap = row.get("marco_snapshot")
    if isinstance(snap, str):
        try:
            snap = frappe.parse_json(snap)
        except Exception:
            return None
    if not isinstance(snap, dict) or not snap.get("elementos"):
        return None
    return snap


def _elemento_meta(elemento_marco, snap):
    """Metadata (codigo, denominacion, texto_oficial) de un Elemento Marco.

    Lee del snapshot congelado (`snap["elementos"][name]`) si se pasó uno; si
    no, consulta Elemento Marco EN VIVO (comportamiento idéntico al de antes
    del snapshot).
    """
    if snap is not None:
        return snap["elementos"].get(elemento_marco) or {}
    return frappe.db.get_value(
        "Elemento Marco", elemento_marco,
        ["codigo", "denominacion", "texto_oficial"], as_dict=True,
    ) or {}


def _orden_elemento(name, snap):
    """Clave de orden estable (orden, codigo) para un Elemento Marco del snapshot."""
    meta = snap["elementos"].get(name) or {}
    orden = meta.get("orden")
    return (orden if orden is not None else 10**6, meta.get("codigo") or "")


def _estandares_del_marco(autoevaluacion, snap):
    """Los estándares (tipo=Estandar) del marco de la autoevaluación.

    Desde el snapshot congelado si se pasó uno (ordenados por `orden`, luego
    `codigo`, replicando el `order_by="orden asc, codigo asc"` de la consulta
    en vivo); si no, delega en `sgc.scoring._estandares_de_autoevaluacion`.
    """
    if snap is not None:
        nombres = [
            name for name, meta in snap["elementos"].items()
            if meta.get("tipo") == "Estandar"
        ]
        nombres.sort(key=lambda n: _orden_elemento(n, snap))
        return nombres
    return _estandares_de_autoevaluacion(autoevaluacion)


def _criterios_del_estandar(estandar_name, snap):
    """Criterios (hijos) assessable de un estándar.

    Desde el snapshot si se pasó uno (misma preferencia que el motor en vivo:
    prioriza `es_valorable`, cae a `tipo == "Criterio"` si el marco no lo
    denormalizó); si no, delega en `sgc.scoring._criterios_de_estandar`.
    """
    if snap is not None:
        hijos = [
            name for name, meta in snap["elementos"].items()
            if meta.get("parent_elemento_marco") == estandar_name
        ]
        valorables = [n for n in hijos if snap["elementos"][n].get("es_valorable")]
        elegidos = valorables or [
            n for n in hijos if (snap["elementos"][n].get("tipo") or "") == "Criterio"
        ]
        elegidos.sort(key=lambda n: _orden_elemento(n, snap))
        return elegidos
    return _criterios_de_estandar(estandar_name)


def _nivel_de_estandar(autoevaluacion, estandar_name):
    """(sigla, confirmado) del estándar.

    Prioriza el `nivel` oficial (Link a Nivel Escala) SOLO si `confirmado`;
    si no está confirmado, cae al `nivel_propuesto` (sigla directa del motor).
    Devuelve (sigla|None, bool_confirmado).
    """
    row = frappe.db.get_value(
        "Valoracion Estandar",
        {"autoevaluacion": autoevaluacion, "elemento_marco": estandar_name},
        ["nivel", "nivel_propuesto", "confirmado", "justificacion"],
        as_dict=True,
    )
    if not row:
        return None, False, None
    if row.get("confirmado") and row.get("nivel"):
        return _sigla_nivel(row["nivel"]), True, row.get("justificacion")
    # No confirmado: propuesta del motor (ya es una sigla NL/L/LP o vacío)
    prop = (row.get("nivel_propuesto") or "").strip() or None
    return prop, False, row.get("justificacion")


def _criterios_consolidados(autoevaluacion, estandar_name, snap=None):
    """Lista de dicts por criterio del estándar: ref_id, denominación, cumple, observación.

    `snap`: dict del snapshot congelado (ver `_snapshot_o_vivo`) o `None`. La
    metadata del criterio (codigo/denominacion/texto_oficial) sale de ahí si
    se pasó uno; `Valoracion Criterio` (el juicio del humano) siempre se lee
    en vivo — no forma parte del árbol del marco, no se congela.
    """
    filas = []
    for crit in _criterios_del_estandar(estandar_name, snap):
        meta = _elemento_meta(crit, snap)
        val = frappe.db.get_value(
            "Valoracion Criterio",
            {"autoevaluacion": autoevaluacion, "criterio": crit},
            ["cumple", "observacion", "debilidad", "estado"],
            as_dict=True,
        ) or {}
        filas.append({
            "ref_id": meta.get("codigo") or crit,
            "denominacion": meta.get("denominacion") or meta.get("texto_oficial") or "",
            "cumple": val.get("cumple") or "Sin valorar",
            "observacion": val.get("observacion") or "",
            "debilidad": val.get("debilidad") or "",
            "estado": val.get("estado") or "",
        })
    return filas


def _evidencias_de_elementos(elementos):
    """Evidencias vinculadas (vía Trazabilidad) a cualquiera de los `elementos` (estándar+criterios).

    Devuelve dicts deduplicados por código de evidencia: ev_id, titulo, doc_sgc, version, estado.
    """
    if not elementos:
        return []
    trazas = frappe.get_all(
        "Trazabilidad",
        filters={"elemento_marco": ["in", list(elementos)]},
        fields=["evidencia", "tipo_vinculo"],
    )
    vistos = {}
    for tz in trazas:
        ev = tz.get("evidencia")
        if not ev or ev in vistos:
            continue
        meta = frappe.db.get_value(
            "Evidencia", ev,
            ["codigo", "titulo", "estado", "documento_controlado", "archivo", "almacenamiento_uri"],
            as_dict=True,
        ) or {}
        doc_sgc = ""
        version = ""
        if meta.get("documento_controlado"):
            doc_sgc = meta["documento_controlado"]
            version = frappe.db.get_value(
                "Documento Controlado", meta["documento_controlado"], "version"
            ) or ""
        vistos[ev] = {
            "ev_id": meta.get("codigo") or ev,
            "titulo": meta.get("titulo") or "",
            "estado": meta.get("estado") or "",
            "doc_sgc": doc_sgc,
            "version": version,
            # El archivo real (M09) tiene prioridad; el URI de MinIO es legado.
            "uri": meta.get("archivo") or meta.get("almacenamiento_uri") or "",
            "vinculo": tz.get("tipo_vinculo") or "",
        }
    # Orden estable por código de evidencia
    return sorted(vistos.values(), key=lambda e: str(e["ev_id"]))


# ===========================================================================
# Consolidador principal
# ===========================================================================

def consolidar(autoevaluacion):
    """Arma el contexto completo del informe SINEACE para una Autoevaluación.

    Estructura devuelta (contrato tipado — no cambiar sin actualizar la plantilla):

        {
          "cabecera": {codigo, titulo, programa, sede, escuela, marco, marco_nombre,
                       ente, periodo, fecha, institucion, alcance, estado, responsable,
                       fecha_congelamiento, version_marco_congelado},
          "vigencia": {oficial, propuesta, texto},      # oficial = resultado_vigencia si lo fijó el humano
          "estandares": [
            {codigo, denominacion, texto_oficial, nivel, confirmado,
             semaforo{color,hex}, justificacion,
             criterios: [{ref_id, denominacion, cumple, observacion, debilidad, estado}],
             evidencias: [{ev_id, titulo, doc_sgc, version, estado, uri, vinculo}]}
          ],
          "resumen_valoracion": [{codigo, nivel, semaforo}],   # matriz-resumen de los 10 estándares
          "todas_evidencias": [ ... ],                          # unión para el Anexo 6
        }

    Inmutabilidad: si la Autoevaluación ya fue enviada (docstatus=1) y tiene un
    `marco_snapshot` congelado válido, "estandares"/"criterios" (codigo,
    denominacion, texto_oficial) salen de esa copia congelada, NO del árbol
    Elemento Marco en vivo — ver `_snapshot_o_vivo`. `cabecera.fecha_congelamiento`
    y `cabecera.version_marco_congelado` quedan vacíos si no hay snapshot (p.ej.
    Autoevaluación en curso, Draft).
    """
    ae = frappe.get_doc("Autoevaluacion", autoevaluacion)
    snap = _snapshot_o_vivo(autoevaluacion)

    # --- Cabecera (sección 1 del F.04) ---
    programa = sede = escuela = ""
    if ae.programa_sede:
        ps = frappe.db.get_value(
            "Programa Sede", ae.programa_sede,
            ["programa", "sede", "escuela"], as_dict=True
        ) or {}
        programa = ps.get("programa") or ""
        sede = ps.get("sede") or ""
        escuela = ps.get("escuela") or ""

    # marco_nombre/ente: el contrato de marco_snapshot NO congela estos dos campos
    # del propio Marco Normativo (solo su `name`, en snap["marco_normativo"]) —
    # se leen siempre en vivo, con o sin snapshot.
    marco_nombre = ente = ""
    if ae.marco_normativo:
        mn = frappe.db.get_value(
            "Marco Normativo", ae.marco_normativo, ["nombre", "ente"], as_dict=True
        ) or {}
        marco_nombre = mn.get("nombre") or ae.marco_normativo
        ente = mn.get("ente") or ""

    periodo_txt = ae.periodo_academico or ""

    institucion = (
        frappe.db.get_default("company")
        or frappe.db.get_single_value("System Settings", "app_name")
        or "Universidad Peruana Unión"
    )

    cabecera = {
        "codigo": ae.codigo,
        "titulo": ae.titulo or "",
        "programa": programa,
        "sede": sede,
        "escuela": escuela,
        "marco": ae.marco_normativo or "",
        "marco_nombre": marco_nombre,
        "ente": ente,
        "periodo": periodo_txt,
        "fecha": formatdate(frappe.utils.today(), "dd 'de' MMMM 'de' yyyy"),
        "institucion": institucion,
        "alcance": ae.alcance or "",
        "estado": ae.estado or "",
        "responsable": ae.responsable or "",
        # Congelamiento (Fase 3+4): solo presentes cuando hay snapshot; vacíos en
        # una Autoevaluación en curso — no se inventa una fecha/versión.
        "fecha_congelamiento": (snap.get("tomado_en") or "") if snap else "",
        "version_marco_congelado": (
            "{0}@{1}".format(snap.get("marco_normativo") or "", snap.get("tomado_en") or "")
            if snap else ""
        ),
    }

    # --- Estándares (sección 4, un bloque por estándar) ---
    estandares_out = []
    resumen = []
    todas_evid = {}
    for est in _estandares_del_marco(autoevaluacion, snap):
        meta = _elemento_meta(est, snap)
        sigla, confirmado, justificacion = _nivel_de_estandar(autoevaluacion, est)
        semaforo = SEMAFORO_POR_NIVEL.get(sigla, SEMAFORO_SIN_DATO)

        criterios = _criterios_consolidados(autoevaluacion, est, snap)
        elementos_evid = {est} | set(_criterios_del_estandar(est, snap))
        evidencias = _evidencias_de_elementos(elementos_evid)
        for e in evidencias:
            todas_evid.setdefault(e["ev_id"], e)

        estandares_out.append({
            "codigo": meta.get("codigo") or est,
            "denominacion": meta.get("denominacion") or "",
            "texto_oficial": meta.get("texto_oficial") or "",
            "nivel": sigla or "Sin valorar",
            "confirmado": bool(confirmado),
            "semaforo": semaforo,
            "justificacion": justificacion or "",
            "criterios": criterios,
            "evidencias": evidencias,
        })
        resumen.append({
            "codigo": meta.get("codigo") or est,
            "nivel": sigla or "Sin valorar",
            "semaforo": semaforo,
        })

    # Orden E1..E10 (natural, no lexicográfico)
    estandares_out.sort(key=lambda s: _codigo_orden(s["codigo"]))
    resumen.sort(key=lambda s: _codigo_orden(s["codigo"]))

    # --- Vigencia: oficial (humano) si existe, si no la propuesta del motor ---
    vigencia = {
        "oficial": ae.resultado_vigencia or "",
        "propuesta": ae.vigencia_propuesta or "",
        "texto": ae.resultado_vigencia or ae.vigencia_propuesta or "Pendiente",
    }

    return {
        "cabecera": cabecera,
        "vigencia": vigencia,
        "estandares": estandares_out,
        "resumen_valoracion": resumen,
        "todas_evidencias": sorted(todas_evid.values(), key=lambda e: str(e["ev_id"])),
    }


# ===========================================================================
# Generación del PDF (motor Chrome de v16)
# ===========================================================================

PRINT_FORMAT = "Informe de Autoevaluacion SINEACE"


def generar_pdf(autoevaluacion, adjuntar=False):
    """Renderiza el Print Format a PDF vía el motor Chrome de Frappe v16.

    - Fija `frappe.local.lang = "es"` ANTES de renderizar: evita el bug de locale de v16
      (formatdate/traducciones que fallan si el lang de la request viene vacío/None).
    - Usa `pdf_generator="chrome"` (soporta flexbox; wkhtmltopdf no).
    - Si `adjuntar=True`, guarda el PDF como File adjunto a la Autoevaluación y devuelve
      dict con nombre de archivo + url; si no, devuelve los bytes crudos.
    """
    frappe.local.lang = "es"

    pdf_bytes = frappe.get_print(
        "Autoevaluacion",
        autoevaluacion,
        print_format=PRINT_FORMAT,
        as_pdf=True,
        pdf_generator="chrome",
    )

    if not adjuntar:
        return pdf_bytes

    fname = "Informe-Autoevaluacion-{0}.pdf".format(autoevaluacion)
    filedoc = frappe.get_doc({
        "doctype": "File",
        "file_name": fname,
        "attached_to_doctype": "Autoevaluacion",
        "attached_to_name": autoevaluacion,
        "is_private": 1,
        "content": pdf_bytes,
    })
    filedoc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"file_name": filedoc.file_name, "file_url": filedoc.file_url}
