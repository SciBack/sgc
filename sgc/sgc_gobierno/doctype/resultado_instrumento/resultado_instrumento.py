# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""M12 — Resultado de Instrumento + tabulación.

Captura un resultado tabulado de una `Aplicacion Instrumento`: por dimensión
(p. ej. "Trato del personal", "Infraestructura"), su `valor` (media Likert, %,
etc.), la `unidad`, el `n` (respuestas que sustentan ese valor) y la
`fecha_corte`. Opcionalmente materializa un `Valor Indicador` fechado que el
motor de indicadores lee (A2).

El DocType no tiene campo `estado` de flujo → NO lleva Workflow.

`tabular_aplicacion` es el método whitelisted de agregación que consume un
tablero: promedio simple, promedio ponderado por `n` y desglose por dimensión.

`publicar_valores_indicador` es el PUENTE Encuestas -> Indicadores: al cerrar la
`Aplicacion Instrumento` materializa un `Valor Indicador` (fuente "encuesta") por
cada Indicador DECLARADO y escribe el back-link `valor_indicador` en las filas
que lo sustentan. El enlace al Indicador es siempre EXPLÍCITO (campo `indicador`
de la fila, o herencia de `Instrumento.indicador`): nunca se infiere desde el
texto libre de `dimension`.
"""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime, nowdate


class ResultadoInstrumento(Document):
    def validate(self):
        if self.dimension:
            self.dimension = self.dimension.strip()

        # El n (tamaño que sustenta el valor) no puede ser negativo.
        if self.n is not None and self.n < 0:
            frappe.throw(_("El n (número de respuestas) no puede ser negativo."))

        # Si la unidad es un porcentaje, el valor debe estar en [0, 100].
        if self.unidad and "%" in self.unidad and self.valor is not None:
            if self.valor < 0 or self.valor > 100:
                frappe.throw(
                    _("Un valor en porcentaje debe estar entre 0 y 100 (recibido {0}).").format(
                        self.valor
                    )
                )

        # Fecha de corte por defecto: el fin del campo de la aplicación, o hoy.
        if not self.fecha_corte and self.aplicacion_instrumento:
            fin = frappe.db.get_value(
                "Aplicacion Instrumento", self.aplicacion_instrumento, "fecha_fin"
            )
            self.fecha_corte = fin or nowdate()


# ===========================================================================
# Tabulación / agregación (consumo de tablero)
# ===========================================================================

@frappe.whitelist()
def tabular_aplicacion(aplicacion):
    """Agrega los Resultado Instrumento de una aplicación para un tablero.

    Devuelve, sobre todas las filas de resultado de la aplicación:
      - `n_resultados`: cuántas filas de resultado hay.
      - `n_total`: suma de los `n` (respuestas totales que sustentan los valores).
      - `promedio`: media simple de los `valor`.
      - `promedio_ponderado`: media de los `valor` ponderada por `n`.
      - `dimensiones`: desglose por dimensión con su promedio (simple y
        ponderado), su `n` y el porcentaje de la muestra que representa.

    Whitelisted: respeta permisos del DocType al leer.
    """
    if not aplicacion:
        frappe.throw(_("Falta la aplicación de instrumento a tabular."))
    if not frappe.db.exists("Aplicacion Instrumento", aplicacion):
        frappe.throw(_("La aplicación de instrumento {0} no existe.").format(aplicacion))

    filas = frappe.get_all(
        "Resultado Instrumento",
        filters={"aplicacion_instrumento": aplicacion},
        fields=["dimension", "indicador", "valor", "unidad", "n", "fecha_corte"],
        order_by="dimension asc",
    )

    n_resultados = len(filas)

    # --- Agregación global ---
    valores = [f.valor for f in filas if f.valor is not None]
    promedio = round(sum(valores) / len(valores), 4) if valores else None

    n_total = sum((f.n or 0) for f in filas)
    suma_pond = sum((f.valor or 0) * (f.n or 0) for f in filas)
    promedio_ponderado = round(suma_pond / n_total, 4) if n_total else None

    # --- Desglose por dimensión ---
    acum = {}
    for f in filas:
        dim = f.dimension or _("(sin dimensión)")
        d = acum.setdefault(
            dim,
            {"dimension": dim, "n_resultados": 0, "valores": [],
             "n": 0, "suma_pond": 0.0, "unidad": f.unidad,
             "indicador": f.indicador},
        )
        d["n_resultados"] += 1
        if f.valor is not None:
            d["valores"].append(f.valor)
        d["n"] += (f.n or 0)
        d["suma_pond"] += (f.valor or 0) * (f.n or 0)
        # Conserva la primera unidad no vacía vista para la dimensión.
        if not d["unidad"] and f.unidad:
            d["unidad"] = f.unidad
        # Ídem con el indicador declarado (informativo para el tablero).
        if not d["indicador"] and f.indicador:
            d["indicador"] = f.indicador

    dimensiones = []
    for dim, d in acum.items():
        prom = round(sum(d["valores"]) / len(d["valores"]), 4) if d["valores"] else None
        prom_pond = round(d["suma_pond"] / d["n"], 4) if d["n"] else None
        pct_muestra = round(d["n"] * 100.0 / n_total, 2) if n_total else None
        dimensiones.append({
            "dimension": dim,
            "indicador": d["indicador"] or "",
            "unidad": d["unidad"] or "",
            "n_resultados": d["n_resultados"],
            "n": d["n"],
            "promedio": prom,
            "promedio_ponderado": prom_pond,
            "pct_muestra": pct_muestra,
        })

    # Orden estable por dimensión para el tablero.
    dimensiones.sort(key=lambda x: x["dimension"])

    return {
        "aplicacion": aplicacion,
        "n_resultados": n_resultados,
        "n_total": n_total,
        "promedio": promedio,
        "promedio_ponderado": promedio_ponderado,
        "dimensiones": dimensiones,
    }


# ===========================================================================
# Puente Encuestas -> Indicadores (A2)
# ===========================================================================
# Fuente que se estampa en `Valor Indicador.fuente`; también es la marca que
# identifica los valores creados por ESTE motor (auto-sanación de duplicados).
FUENTE_ENCUESTA = "encuesta"


def publicar_valores_indicador(aplicacion):
    """Materializa los `Valor Indicador` de una `Aplicacion Instrumento` cerrada.

    Agrupa las filas de `Resultado Instrumento` POR INDICADOR DECLARADO:

        indicador_de_la_fila = Resultado Instrumento.indicador
                               or Instrumento.indicador (herencia de plantilla)

    Nunca se infiere el Indicador desde `dimension` (texto libre): la fila sin
    indicador declarado ni heredable se OMITE y se cuenta en el retorno.

    Por grupo publica UN `Valor Indicador` con el promedio PONDERADO por `n`
    (fallback a promedio simple si la suma de `n` es 0), `fuente="encuesta"`,
    `calculado=1`, y el ámbito (periodo/programa-sede/unidad) copiado de la
    aplicación. Es IDEMPOTENTE: la clave es el back-link
    `Resultado Instrumento.valor_indicador` de las filas del grupo — si ya
    apunta a un Valor Indicador vivo se actualiza ése; si no, se crea y se
    escribe el back-link en TODAS las filas del grupo.

    Devuelve un dict con `publicados` (uno por indicador), `omitidas`
    (nº de filas sin indicador declarado), `dimensiones_omitidas` y
    `dimensiones_heredadas`.

    Sobre la herencia, que es cómoda y silenciosa a la vez: si el `Instrumento`
    declara indicador, TODAS sus dimensiones tributan a él, incluidas las que no
    miden eso. Medido en producción (2026-08-20) sobre una encuesta docente que
    llevaba una dimensión de infraestructura: el indicador CONEAU ID19 se
    publicó como 71.21 en vez de 81.43 -- 10 puntos de diferencia en un dato que
    va a SINEACE, sin ningún aviso. No se puede excluir una fila dejándole el
    indicador vacío (eso es justo lo que dispara la herencia); la única vía hoy
    es NO declarar indicador en el `Instrumento` y declararlo fila por fila.
    Por eso el retorno nombra las dimensiones que entraron por herencia: que la
    mezcla sea al menos VISIBLE. Si conviene poder marcar "esta dimensión no
    tributa" es decisión de Calidad, no se asume aquí.
    """
    if not aplicacion:
        frappe.throw(_("Falta la aplicación de instrumento a publicar."))

    apl = frappe.db.get_value(
        "Aplicacion Instrumento",
        aplicacion,
        ["name", "instrumento", "periodo_academico", "programa_sede",
         "unidad_organica", "fecha_fin"],
        as_dict=True,
    )
    if not apl:
        frappe.throw(_("La aplicación de instrumento {0} no existe.").format(aplicacion))

    # Indicador de plantilla (1 por instrumento): se hereda cuando la fila no
    # declara el suyo.
    indicador_plantilla = (
        frappe.db.get_value("Instrumento", apl.instrumento, "indicador")
        if apl.instrumento
        else None
    )

    filas = frappe.get_all(
        "Resultado Instrumento",
        filters={"aplicacion_instrumento": apl.name},
        fields=["name", "dimension", "indicador", "valor", "unidad", "n", "valor_indicador"],
        order_by="creation asc",
    )

    grupos = {}
    omitidas = 0
    dimensiones_omitidas = []
    for f in filas:
        heredado = not f.indicador and bool(indicador_plantilla)
        indicador = f.indicador or indicador_plantilla
        # Sin enlace explícito (ni heredado), o con un Link colgado: se omite.
        if not indicador or not frappe.db.exists("Indicador", indicador):
            omitidas += 1
            dimensiones_omitidas.append(f.dimension or "")
            continue
        g = grupos.setdefault(
            indicador,
            {"filas": [], "valores": [], "n": 0, "suma_pond": 0.0,
             "n_completo": True, "unidad": f.unidad, "heredadas": []},
        )
        g["filas"].append(f)
        if heredado:
            # Entró por herencia de plantilla, no porque la fila lo declarara.
            # Se anota para poder DECIRLO (ver `dimensiones_heredadas` en el
            # retorno): la herencia es cómoda pero silenciosa, y una dimensión
            # que no mide lo que el indicador mide desplaza su promedio sin que
            # nadie lo note.
            g["heredadas"].append(f.dimension or "")
        # Solo las filas CON valor entran en la media: sumar el `n` de una fila
        # sin valor inflaría el denominador y hundiría el ponderado.
        #
        # `valor` es un Float de Frappe => la columna es NOT NULL DEFAULT 0.0
        # (verificado en Postgres), asi que una fila NUNCA llenada llega como
        # 0.0 y es INDISTINGUIBLE de un 0 medido de verdad. Ante esa ambiguedad
        # se elige el lado seguro: 0.0 se trata como "sin dato" y se OMITE.
        # Publicar un 0 fantasma seria peor que omitir un 0 real -- este valor
        # termina en un indicador reportado a SINEACE, y una omision queda
        # visible en `omitidas`/`dimensiones_omitidas`, mientras que un 0
        # inventado se reportaria como "0% de satisfaccion" sin dejar rastro.
        # Si Calidad necesita registrar ceros reales, la via correcta es hacer
        # el campo representable (p.ej. un `valor_declarado` Check) -- decision
        # de negocio pendiente, no se asume aqui.
        if f.valor:
            g["valores"].append(f.valor)
            g["n"] += (f.n or 0)
            g["suma_pond"] += f.valor * (f.n or 0)
            if not f.n:
                # Sin `n` no se puede ponderar esta fila (ver nota en el cálculo).
                g["n_completo"] = False
        if not g["unidad"] and f.unidad:
            g["unidad"] = f.unidad

    # La fecha del valor es el corte real del campo (fin de la aplicación).
    fecha = get_datetime(apl.fecha_fin) if apl.fecha_fin else now_datetime()

    publicados = []
    for indicador, g in grupos.items():
        if not g["valores"]:
            # Grupo sin ningún `valor` numérico: no hay nada que publicar.
            omitidas += len(g["filas"])
            dimensiones_omitidas.extend((f.dimension or "") for f in g["filas"])
            continue

        # `n` es Int de Frappe => NOT NULL DEFAULT 0, la MISMA ambigüedad que
        # `valor`: no se distingue "0 respuestas" de "no lo llenaron". Ponderar
        # con un `n` faltante le da peso CERO a esa fila, o sea la borra del
        # promedio en silencio. Por eso el ponderado solo se usa cuando TODAS
        # las filas con valor traen su `n`; si a alguna le falta, se cae al
        # promedio simple para el grupo entero: menos preciso, pero no descarta
        # ninguna medición sin avisar.
        if g["n"] and g["n_completo"]:
            valor_num = round(g["suma_pond"] / g["n"], 4)     # ponderado por n
        else:
            valor_num = round(sum(g["valores"]) / len(g["valores"]), 4)  # simple

        vi = _upsert_valor_indicador(apl, indicador, valor_num, g, fecha)

        # Back-link en todas las filas que sustentan el valor. db.set_value con
        # update_modified=False para no re-disparar validaciones en cadena ni
        # ensuciar el `modified` de los resultados (mismo patrón que M06).
        for f in g["filas"]:
            if f.valor_indicador != vi:
                frappe.db.set_value(
                    "Resultado Instrumento", f.name, "valor_indicador", vi,
                    update_modified=False,
                )

        publicados.append({
            "indicador": indicador,
            "valor_indicador": vi,
            "valor_num": valor_num,
            "n": g["n"],
            "n_filas": len(g["filas"]),
            "unidad": g["unidad"] or "",
            "dimensiones_heredadas": list(g["heredadas"]),
        })

    publicados.sort(key=lambda x: x["indicador"])

    return {
        "aplicacion": apl.name,
        "publicados": publicados,
        "n_publicados": len(publicados),
        "omitidas": omitidas,
        "dimensiones_omitidas": dimensiones_omitidas,
        "dimensiones_heredadas": [
            d for p in publicados for d in p["dimensiones_heredadas"]
        ],
    }


def _upsert_valor_indicador(apl, indicador, valor_num, grupo, fecha):
    """Crea o actualiza el `Valor Indicador` del par (aplicación, indicador).

    La identidad se resuelve por el back-link ya escrito en las filas del grupo
    (no por los campos del Valor Indicador: los Links vacíos en Postgres son
    ambiguos entre NULL y ''). Si el grupo apunta a más de un Valor Indicador
    —dos publicaciones concurrentes— se conserva el más antiguo y se borran los
    extras QUE ESTE MOTOR CREÓ (fuente "encuesta"), para que el tablero no
    cuente el mismo indicador dos veces. Devuelve el `name`.
    """
    enlazados = [f.valor_indicador for f in grupo["filas"] if f.valor_indicador]
    # Se re-consulta en vez de confiar en el back-link: el Valor Indicador pudo
    # haberse borrado a mano (Link colgado) -> en ese caso se crea uno nuevo.
    #
    # Se filtra por `indicador` Y por `fuente`, no solo por `name`. Ambos filtros
    # evitan una pérdida de dato SILENCIOSA:
    #  - por `indicador`: si Calidad corrige el Indicador de una fila ya publicada
    #    (caso de uso explícito de `publicar_indicadores`), su back-link sigue
    #    apuntando al Valor Indicador del indicador ANTERIOR. Sin este filtro, el
    #    grupo nuevo reutilizaría ese mismo documento y lo pisaría, dejando UN solo
    #    Valor Indicador y borrando el del indicador viejo — sin error y sin
    #    auto-sanarse nunca.
    #  - por `fuente`: `Resultado Instrumento.valor_indicador` es un Link editable
    #    (DPGC/Analista/Data Steward tienen escritura). Si alguien lo apunta a mano
    #    a uno de los Valor Indicador que cargan los conectores MidPoint/Oracle,
    #    este motor lo reescribiría entero — y `ignore_version` suprimiría el
    #    historial. Solo se reutiliza lo que este motor mismo publicó.
    candidatos = frappe.get_all(
        "Valor Indicador",
        filters={
            "name": ["in", enlazados],
            "indicador": indicador,
            "fuente": FUENTE_ENCUESTA,
        },
        pluck="name",
        order_by="creation asc",
    ) if enlazados else []

    if candidatos:
        # `candidatos` ya viene acotado a (indicador, fuente=encuesta), así que
        # todos son de este motor: los extras son duplicados reales y se pueden
        # consolidar en el más antiguo.
        vi = frappe.get_doc("Valor Indicador", candidatos[0])
        for extra in candidatos[1:]:
            frappe.delete_doc("Valor Indicador", extra, force=1, ignore_permissions=True)
    else:
        vi = frappe.new_doc("Valor Indicador")

    vi.indicador = indicador
    vi.periodo_academico = apl.periodo_academico
    vi.programa_sede = apl.programa_sede
    vi.unidad_organica = apl.unidad_organica
    vi.valor_num = valor_num
    # `valor_texto` es Data(140): trazabilidad corta y truncada por seguridad.
    vi.valor_texto = f"{apl.name} · n={grupo['n']}"[:140]
    vi.calculado = 1
    vi.fuente = FUENTE_ENCUESTA
    vi.fecha = fecha
    if not vi.registrado_por:
        vi.registrado_por = frappe.session.user
    vi.flags.ignore_permissions = True
    # ignore_version evita ruido de versión al re-publicar en cada save.
    vi.flags.ignore_version = True
    vi.save(ignore_permissions=True)
    return vi.name
