"""F17 — ALCANCE y METADATOS normativos de cada Marco Normativo.

Dos cosas que se arreglan juntas porque fallan por la misma causa: el marco no
declara lo que es.

1. ALCANCE. Sin esta clasificación, la diferencia entre los tres mundos que la
   normativa peruana mantiene separados vivía solo en el nombre del marco, y
   nada impedía cruzarlos. Comprobado en producción el 2026-08-23: abriendo una
   autoevaluación con el marco de licenciamiento y calificando sus condiciones,
   el sistema emitía «Acreditado 6 años» — un resultado que ese marco no otorga.

2. METADATOS. En producción los tres marcos llevan nombre y nota pobres, y uno
   de ellos derechamente engañoso: el de licenciamiento se llama
   `CBC-SUNEDU-2026` cuando su contenido son las 8 condiciones básicas de
   calidad (CBC) del Modelo de Licenciamiento Institucional aprobado por la
   Resolución del Consejo Directivo (RCD) 006-2015-SUNEDU/CD. Ese «2026» hace
   creer que hay un modelo de 2026 que no existe. El `codigo` es la clave
   primaria del registro (`autoname: field:codigo`) y renombrarlo rompería toda
   referencia, así que NO se toca: se corrigen `nombre`, `version` y
   `nota_normativa`, y la nota deja constancia de que el código heredado no es
   el año del modelo.

Los tres mundos, y por qué no se mezclan:

  Licenciamiento (Sunedu)   — el permiso para OPERAR. Obligatorio. Lógica de
                              semáforo: se cumple o no. Su puerta en el sistema
                              es `Informe Cumplimiento`.
  Acreditación de programa  — sello voluntario para UNA carrera. Modelo Coneau:
                              10 estándares, 53 criterios, 29 indicadores.
                              Excelencia a partir de 16 puntos (Tabla 10).
  Acreditación institucional— sello voluntario para la UNIVERSIDAD entera.
                              9 estándares, 68 criterios, 37 indicadores.
                              Excelencia a partir de 20 puntos.

No es criterio propio. El Modelo de Licenciamiento Institucional (RCD
006-2015-SUNEDU/CD, §2.5) llama a licenciamiento y acreditación «distintos y
complementarios», y sitúa el primero como condición necesaria para iniciar el
proceso conducente a la segunda, que es voluntaria. Son escalones distintos de
una misma escalera, no sinónimos.

Fuentes primarias de todo lo que se afirma aquí (en `sciback/biblioteca/`):
`sunedu/rcd-006-2015-modelo-licenciamiento-institucional.pdf`,
`sunedu/guia-sunedu-2024-aplicacion-ley-32105.pdf`,
`sineace/modelo-acreditacion-programas-estudios-coneau-2026.pdf`,
`sineace/modelo-acreditacion-institucional-universidades-coneau-2026.pdf`,
`congreso/ley-30220-ley-universitaria-ACTUALIZADA.pdf`.

Ejecutar (idempotente):
    bench --site <site> execute sgc.setup.f17_alcance_marcos.run
"""
import unicodedata

import frappe

# Definición del campo. Se asegura AQUÍ y no solo en `f1_estructura`, porque
# aquel solo crea el DocType cuando aún no existe: en un sitio ya instalado, un
# campo nuevo en esa lista no llega nunca a la base. Mismo patrón que
# `f2_fields.py`.
CAMPO_ALCANCE = {
    "fieldname": "alcance",
    "fieldtype": "Select",
    "label": "Alcance",
    "options": "\nLicenciamiento\nAcreditación de programa\nAcreditación institucional\nGestión interna",
    "in_list_view": 1,
    "in_standard_filter": 1,
    "insert_after": "ente",
    "description": "Licenciamiento = permiso para operar (Sunedu). "
                   "Acreditación = sello de calidad (Sineace/Coneau), por programa o institucional.",
}

LICENCIAMIENTO = "Licenciamiento"
ACRED_PROGRAMA = "Acreditación de programa"
ACRED_INSTITUCIONAL = "Acreditación institucional"


# ===========================================================================
# Reglas de vigencia (Tabla 9 de los modelos Coneau)
# ===========================================================================
# ⚠️ HOY NADIE LEE ESTE JSON. La regla de vigencia está escrita a fuego en
# `sgc/scoring.py::proponer_vigencia`, igual para los dos modelos Coneau.
# Funciona porque sus tramos 1-3 coinciden; sus umbrales de excelencia NO
# (16 puntos en programas, 20 en institucional, Tabla 9 de cada modelo).
# Poblar `reglas_vigencia` es PREPARAR EL TERRENO, no activarlo: deja el dato
# declarado por marco para cuando se implemente el tramo de 8 años, que debe
# leerse de aquí y no del código. Este paso NO modifica `scoring.py`.
# Los literales de `resultado` son los del Select `Autoevaluacion.vigencia_propuesta`.

