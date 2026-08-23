"""F17 — Clasifica cada Marco Normativo por su ALCANCE.

Sin esta clasificación, la diferencia entre los tres mundos que la normativa
peruana mantiene separados vivía solo en el nombre del marco, y nada impedía
cruzarlos. Comprobado en producción el 2026-08-23: abriendo una autoevaluación
con el marco de licenciamiento y calificando sus condiciones, el sistema emitía
«Acreditado 6 años» — un resultado que ese marco no otorga.

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

El propio Modelo de Acreditación Institucional del Coneau (2026) lo dice en su
§4.2: los estándares se definieron revisando las condiciones básicas de Sunedu
«para diferenciar los niveles de exigencia». Son escalones distintos de una
misma escalera, no sinónimos.

Ejecutar (idempotente):
    bench --site <site> execute sgc.setup.f17_alcance_marcos.run
"""
import frappe

LICENCIAMIENTO = "Licenciamiento"
ACRED_PROGRAMA = "Acreditación de programa"
ACRED_INSTITUCIONAL = "Acreditación institucional"

# Clasificación explícita de los marcos conocidos. Se listan por código en vez
# de deducirlos del nombre: un marco nuevo debe clasificarse a conciencia, no
# por coincidencia de texto.
ALCANCE_POR_MARCO = {
    "CBC-SUNEDU-2026": LICENCIAMIENTO,
    "CONEAU-Programas-2025": ACRED_PROGRAMA,
    "CONEAU-Institucional-2026": ACRED_INSTITUCIONAL,
}


def run():
    frappe.flags.in_patch = True
    clasificados, pendientes = [], []

    for marco in frappe.get_all("Marco Normativo", fields=["name", "ente", "alcance"]):
        esperado = ALCANCE_POR_MARCO.get(marco.name)
        if not esperado and marco.ente == "SUNEDU":
            # Regla de respaldo SOLO hacia el lado prudente: lo de Sunedu es
            # licenciamiento. Nunca se asume acreditación por descarte, porque
            # equivocarse en ese sentido es lo que emite un sello que nadie
            # otorgó.
            esperado = LICENCIAMIENTO
        if not esperado:
            pendientes.append(marco.name)
            continue
        if marco.alcance != esperado:
            frappe.db.set_value("Marco Normativo", marco.name, "alcance", esperado,
                                update_modified=False)
            clasificados.append((marco.name, esperado))

    frappe.db.commit()

    print("F17 alcance de marcos OK:", len(clasificados), "actualizado(s)")
    for nombre, alcance in clasificados:
        print("   %-30s -> %s" % (nombre, alcance))
    if pendientes:
        print("   ⚠ SIN CLASIFICAR (añádelos a ALCANCE_POR_MARCO):", ", ".join(pendientes))
