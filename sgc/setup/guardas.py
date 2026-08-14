# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Guarda de sitio para los scripts que siembran datos sin marcar.

Los scripts `f*_e2e*.py` recorren el circuito completo de acreditación creando
registros de verdad: una autoevaluación, sus valoraciones, un hallazgo, una no
conformidad y un plan de mejora. Eso es exactamente lo que se quiere en un
laboratorio, y exactamente lo que no se quiere en el sitio de una institución:
los registros que dejan **no llevan ninguna marca** que los distinga del dato
real, así que una vez dentro se leen —y se reportan— como avance institucional.

Ya ocurrió. El 04-jul-2026 estos scripts se ejecutaron contra producción, y sus
53 valoraciones se estuvieron reportando durante seis semanas como la
autoevaluación de la EP de Enfermería.

Por qué una guarda y no simplemente cuidado: `bench execute` no pregunta nada y
el sitio va en un parámetro fácil de heredar de la línea anterior. La diferencia
entre laboratorio y producción no puede depender de acordarse.

**Qué sitios se consideran de pruebas**

  - Cualquiera cuyo nombre termine en `.localhost` — es la convención de bench
    para sitios locales (`sgc.localhost`, `test_site.localhost` en el CI).
  - Los que la institución declare explícitamente en `site_config.json`:

        "sgc_sitios_e2e": ["staging.ejemplo.edu.pe"]

    Es deliberado que haya que escribir el nombre del sitio a mano: habilitarlo
    es una decisión, no un descuido.

Esto NO aplica a `demo_seed.py`, que sí está pensado para correrse contra un
sitio institucional: todo lo que crea lleva `[DEMO]` en el título y códigos
`*-DEMO-*`, y `demo_cleanup.py` lo retira. Ese es el patrón correcto para
poblar un sitio real con datos de demostración.
"""
import frappe


class SitioNoEsDePruebas(Exception):
    """El script iba a sembrar datos sin marcar en un sitio que no es de pruebas."""


def sitio_es_de_pruebas(sitio: str | None = None) -> bool:
    """¿El sitio admite que se siembren datos sin marcar?"""
    sitio = sitio or frappe.local.site or ""
    if sitio.endswith(".localhost"):
        return True
    declarados = frappe.conf.get("sgc_sitios_e2e") or []
    return sitio in declarados


def exigir_sitio_de_pruebas(script: str) -> None:
    """Aborta si el sitio actual no es de pruebas.

    Se llama al principio de `run()`, antes de crear nada.
    """
    sitio = frappe.local.site or "(desconocido)"
    if sitio_es_de_pruebas(sitio):
        return
    raise SitioNoEsDePruebas(
        f"{script} crea datos de acreditación SIN marca [DEMO] y el sitio "
        f"'{sitio}' no es de pruebas: se detuvo antes de escribir nada.\n"
        f"Si de verdad querías correrlo aquí, declara el sitio en su "
        f'site_config.json: "sgc_sitios_e2e": ["{sitio}"].\n'
        f"Para poblar un sitio institucional con datos de demostración usa "
        f"sgc.setup.demo_seed, que los marca y permite retirarlos."
    )