def _tabla9(puntaje_excelencia_minimo, fuente):
    """Los cuatro tramos de la Tabla 9, con el umbral de excelencia del modelo.

    Idénticos en ambos modelos Coneau salvo ese umbral — que es justo lo que el
    código fijo no puede distinguir.
    """
    return {
        "fuente": fuente,
        "escala": ["NL", "L", "LP"],
        "base": "niveles confirmados de todos los estándares del marco",
        "tramos": [
            {"condicion": "algun_estandar_NL", "resultado": "En proceso", "anios": 0},
            {"condicion": "todos_L_o_combinacion_L_LP", "resultado": "Acreditado 3 anios", "anios": 3},
            {"condicion": "todos_LP", "resultado": "Acreditado 6 anios", "anios": 6},
            {
                "condicion": "todos_LP_y_puntaje_excelencia_suficiente",
                "resultado": "Acreditado 8 anios",
                "anios": 8,
                "puntaje_excelencia_minimo": puntaje_excelencia_minimo,
            },
        ],
    }


# ===========================================================================
# Metadatos de los marcos conocidos
# ===========================================================================

def _campo(valor, *senales):
    """Valor canónico de un campo, y las señales que lo dan por ya correcto.

    `senales` son fragmentos que, si aparecen TODOS en el valor que hay en la
    base, significan que alguien ya escribió a mano algo que dice lo correcto —
    y entonces no se pisa. Sin señales explícitas, la señal es el propio valor
    (es decir: solo se respeta la coincidencia exacta). La comparación ignora
    mayúsculas, tildes y espacios de más.
    """
    return {"valor": valor, "senales": senales or (valor,)}


NOTA_CBC = (
    "Modelo de Licenciamiento Institucional de la Superintendencia Nacional de Educación "
    "Superior Universitaria (Sunedu), aprobado por la Resolución del Consejo Directivo (RCD) "
    "006-2015-SUNEDU/CD — Anexo N.° 01 de «El Modelo de Licenciamiento y su Implementación en el "
    "Sistema Universitario Peruano». Son 8 condiciones básicas de calidad (CBC), Condición I a "
    "Condición VIII, con los textos del artículo 28 de la Ley 30220, Ley Universitaria.\n\n"
    "VIGENTE, y es el modelo que aplica a una universidad ya licenciada. No confundirlo con el "
    "modelo de licenciamiento de universidades NUEVAS (RCD 043-2020), que tiene 6 CBC: los "
    "modelos Coneau mapean sus estándares contra esa matriz de 6 y de ahí sale la confusión "
    "recurrente. Los enumera uno por uno la Guía de orientación para la aplicación de la Ley "
    "32105 (Sunedu, Dirección Técnico Normativa, 2024).\n\n"
    "Este marco NO otorga años de vigencia, y por eso no lleva reglas de vigencia: el "
    "licenciamiento se cumple o no se cumple. El artículo 13.4 de la Ley Universitaria, en la "
    "redacción que le dio la Ley 32105, hizo la autorización "
    "de carácter permanente «siempre y cuando las universidades demuestren el cumplimiento "
    "continuo de las condiciones básicas de calidad», y derogó el modelo de renovación "
    "periódica (RCD 091-2021). El artículo 13.5 nombra entre las herramientas de la Sunedu «la "
    "presentación de informes anuales de cumplimiento»: esa es la base legal del módulo de "
    "Informe de Cumplimiento del SGC.\n\n"
    "SOBRE EL CÓDIGO: `CBC-SUNEDU-2026` es un código heredado y su «2026» NO es el año del "
    "modelo — el modelo es de 2015. No se renombra porque `codigo` es la clave primaria del "
    "registro y hay documentos que lo referencian.\n\n"
    "NO VERIFICADO: la guía de la Sunedu de 2024 cita junto a este modelo la RS 054-2017; ese "
    "documento aún no está en la biblioteca, así que aquí no se afirma nada de su contenido."
)

NOTA_CONEAU_PROGRAMAS = (
    "Modelo de Acreditación para Programas de Estudios de Educación Superior Universitaria del "
    "Coneau (Consejo de Evaluación, Acreditación y Certificación de la Calidad de la Educación "
    "Universitaria), órgano operador del Sineace (Sistema Nacional de Evaluación, Acreditación y "
    "Certificación de la Calidad Educativa). Según la portada del propio modelo: primera edición "
    "electrónica, agosto de 2025; resolución de aprobación, Resolución de Presidencia "
    "N.° 000106-2025-SINEACE/COSUSINEACE-P.\n\n"
    "10 estándares, 53 criterios, 52 evidencias y 29 indicadores (Tabla 8 del modelo). Valoración "
    "por estándar en escala de tres niveles: NL (no logrado), L (logrado), LP (logrado "
    "plenamente).\n\n"
    "Vigencia (Tabla 9): algún estándar NL, en proceso de acreditación; todos L o combinación "
    "L/LP, 3 años; todos LP, 6 años; todos LP y 16 o más puntos de la Tabla 10 (criterios de "
    "acreditación con excelencia), 8 años. El tramo de 8 años todavía NO lo produce el sistema: "
    "nadie calcula el puntaje de excelencia ni están cargados los criterios de la Tabla 10.\n\n"
    "Acreditación VOLUNTARIA, y por programa de estudios. No sustituye al licenciamiento de la "
    "Sunedu ni se calcula con sus condiciones."
)

NOTA_CONEAU_INSTITUCIONAL = (
    "Modelo de Acreditación Institucional de Universidades y Escuelas de Posgrado del Coneau "
    "(Consejo de Evaluación, Acreditación y Certificación de la Calidad de la Educación "
    "Universitaria), órgano operador del Sineace. El propio modelo titula su sección 6 "
    "«Estándares para la acreditación institucional de universidades 2026».\n\n"
    "9 estándares, 68 criterios, 84 evidencias y 37 indicadores. Misma escala de tres niveles "
    "NL / L / LP que el modelo de programas.\n\n"
    "Vigencia (Tabla 9): algún estándar NL, en proceso de acreditación; todos L o combinación "
    "L/LP, 3 años; todos LP, 6 años; todos LP y 20 o más puntos de la Tabla 10, 8 años. OJO: el "
    "umbral de excelencia es 20, no 16 como en programas — es la única diferencia entre ambas "
    "tablas de vigencia, y la razón por la que la regla no puede quedarse escrita a fuego en el "
    "código.\n\n"
    "Su §4.2 cuenta que la propuesta de estándares consideró la revisión de las condiciones "
    "básicas del modelo de licenciamiento para universidades NUEVAS, lo que «ha permitido "
    "diferenciar los niveles de exigencia respecto a la calidad de la gestión institucional»: "
    "acreditar es el escalón de arriba del licenciamiento, no lo mismo.\n\n"
    "Acreditación VOLUNTARIA, y de la universidad entera."
)

# Los marcos conocidos, listados por código (= `name`) en vez de deducidos del
# nombre: un marco nuevo debe clasificarse a conciencia, no por coincidencia de
# texto. Un marco que no esté aquí NO se toca — se reporta al final.
MARCOS = {
    "CBC-SUNEDU-2026": {
        "alcance": LICENCIAMIENTO,
        "campos": {
            "nombre": _campo(
                "Modelo de Licenciamiento Institucional (Sunedu, RCD 006-2015-SUNEDU/CD)",
                "licenciamiento institucional",
            ),
            # El año del MODELO, que es lo que este campo significa. El «2026»
            # del código no lo es.
            "version": _campo("2015", "2015"),
            "nota_normativa": _campo(NOTA_CBC, "006-2015"),
        },
        # Sin reglas de vigencia a propósito: el licenciamiento no concede años
        # (Ley 32105, art. 13.4 — autorización permanente con cumplimiento continuo).
        "reglas_vigencia": None,
    },
    "CONEAU-Programas-2025": {
        "alcance": ACRED_PROGRAMA,
        "campos": {
            "nombre": _campo(
                "Modelo de Acreditación para Programas de Estudios de Educación Superior "
                "Universitaria del Coneau (2025)",
                "programas de estudios",
            ),
            "version": _campo("2025", "2025"),
            "nota_normativa": _campo(NOTA_CONEAU_PROGRAMAS, "53 criterios"),
        },
        "reglas_vigencia": _tabla9(16, "Tabla 9 del Modelo de Acreditación para Programas de "
                                       "Estudios del Coneau"),
    },
    "CONEAU-Institucional-2026": {
        "alcance": ACRED_INSTITUCIONAL,
        "campos": {
            "nombre": _campo(
                "Modelo de Acreditación Institucional de Universidades y Escuelas de Posgrado "
                "del Coneau (2026)",
                "acreditacion institucional",
            ),
            "version": _campo("2026", "2026"),
            "nota_normativa": _campo(NOTA_CONEAU_INSTITUCIONAL, "68 criterios"),
        },
        "reglas_vigencia": _tabla9(20, "Tabla 9 del Modelo de Acreditación Institucional de "
                                       "Universidades y Escuelas de Posgrado del Coneau"),
    },
}

# Compatibilidad: la clasificación por alcance, que es lo que este paso hacía
# antes de encargarse también de los metadatos.
ALCANCE_POR_MARCO = {codigo: datos["alcance"] for codigo, datos in MARCOS.items()}


# ===========================================================================
# Decisión (funciones puras: no tocan la base — así se pueden testear sin sitio)
# ===========================================================================

def _normalizar(texto):
    """Minúsculas, sin tildes y con los espacios colapsados.

    Para comparar lo que hay escrito con lo que debería decir sin que un acento
    o un doble espacio provoquen una reescritura innecesaria.
    """
    if texto is None:
        return ""
    plano = unicodedata.normalize("NFKD", str(texto))
    plano = "".join(c for c in plano if not unicodedata.combining(c))
    return " ".join(plano.casefold().split())


def _cambios_de_metadatos(actual, campos):
    """Qué escribir y qué dejar como está. Devuelve `(cambios, respetados)`.

    Tres casos por campo:
      vacío           -> se fija el valor canónico;
      con las señales -> se RESPETA (alguien ya escribió algo que dice lo
                         correcto, quizá mejor redactado que esto);
      cualquier otro  -> se fija (es el valor pobre o engañoso que venía).

    El valor canónico contiene sus propias señales, así que una segunda pasada
    lo respeta: de ahí la idempotencia.
    """
    cambios, respetados = {}, []
    for fieldname, spec in campos.items():
        actual_norm = _normalizar(actual.get(fieldname))
        if not actual_norm:
            cambios[fieldname] = spec["valor"]
        elif all(_normalizar(s) in actual_norm for s in spec["senales"]):
            respetados.append(fieldname)
        else:
            cambios[fieldname] = spec["valor"]
    return cambios, respetados


def _reglas_a_fijar(actual, reglas):
    """JSON de reglas de vigencia a escribir, o `None` si no hay que tocar nada.

    Solo se puebla cuando el campo está VACÍO. Nunca se pisa: si alguien puso
    ahí un JSON propio, es una decisión deliberada sobre un campo que hoy no
    lee nadie, y machacarla sería peor que dejarla.
    """
    if not reglas:
        return None
    if isinstance(actual, str):
        actual = actual.strip()
    elif isinstance(actual, (dict, list)):
        # El campo JSON llega ya parseado según por dónde se lea: un dict vacío
        # es tan vacío como la cadena vacía, y sin esto pasaría por "ocupado".
        actual = actual or ""
    if actual not in (None, "", "{}", "[]", "null"):
        return None
    return frappe.as_json(reglas)


# ===========================================================================
# Aplicación
# ===========================================================================

def _asegurar_campo():
    """Añade `alcance` al DocType si falta. Idempotente."""
    doc = frappe.get_doc("DocType", "Marco Normativo")
    if any(f.fieldname == "alcance" for f in doc.fields):
        return False
    doc.append("fields", CAMPO_ALCANCE)
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return True


CAMPOS_LEIDOS = ["name", "ente", "alcance", "nombre", "version", "nota_normativa", "reglas_vigencia"]


def run():
    frappe.flags.in_patch = True
    frappe.flags.in_fixtures = True

    if _asegurar_campo():
        print("F17: campo `alcance` añadido a Marco Normativo")

    revisados, pendientes = [], []

    for marco in frappe.get_all("Marco Normativo", fields=CAMPOS_LEIDOS):
        conocido = MARCOS.get(marco.name)
        cambios, respetados = {}, []

        if conocido:
            alcance = conocido["alcance"]
            cambios, respetados = _cambios_de_metadatos(marco, conocido["campos"])
            reglas = _reglas_a_fijar(marco.get("reglas_vigencia"), conocido.get("reglas_vigencia"))
            if reglas:
                cambios["reglas_vigencia"] = reglas
        elif marco.ente == "SUNEDU":
            # Regla de respaldo SOLO hacia el lado prudente: lo de Sunedu es
            # licenciamiento. Nunca se asume acreditación por descarte, porque
            # equivocarse en ese sentido es lo que emite un sello que nadie
            # otorgó. Los metadatos de un marco desconocido NO se tocan: no
            # sabemos qué norma es.
            alcance = LICENCIAMIENTO
        else:
            pendientes.append(marco.name)
            continue

        if marco.alcance != alcance:
            cambios["alcance"] = alcance

        if cambios:
            frappe.db.set_value("Marco Normativo", marco.name, cambios, update_modified=False)
        revisados.append((marco.name, sorted(cambios), sorted(respetados)))

    frappe.db.commit()

    actualizados = [nombre for nombre, cambios, _ in revisados if cambios]
    print("F17 marcos: %d revisado(s), %d con cambios" % (len(revisados), len(actualizados)))
    for nombre, cambios, respetados in revisados:
        print("   %s" % nombre)
        print("      fijado:    %s" % (", ".join(cambios) or "— (ya estaba)"))
        print("      respetado: %s" % (", ".join(respetados) or "—"))
    if pendientes:
        print("   ⚠ SIN CLASIFICAR (añádelos a MARCOS):", ", ".join(pendientes))

    return {"revisados": revisados, "pendientes": pendientes}
